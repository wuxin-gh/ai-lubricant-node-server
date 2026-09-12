"""Raw ASGI handler for the ``NodeConnect`` bidirectional stream.

This is the streaming crux: the shipped Go ``agent-compose-agent`` opens
``NodeConnect`` as a connect-go bidi stream over **h2c (cleartext HTTP/2)** with
**binary-protobuf envelopes** (``application/connect+proto``). A FastAPI route
cannot express a full-duplex HTTP/2 body, so this is a *raw ASGI app* that reads
request-body chunks (``receive``) and writes response-body chunks (``send``)
concurrently over the one long-lived HTTP/2 stream.

Flow (mirror of ``pkg/agentcompose/api/node.go`` ``NodeConnect``):

1. Send response headers (200, ``content-type: application/connect+proto``).
2. Send ``NodeServerHello{server_time}`` first — the authoritative clock the node
   derives its TOTP code from.
3. Read the first upstream frame; it must be ``register``. Authenticate via TOTP
   against the stored sealed secret (unknown / revoked / bad-code all fail
   indistinguishably as permission-denied).
4. Send the ``registered`` ack; register the live connection; then run the
   downstream pump (registry queue → ``send``) and the upstream loop
   (``receive`` → decode → ``service.handle_upstream``) concurrently until either
   side ends, then emit the end-of-stream trailer and unregister.

Mounted (not a FastAPI route) at
``/agentcompose.v2.NodeService/NodeConnect`` by :mod:`.wiring`.
"""
from __future__ import annotations

import asyncio

from loguru import logger

from . import agentcompose_v2_pb2 as pb
from . import crypto, envelope
from .service import NodeService, RPCError, Code, status_to_proto
from .store import NODE_STATUS_REVOKED


# Connect error code → HTTP status is only relevant for *unary*; a streaming RPC
# always returns HTTP 200 and carries the error in the end-of-stream trailer.
_ASGI_OK_HEADERS = [
    (b"content-type", envelope.CONTENT_TYPE.encode("ascii")),
    # We neither send nor accept compression on this stream.
    (b"connect-content-encoding", b"identity"),
]


def _peer_address(scope: dict) -> str:
    """The node's address as seen by the server, for the console to display.

    Prefers the proxy-forwarded client IP (``x-forwarded-for`` / ``x-real-ip``)
    so a node behind a reverse proxy still shows its own address rather than the
    proxy's, and falls back to the raw ASGI socket peer. Returns "" when nothing
    is available (e.g. an in-process test transport).
    """
    headers = {}
    for raw_key, raw_value in scope.get("headers") or []:
        try:
            headers[raw_key.decode("latin-1").lower()] = raw_value.decode("latin-1")
        except Exception:  # noqa: BLE001 - a malformed header must not break auth
            continue

    forwarded = headers.get("x-forwarded-for", "")
    if forwarded:
        # Left-most entry is the original client; the rest are proxy hops.
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real_ip = (headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip

    client = scope.get("client")
    if isinstance(client, (tuple, list)) and client:
        host = str(client[0] or "").strip()
        if host:
            port = client[1] if len(client) > 1 else None
            return f"{host}:{port}" if port else host
    return ""


async def _send_start(send, status: int = 200) -> None:    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": _ASGI_OK_HEADERS,
        }
    )


async def _send_body(send, data: bytes, *, more: bool = True) -> None:
    await send({"type": "http.response.body", "body": data, "more_body": more})


class _UpstreamReader:
    """Turns the ASGI ``receive`` channel into an async iterator of decoded
    upstream frames, buffering partial envelopes across chunk boundaries."""

    def __init__(self, receive) -> None:
        self._receive = receive
        self._decoder = envelope.FrameDecoder()
        self._eof = False

    async def next(self) -> "pb.NodeUpstreamFrame | None":
        """Return the next decoded ``NodeUpstreamFrame``, or ``None`` at EOF.

        End-of-stream envelopes (flag ``0x02``) from the client terminate the
        request half; we treat them as EOF.
        """
        while True:
            frame = self._decoder.next_frame()
            if frame is not None:
                flags, payload = frame
                if flags & envelope.FLAG_END_STREAM:
                    self._eof = True
                    return None
                msg = pb.NodeUpstreamFrame()
                msg.ParseFromString(payload)
                return msg
            if self._eof:
                return None
            event = await self._receive()
            etype = event.get("type")
            if etype == "http.request":
                body = event.get("body") or b""
                if body:
                    self._decoder.feed(body)
                if not event.get("more_body", False):
                    self._eof = True
            elif etype == "http.disconnect":
                self._eof = True


async def node_connect_asgi(scope: dict, receive, send, service: NodeService) -> None:
    """ASGI handler for one ``NodeConnect`` stream."""
    if scope["type"] != "http":  # pragma: no cover - mount guards this
        return

    reader = _UpstreamReader(receive)
    await _send_start(send)

    # 1. Server hello (authoritative time) before the node registers.
    #    gateway_origin 一并通告：MCP SSE 网关在数据服务上，不在本控制面——
    #    节点拿它把会话 spec 里的相对 MCP url 拼成可达的绝对地址。空值（未推导
    #    出）时节点回退用自己拨号的本控制面地址（老行为）。
    from . import config as node_server_config

    server_time = crypto.utc_now()
    hello = pb.NodeDownstreamFrame(created_at=crypto.rfc3339nano(server_time))
    gateway_origin = (node_server_config.settings.gateway_public_url or "").strip().rstrip("/")
    hello.server_hello.CopyFrom(pb.NodeServerHello(
        server_time=crypto.rfc3339nano(server_time),
        gateway_origin=gateway_origin,
    ))
    await _send_body(send, envelope.encode_message(hello))

    # 2. Await the register frame + authenticate.
    try:
        logger.info("[nodeserver] NodeConnect: awaiting register frame")
        first = await reader.next()
        logger.info("[nodeserver] NodeConnect: got first frame = {}", first.WhichOneof("frame") if first else None)
        if first is None:
            await _end(send, RPCError(Code.INVALID_ARGUMENT, "node connect: stream closed before register"))
            return
        if first.WhichOneof("frame") != "register":
            await _end(
                send,
                RPCError(
                    Code.INVALID_ARGUMENT,
                    f"node connect: first frame must be register, got {first.WhichOneof('frame')}",
                ),
            )
            return
        logger.info("[nodeserver] NodeConnect: authenticating node_id={}", first.register.node_id)
        peer_address = _peer_address(scope)
        record = await service.authenticate_registration(first.register, server_time, peer_address=peer_address)
        logger.info("[nodeserver] NodeConnect: authenticated, record.status={}", record.status)
    except RPCError as exc:
        logger.warning("[nodeserver] NodeConnect: auth RPCError code={} msg={}", exc.code, exc.message)
        await _end(send, exc)
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("[nodeserver] register failed")
        await _end(send, RPCError(Code.INTERNAL, str(exc)))
        return

    # A revoked node gets a registered frame carrying the revoked status, then
    # the stream is closed with permission-denied.
    if record.status == NODE_STATUS_REVOKED:
        revoked = pb.NodeDownstreamFrame()
        revoked.registered.CopyFrom(
            pb.NodeRegistered(node_id=record.id, status=status_to_proto(record.status))
        )
        await _send_body(send, envelope.encode_message(revoked))
        await _end(send, RPCError(Code.PERMISSION_DENIED, f"node {record.id} is revoked"))
        return

    # 3. Ack registration.
    registered = pb.NodeDownstreamFrame(created_at=crypto.rfc3339nano(crypto.utc_now()))
    registered.registered.CopyFrom(
        pb.NodeRegistered(
            node_id=record.id,
            status=status_to_proto(record.status),
            server_time=crypto.rfc3339nano(server_time),
            online=True,
        )
    )
    await _send_body(send, envelope.encode_message(registered))

    caps = first.register.capabilities if first.register.HasField("capabilities") else None
    conn = service.registry.register(record.id, caps, peer_address)
    conn.note_heartbeat(None)  # bootstrap liveness: a just-registered node is fresh
    # Configuration is a durable authoritative snapshot. Enqueue it after the
    # mandatory registration ack so every reconnect catches up even if it missed
    # an earlier live broadcast.
    try:
        conn.send(await service.public_ip_lookup_config_frame())
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] enqueue public-ip config for {} failed: {}", record.id, exc)
    try:
        conn.send(await service.node_proxy_config_frame(record.id))
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] enqueue node proxy config for {} failed: {}", record.id, exc)

    # Host terminals outlive the NodeConnect stream. Reattach any that the node
    # still has alive so a reconnect keeps cwd and foreground processes instead
    # of opening a fresh shell.
    try:
        await service.fire_node_connected(record.id, conn)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] reattach host terminals for {} failed: {}", record.id, exc)

    # iOS host nodes: request a fresh device inventory snapshot so the management
    # console's device list reflects the current attach/detach state immediately.
    from .store import NODE_ROLE_IOS_HOST
    if record.role == NODE_ROLE_IOS_HOST:
        caps_dict = record.capabilities or {}
        if caps_dict.get("ios_mgmt") == "true":
            try:
                await service.ios_discover(record.id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[nodeserver] auto-discover iOS devices for {} failed: {}", record.id, exc)

    # 4. Downstream pump + upstream loop until either ends.
    stop = asyncio.Event()

    async def downstream_pump() -> None:
        try:
            while True:
                frame = await conn.downstream_get()
                if frame is None:  # sentinel: connection closed
                    return
                await _send_body(send, envelope.encode_message(frame))
        except Exception as exc:  # noqa: BLE001
            logger.debug("[nodeserver] downstream pump ended for {}: {}", record.id, exc)
        finally:
            stop.set()

    async def upstream_loop() -> None:
        try:
            while True:
                frame = await reader.next()
                if frame is None:
                    return
                await service.handle_upstream(record.id, conn, frame)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[nodeserver] upstream loop ended for {}: {}", record.id, exc)
        finally:
            stop.set()

    pump_task = asyncio.create_task(downstream_pump())
    up_task = asyncio.create_task(upstream_loop())
    try:
        await stop.wait()
    finally:
        service.registry.unregister(record.id, conn)
        for task in (pump_task, up_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(pump_task, up_task, return_exceptions=True)
        await _end(send, None)


async def _end(send, error: "RPCError | None") -> None:
    """Emit the end-of-stream trailer envelope and close the response body.

    ``error`` None → clean close (trailer ``{}``); otherwise a Connect error
    object. Best-effort: a broken pipe here just means the node already left.
    """
    err_obj = None
    if error is not None:
        err_obj = {"code": error.code, "message": error.message}
    try:
        await _send_body(send, envelope.encode_end_stream(err_obj), more=False)
    except Exception:  # noqa: BLE001
        pass
