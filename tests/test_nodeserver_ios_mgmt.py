"""iOS device management frame round-trip tests (role ios_host).

Tests the NodeConnect iOS management surface in the same "play the node" style as
test_nodeserver_stream_e2e.py: drive the raw ASGI handler with in-memory queues,
send frames up as the node would, assert the server's downstream dispatch and acks.

Coverage:
- ios_host registration with ios_mgmt capability label
- Auto-discover triggered after register
- NodeIosDiscover → immediate ack
- NodeIosDevicesReport upstream → cached in registry
- NodeIosClaimDevice dispatch → ack with error/success
- NodeIosReleaseDevice dispatch → ack
- NodeIosConfigureDevice dispatch → ack with applied revision
- get_ios_devices returns the cached snapshot
- Capability gating: ios_mgmt=false rejects iOS frames with failed_precondition
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from node_server import agentcompose_v2_pb2 as pb
from node_server import crypto, envelope
from node_server.connect_stream import node_connect_asgi
from node_server.registry import Registry
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
    """Simulated agent-side stream: same shape as test_nodeserver_stream_e2e.py."""

    def __init__(self) -> None:
        self._request_q: asyncio.Queue = asyncio.Queue()
        self.downstream: asyncio.Queue = asyncio.Queue()
        self._decoder = envelope.FrameDecoder()
        self._started = False

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

    def feed_upstream(self, frame: "pb.NodeUpstreamFrame", *, more: bool = True) -> None:
        self._request_q.put_nowait(
            {"type": "http.request", "body": envelope.encode_message(frame), "more_body": more}
        )

    def disconnect(self) -> None:
        self._request_q.put_nowait({"type": "http.disconnect"})

    async def next_downstream(self, timeout: float = 2.0):
        kind, msg = await asyncio.wait_for(self.downstream.get(), timeout=timeout)
        return kind, msg


async def _onboard_approved_ios_host(service: NodeService, *, ios_mgmt: bool = True):
    """Onboard + approve an ios_host node, return (node_id, secret_b32, ios_mgmt)."""
    resp = await service.onboard_node(
        pb.OnboardNodeRequest(role=pb.NodeRole.NODE_ROLE_IOS_HOST, node_name="ios-host-e2e")
    )
    await service.approve_node(pb.ApproveNodeRequest(node_id=resp.node_id))
    return resp.node_id, resp.secret, ios_mgmt


async def _register_ios_host(
    ch: FakeNodeChannel, service: NodeService, node_id: str, secret_b32: str, *, ios_mgmt: bool = True
):
    """Complete the handshake: ServerHello → register with TOTP + capabilities → registered ack."""
    kind, hello = await ch.next_downstream()
    assert kind == "frame"
    assert hello.WhichOneof("frame") == "server_hello"

    secret = crypto.decode_secret(secret_b32)
    code = crypto.generate(secret, crypto.utc_now())
    reg = pb.NodeUpstreamFrame()
    caps = pb.NodeCapabilities(os="darwin", arch="arm64")
    if ios_mgmt:
        # 真实 node-ios 把能力标签放在 caps.labels（ios/main.go Options.Labels →
        # client.go capabilityLabels → Capabilities.Labels），proto 的
        # NodeCapabilities 没有 ios_mgmt 专属字段。
        caps.labels["ios_mgmt"] = "true"
    reg.register.CopyFrom(
        pb.NodeRegister(node_id=node_id, totp_code=code, node_name="ios-host-e2e", capabilities=caps)
    )
    ch.feed_upstream(reg)

    kind, registered = await ch.next_downstream()
    assert kind == "frame"
    assert registered.WhichOneof("frame") == "registered"
    assert registered.registered.node_id == node_id

    # Wait for registry to see the connection
    for _ in range(50):
        if service.registry.lookup(node_id) is not None:
            break
        await asyncio.sleep(0.01)
    assert service.registry.lookup(node_id) is not None


@pytest.mark.asyncio
async def test_ios_host_auto_discover_after_register(db, service):
    """An ios_host with ios_mgmt=true receives a NodeIosDiscover frame after register."""
    node_id, secret_b32, _ = await _onboard_approved_ios_host(service, ios_mgmt=True)
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/agentcompose.v2.NodeService/NodeConnect"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    await _register_ios_host(ch, service, node_id, secret_b32, ios_mgmt=True)

    # The public-IP config frame arrives first (always sent post-register)
    kind, config_frame = await ch.next_downstream()
    assert kind == "frame"
    assert config_frame.WhichOneof("frame") == "public_ip_lookup_config"

    # Then the proxy config frame
    kind, proxy_frame = await ch.next_downstream()
    assert kind == "frame"
    assert proxy_frame.WhichOneof("frame") == "node_proxy_config"

    # Then the auto-discover
    kind, discover = await ch.next_downstream()
    assert kind == "frame"
    assert discover.WhichOneof("frame") == "ios_discover"
    assert discover.ios_discover.request_id  # non-empty

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


@pytest.mark.asyncio
async def test_ios_devices_report_cached_in_registry(db, service):
    """NodeIosDevicesReport upstream is cached; get_ios_devices reads it."""
    node_id, secret_b32, _ = await _onboard_approved_ios_host(service)
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    await _register_ios_host(ch, service, node_id, secret_b32)
    # Drain the auto-enqueued frames
    await ch.next_downstream()  # public_ip_lookup_config
    await ch.next_downstream()  # node_proxy_config
    await ch.next_downstream()  # ios_discover

    # Node sends a devices report
    report = pb.NodeIosDevicesReport(
        request_id="req-123",
        snapshot_revision=1,
        reported_at=crypto.rfc3339nano(crypto.utc_now()),
    )
    dev = report.devices.add()
    dev.udid = "00008030-001A1B2C3D4E5F6A"
    dev.name = "Test iPhone"
    dev.model = "iPhone15,2"
    dev.product_version = "17.3.1"
    dev.connection_type = "IOS_CONNECTION_TYPE_USB"
    dev.present = True
    dev.claimed = False

    frame = pb.NodeUpstreamFrame()
    frame.ios_devices_report.CopyFrom(report)
    ch.feed_upstream(frame)
    await asyncio.sleep(0.05)

    # get_ios_devices returns the cached snapshot
    result = await service.get_ios_devices(node_id)
    assert result["node_id"] == node_id
    assert result["snapshot_revision"] == 1
    assert len(result["devices"]) == 1
    d = result["devices"][0]
    assert d["udid"] == "00008030-001A1B2C3D4E5F6A"
    assert d["name"] == "Test iPhone"
    assert d["present"] is True
    assert d["claimed"] is False

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


@pytest.mark.asyncio
async def test_ios_claim_device_dispatch_and_ack(db, service):
    """ios_claim_device dispatches NodeIosClaimDevice, waits for ack."""
    node_id, secret_b32, _ = await _onboard_approved_ios_host(service)
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    await _register_ios_host(ch, service, node_id, secret_b32)
    await ch.next_downstream()  # public_ip_lookup_config
    await ch.next_downstream()  # node_proxy_config
    await ch.next_downstream()  # ios_discover

    # Dispatch a claim in the background
    async def _drive_claim():
        return await service.ios_claim_device(node_id, "00008030-AABBCCDDEEFF", "My iPhone", "CODE123")

    claim_task = asyncio.create_task(_drive_claim())

    # The NodeIosClaimDevice frame arrives downstream
    kind, claim_frame = await ch.next_downstream()
    assert kind == "frame"
    assert claim_frame.WhichOneof("frame") == "ios_claim_device"
    assert claim_frame.ios_claim_device.udid == "00008030-AABBCCDDEEFF"
    assert claim_frame.ios_claim_device.device_label == "My iPhone"
    assert claim_frame.ios_claim_device.pairing_code == "CODE123"
    server_frame_id = claim_frame.server_frame_id

    # Ack it as the node would
    ack = pb.NodeUpstreamFrame()
    ack.command_ack.CopyFrom(pb.NodeCommandAck(server_frame_id=server_frame_id, ok=True))
    ch.feed_upstream(ack)

    result = await asyncio.wait_for(claim_task, timeout=2.0)
    assert result["node_id"] == node_id
    assert result["udid"] == "00008030-AABBCCDDEEFF"

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


@pytest.mark.asyncio
async def test_ios_release_device_dispatch_and_ack(db, service):
    """ios_release_device dispatches NodeIosReleaseDevice, waits for ack."""
    node_id, secret_b32, _ = await _onboard_approved_ios_host(service)
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    await _register_ios_host(ch, service, node_id, secret_b32)
    await ch.next_downstream()
    await ch.next_downstream()
    await ch.next_downstream()

    async def _drive_release():
        return await service.ios_release_device(
            node_id, "device-abc123", "00008030-AABBCCDDEEFF", delete_credential=True
        )

    release_task = asyncio.create_task(_drive_release())

    kind, release_frame = await ch.next_downstream()
    assert kind == "frame"
    assert release_frame.WhichOneof("frame") == "ios_release_device"
    assert release_frame.ios_release_device.udid == "00008030-AABBCCDDEEFF"
    assert release_frame.ios_release_device.device_id == "device-abc123"
    assert release_frame.ios_release_device.delete_credential is True

    ack = pb.NodeUpstreamFrame()
    ack.command_ack.CopyFrom(pb.NodeCommandAck(server_frame_id=release_frame.server_frame_id, ok=True))
    ch.feed_upstream(ack)

    result = await asyncio.wait_for(release_task, timeout=2.0)
    assert result["node_id"] == node_id
    assert result["udid"] == "00008030-AABBCCDDEEFF"

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


@pytest.mark.asyncio
async def test_ios_configure_device_dispatch_and_ack(db, service):
    """ios_configure_device dispatches NodeIosConfigureDevice, waits for ack."""
    node_id, secret_b32, _ = await _onboard_approved_ios_host(service)
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    await _register_ios_host(ch, service, node_id, secret_b32)
    await ch.next_downstream()
    await ch.next_downstream()
    await ch.next_downstream()

    async def _drive_configure():
        return await service.ios_configure_device(
            node_id,
            "device-abc123",
            "00008030-AABBCCDDEEFF",
            config_revision=5,
            transport="usb",
            wda_bundle_id="com.facebook.WebDriverAgentRunner.xctrunner",
            xctest_config_name="WebDriverAgentRunner_iphoneos17.3-arm64",
        )

    configure_task = asyncio.create_task(_drive_configure())

    kind, cfg_frame = await ch.next_downstream()
    assert kind == "frame"
    assert cfg_frame.WhichOneof("frame") == "ios_configure_device"
    assert cfg_frame.ios_configure_device.udid == "00008030-AABBCCDDEEFF"
    assert cfg_frame.ios_configure_device.config_revision == 5
    assert cfg_frame.ios_configure_device.transport == "usb"

    ack = pb.NodeUpstreamFrame()
    ack.command_ack.CopyFrom(pb.NodeCommandAck(server_frame_id=cfg_frame.server_frame_id, ok=True))
    ch.feed_upstream(ack)

    result = await asyncio.wait_for(configure_task, timeout=2.0)
    assert result["node_id"] == node_id
    assert result["udid"] == "00008030-AABBCCDDEEFF"
    assert result["config_revision"] == 5

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


@pytest.mark.asyncio
async def test_ios_mgmt_capability_gating(db, service):
    """A node without ios_mgmt=true is rejected with failed_precondition."""
    # Onboard an ios_host but register WITHOUT the capability label
    node_id, secret_b32, _ = await _onboard_approved_ios_host(service, ios_mgmt=False)
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    await _register_ios_host(ch, service, node_id, secret_b32, ios_mgmt=False)
    await ch.next_downstream()  # public_ip_lookup_config
    await ch.next_downstream()  # node_proxy_config
    # No auto-discover (the ios_mgmt check blocks it)

    # Try to claim a device
    with pytest.raises(RPCError) as exc_info:
        await service.ios_claim_device(node_id, "00008030-AABBCCDDEEFF", "My iPhone", "CODE123")
    assert exc_info.value.code == Code.FAILED_PRECONDITION
    assert "does not support iOS management" in str(exc_info.value)

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


@pytest.mark.asyncio
async def test_get_ios_devices_empty_when_no_report_yet(db, service):
    """get_ios_devices returns empty devices[] when the node has not sent a report."""
    node_id, secret_b32, _ = await _onboard_approved_ios_host(service)
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    await _register_ios_host(ch, service, node_id, secret_b32)
    await ch.next_downstream()
    await ch.next_downstream()
    await ch.next_downstream()

    # get_ios_devices before any NodeIosDevicesReport was sent
    result = await service.get_ios_devices(node_id)
    assert result["node_id"] == node_id
    assert result["devices"] == []

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


# ── ios_host approve-gate exemption ──────────────────────────────────────────
# node-ios 不跑 agent-compose session：它注册时不报 providers/node_version/
# npm_version/runtime_version（iOS 宿主能力在 labels 的 ios_mgmt=true），
# 此前 approve_node 的执行节点分支照样卡「至少一个编辑器客户端」，ios_host
# 从门禁加上那天起就永远过不了审批。


@pytest.mark.asyncio
async def test_ios_host_approve_exempt_from_execution_gate(db, service):
    """ios_host 审批不要求 Node.js/npm/runtime/编辑器——它只做构建和驱动 iPhone。

    场景即真实 node-ios 首次入驻：onboard → 节点拨入 register（只带 os/arch +
    ios_mgmt 标签，无 providers/版本标签）→ 管理员点「通过审批」。此时必须直接
    通过，而不是被「至少一个编辑器客户端」卡死。
    """
    resp = await service.onboard_node(
        pb.OnboardNodeRequest(role=pb.NodeRole.NODE_ROLE_IOS_HOST, node_name="ios-host-gate")
    )
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    await _register_ios_host(ch, service, resp.node_id, resp.secret, ios_mgmt=True)

    record = await service.store.get_node_if_exists(resp.node_id)
    assert record is not None
    caps = record.capabilities or {}
    # 真实 node-ios 注册时确实没有任何执行节点的环境标签。
    assert not (caps.get("providers") or "").strip()
    assert not (caps.get("node_version") or "").strip()

    approve_resp = await service.approve_node(pb.ApproveNodeRequest(node_id=resp.node_id))
    assert approve_resp.node.status == pb.NodeStatus.NODE_STATUS_APPROVED

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)


@pytest.mark.asyncio
async def test_execution_node_approve_still_blocked_without_providers(db, service):
    """回归：执行节点缺编辑器仍然被审批门禁拦住——豁免只给 ios_host。"""
    # 执行节点 onboard 必须挂一个管理节点；passive 只做归属容器不拨入。
    mgr = await service.onboard_node(
        pb.OnboardNodeRequest(role=pb.NodeRole.NODE_ROLE_PASSIVE_MANAGEMENT, node_name="mgr-gate")
    )
    resp = await service.onboard_node(
        pb.OnboardNodeRequest(
            role=pb.NodeRole.NODE_ROLE_EXECUTION,
            node_name="exec-gate",
            manager_node_id=mgr.node_id,
        )
    )
    ch = FakeNodeChannel()
    scope = {"type": "http", "method": "POST", "path": "/x"}
    handler = asyncio.create_task(node_connect_asgi(scope, ch.receive, ch.send, service))

    # 注册一个什么都缺的执行节点（无 providers/版本标签）。
    kind, hello = await ch.next_downstream()
    assert kind == "frame"
    assert hello.WhichOneof("frame") == "server_hello"
    secret = crypto.decode_secret(resp.secret)
    code = crypto.generate(secret, crypto.utc_now())
    reg = pb.NodeUpstreamFrame()
    reg.register.CopyFrom(
        pb.NodeRegister(
            node_id=resp.node_id,
            totp_code=code,
            node_name="exec-gate",
            capabilities=pb.NodeCapabilities(os="linux", arch="amd64"),
        )
    )
    ch.feed_upstream(reg)
    kind, registered = await ch.next_downstream()
    assert kind == "frame"
    assert registered.WhichOneof("frame") == "registered"

    with pytest.raises(RPCError) as exc_info:
        await service.approve_node(pb.ApproveNodeRequest(node_id=resp.node_id))
    assert exc_info.value.code == Code.FAILED_PRECONDITION
    assert "编辑器" in str(exc_info.value)

    ch.disconnect()
    await asyncio.wait_for(handler, timeout=2.0)
