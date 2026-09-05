"""End-to-end NodeConnect streaming parity, driven in-process.

This exercises the streaming crux without the Go binary: it drives the raw-ASGI
``node_connect_asgi`` handler through the exact wire the shipped
``agent-compose-agent`` speaks — Connect streaming envelopes (5-byte prefix +
binary protobuf) over a simulated ASGI HTTP/2 request/response — and asserts the
full lifecycle:

* ServerHello (authoritative time) arrives first, before the node registers.
* A TOTP code derived from that time authenticates the node (the same
  ``crypto.generate`` the agent uses).
* The ``registered`` ack carries the durable node id + status + online.
* Heartbeat frames touch last-seen and mark the node online in ``ListNodes``.
* A ``DispatchSession`` reverse-dispatched from the service arrives on the node's
  downstream, and the node's ``command_ack`` unblocks the dispatch call.
* Session output the node streams up is fanned to a bound follow sink.

The "node" side is a pair of in-memory asyncio queues wired to the handler's
``receive``/``send`` — no sockets, no HTTP/2 server — so the envelope framing and
the concurrent downstream-pump / upstream-loop are what actually get tested.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from node_server import agentcompose_v2_pb2 as pb
from node_server import crypto, envelope
from node_server.connect_stream import node_connect_asgi
from node_server.registry import OutputSink, Registry
from node_server.service import Code, NodeService, RPCError
from node_server.store import node_store

_MASTER_KEY_HEX = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"


@pytest_asyncio.fixture
async def db():
    from tortoise import Tortoise

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"node_server": ["node_server.store"]},
        use_tz=False,
    )
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()


@pytest.fixture
def service():
    return NodeService(
        master_key=crypto.parse_master_key(_MASTER_KEY_HEX),
        server_url="http://127.0.0.1:8001",
        store=node_store,
        registry=Registry(),
    )


class FakeNodeChannel:
    """A simulated agent-side stream: ``receive``/``send`` ASGI callables backed
    by asyncio queues, plus a client-side envelope decoder for downstream frames.

    ``send`` (server→node) frames are decoded and pushed onto ``downstream``;
    ``feed_upstream`` (node→server) encodes a NodeUpstreamFrame into the request
    body the handler reads via ``receive``.
    """

    def __init__(self) -> None:
        self._request_q: asyncio.Queue = asyncio.Queue()
        self.downstream: asyncio.Queue = asyncio.Queue()
        self._decoder = envelope.FrameDecoder()
        self._started = False

    # ASGI callables handed to the handler ----------------------------------
    async def receive(self) -> dict:
        return await self._request_q.get()

    async def send(self, event: dict) -> None:
        if event["type"] == "http.response.start":
            self._started = True
            return
        if event["type"] == "http.response.body":
            self._decoder.feed(event.get("body") or b"")
            while True:
                frame = self._decoder.next_frame()
                if frame is None:
                    break
                flags, payload = frame
                if flags & envelope.FLAG_END_STREAM:
                    await self.downstream.put(("end", payload))
                    continue
                msg = pb.NodeDownstreamFrame()
                msg.ParseFromString(payload)
                await self.downstream.put(("frame", msg))

    # node→server helpers ---------------------------------------------------
    def feed_upstream(self, frame: "pb.NodeUpstreamFrame", *, more: bool = True) -> None:
        self._request_q.put_nowait(
            {"type": "http.request", "body": envelope.encode_message(frame), "more_body": more}
        )

    def disconnect(self) -> None:
        self._request_q.put_nowait({"type": "http.disconnect"})

    async def next_downstream(self, timeout: float = 2.0):
        kind, msg = await asyncio.wait_for(self.downstream.get(), timeout=timeout)
        return kind, msg


async def _onboard_approved_execution(service: NodeService):
    """Onboard a passive manager + an execution node, approve it, return
    (node_id, secret_b32)."""
    mgr = await service.onboard_node(
        pb.OnboardNodeRequest(role=pb.NodeRole.NODE_ROLE_PASSIVE_MANAGEMENT)
    )
    ex = await service.onboard_node(
        pb.OnboardNodeRequest(
            role=pb.NodeRole.NODE_ROLE_EXECUTION,
            manager_node_id=mgr.node_id,
            node_name="worker-e2e",
        )
    )
    await service.approve_node(pb.ApproveNodeRequest(node_id=ex.node_id))
    return ex.node_id, ex.secret


@pytest.mark.asyncio
async def test_full_handshake_dispatch_and_follow(db, service):
    node_id, secret_b32 = await _onboard_approved_execution(service)

    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/agentcompose.v2.NodeService/NodeConnect"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    # 1. ServerHello arrives first (authoritative clock).
    kind, hello = await ch.next_downstream()
    assert kind == "frame"
    assert hello.WhichOneof("frame") == "server_hello"
    server_time = crypto.utc_now()  # our clock is close enough (±2 step window)

    # 2. Register with a TOTP code derived from the secret, exactly as the agent.
    secret = crypto.decode_secret(secret_b32)
    code = crypto.generate(secret, server_time)
    reg = pb.NodeUpstreamFrame()
    reg.register.CopyFrom(
        pb.NodeRegister(
            node_id=node_id,
            totp_code=code,
            node_name="worker-e2e",
            capabilities=pb.NodeCapabilities(os="linux", arch="amd64", providers=["claude"]),
        )
    )
    ch.feed_upstream(reg)

    # 3. registered ack.
    kind, registered = await ch.next_downstream()
    assert kind == "frame"
    assert registered.WhichOneof("frame") == "registered"
    assert registered.registered.node_id == node_id
    assert registered.registered.status == pb.NodeStatus.NODE_STATUS_APPROVED
    assert registered.registered.online is True

    # Wait for the registry to see the live connection.
    for _ in range(50):
        if service.registry.lookup(node_id) is not None:
            break
        await asyncio.sleep(0.01)
    assert service.registry.lookup(node_id) is not None

    # 4. Heartbeat → node reads online in ListNodes.
    hb = pb.NodeUpstreamFrame()
    hb.heartbeat.CopyFrom(pb.NodeHeartbeat(node_id=node_id))
    ch.feed_upstream(hb)
    await asyncio.sleep(0.05)
    listed = await service.list_nodes(pb.ListNodesRequest())
    online = {n.node_id: n.online for n in listed.nodes}
    assert online.get(node_id) is True

    # The authoritative global public-IP lookup snapshot follows registration.
    kind, public_ip_config = await ch.next_downstream()
    assert kind == "frame"
    assert public_ip_config.WhichOneof("frame") == "public_ip_lookup_config"

    # 5. Bind a follow sink, then dispatch a session; the CreateSession command
    #    must arrive on the node downstream, and our ack unblocks dispatch.
    got_output: list[bytes] = []
    conn = service.registry.lookup(node_id)
    conn.bind_sink("will-rebind", OutputSink())  # placeholder; real sink bound after dispatch

    async def _drive_dispatch():
        req = pb.DispatchSessionRequest(node_id=node_id)
        req.session.provider = "claude"
        return await service.dispatch_session(req)

    dispatch_task = asyncio.create_task(_drive_dispatch())

    # The CreateSession frame arrives downstream; ack it as the node would.
    kind, create = await ch.next_downstream()
    assert kind == "frame"
    assert create.WhichOneof("frame") == "create_session"
    session_id = create.create_session.session_id
    assert session_id.startswith("sess-")
    server_frame_id = create.server_frame_id

    ack = pb.NodeUpstreamFrame()
    ack.command_ack.CopyFrom(pb.NodeCommandAck(server_frame_id=server_frame_id, ok=True))
    ch.feed_upstream(ack)

    resp = await asyncio.wait_for(dispatch_task, timeout=2.0)
    assert resp.accepted is True
    assert resp.session_id == session_id

    # 6. Session output the node streams up reaches a bound sink.
    conn.bind_sink(session_id, OutputSink(on_output=lambda o: got_output.append(o.data)))
    out = pb.NodeUpstreamFrame()
    out.session_output.CopyFrom(pb.NodeSessionOutput(session_id=session_id, data=b"hello from node"))
    ch.feed_upstream(out)
    await asyncio.sleep(0.05)
    assert got_output == [b"hello from node"]

    # 7. Clean teardown: node disconnects → handler unregisters.
    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)
    assert service.registry.lookup(node_id) is None


@pytest.mark.asyncio
async def test_dispatch_rejects_registered_connection_with_stale_heartbeat(db, service):
    node_id, secret_b32 = await _onboard_approved_execution(service)
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/agentcompose.v2.NodeService/NodeConnect"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    _kind, _hello = await ch.next_downstream()
    secret = crypto.decode_secret(secret_b32)
    reg = pb.NodeUpstreamFrame()
    reg.register.CopyFrom(
        pb.NodeRegister(
            node_id=node_id,
            totp_code=crypto.generate(secret, crypto.utc_now()),
            capabilities=pb.NodeCapabilities(os="linux", arch="amd64", providers=["claude"]),
        )
    )
    ch.feed_upstream(reg)
    _kind, registered = await ch.next_downstream()
    assert registered.WhichOneof("frame") == "registered"

    for _ in range(50):
        if service.registry.lookup(node_id) is not None:
            break
        await asyncio.sleep(0.01)
    conn = service.registry.lookup(node_id)
    assert conn is not None

    # Keep the stream registered but move both liveness timestamps beyond the
    # timeout. This is the exact window in which connected=true yet online=false.
    from datetime import timedelta

    conn.connected_at = crypto.utc_now() - timedelta(minutes=2)
    conn._last_heartbeat_at = crypto.utc_now() - timedelta(minutes=2)
    req = pb.DispatchSessionRequest(node_id=node_id)
    req.session.provider = "claude"
    with pytest.raises(RPCError) as exc_info:
        await service.dispatch_session(req)
    assert exc_info.value.code == Code.UNAVAILABLE
    assert "heartbeat stale" in str(exc_info.value)

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


@pytest.mark.asyncio
async def test_bad_totp_code_is_rejected(db, service):
    node_id, _secret = await _onboard_approved_execution(service)

    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    kind, hello = await ch.next_downstream()
    assert hello.WhichOneof("frame") == "server_hello"

    reg = pb.NodeUpstreamFrame()
    reg.register.CopyFrom(pb.NodeRegister(node_id=node_id, totp_code="000000"))
    ch.feed_upstream(reg)

    # The stream ends with a permission-denied trailer, no registered frame.
    kind, payload = await ch.next_downstream()
    assert kind == "end"
    trailer = envelope.parse_end_stream(payload)
    assert trailer.get("error", {}).get("code") == "permission_denied"
    await asyncio.wait_for(handler, timeout=2.0)
    assert service.registry.lookup(node_id) is None


@pytest.mark.asyncio
async def test_unknown_node_indistinguishable_permission_denied(db, service):
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    _kind, _hello = await ch.next_downstream()

    reg = pb.NodeUpstreamFrame()
    reg.register.CopyFrom(pb.NodeRegister(node_id="node-does-not-exist", totp_code="123456"))
    ch.feed_upstream(reg)

    kind, payload = await ch.next_downstream()
    assert kind == "end"
    trailer = envelope.parse_end_stream(payload)
    assert trailer.get("error", {}).get("code") == "permission_denied"
    await asyncio.wait_for(handler, timeout=2.0)
