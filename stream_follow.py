"""Raw ASGI handler for the ``FollowNodeSession`` server-stream RPC.

Port of ``pkg/agentcompose/api/node_dispatch.go`` ``FollowNodeSession``. A client
opens this Connect *server-stream* to watch a dispatched session live: it sends
one ``FollowNodeSessionRequest`` (the session id), and the server streams back
``NodeSessionEvent`` envelopes (interleaved output / structured events, then a
terminal result) as the owning node reports them upstream.

Like :mod:`.connect_stream` this is a raw-ASGI app rather than a FastAPI route,
because it must write response-body chunks over the long-lived HTTP/2 stream as
frames arrive. The framing is the same Connect streaming envelope (5-byte prefix
+ protobuf), so we reuse :mod:`.envelope`.

The bridge from the node's upstream frames to this stream is an
:class:`~.registry.OutputSink` bound on the live connection: the node's
``session_output`` / ``session_result`` / ``session_event`` frames are fanned
out to the sink, which enqueues ``NodeSessionEvent`` envelopes onto an asyncio
queue this handler drains. A ``result`` frame is terminal.
"""
from __future__ import annotations

import asyncio

from loguru import logger

from . import agentcompose_v2_pb2 as pb
from . import envelope
from .registry import OutputSink
from .service import NodeService, RPCError, Code


_ASGI_OK_HEADERS = [
    (b"content-type", envelope.CONTENT_TYPE.encode("ascii")),
    (b"connect-content-encoding", b"identity"),
]

# How many pending events the follow queue holds before dropping (a slow client
# must not block the node's upstream loop). Mirrors the Go followSink buffer.
_FOLLOW_BUFFER = 256


async def _read_first_request(receive) -> "pb.FollowNodeSessionRequest | None":
    """Read the single client request message off the request body."""
    decoder = envelope.FrameDecoder()
    eof = False
    while True:
        frame = decoder.next_frame()
        if frame is not None:
            flags, payload = frame
            if flags & envelope.FLAG_END_STREAM:
                return None
            msg = pb.FollowNodeSessionRequest()
            msg.ParseFromString(payload)
            return msg
        if eof:
            return None
        event = await receive()
        etype = event.get("type")
        if etype == "http.request":
            body = event.get("body") or b""
            if body:
                decoder.feed(body)
            if not event.get("more_body", False):
                eof = True
        elif etype == "http.disconnect":
            return None


async def proxy_follow_asgi(scope: dict, receive, send, *, base_url: str, token: str) -> None:
    """Pass the Connect server-stream through the data service unchanged."""
    if not (base_url or "").strip() or not (token or "").strip():
        await send({"type": "http.response.start", "status": 503, "headers": []})
        await send({"type": "http.response.body", "body": b"control plane unavailable", "more_body": False})
        return
    if scope["type"] != "http":
        return
    if scope.get("method") != "POST":
        await send({"type": "http.response.start", "status": 405, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        return
    body = bytearray()
    while True:
        event = await receive()
        if event.get("type") == "http.disconnect":
            return
        if event.get("type") != "http.request":
            continue
        body.extend(event.get("body") or b"")
        if not event.get("more_body", False):
            break
    import aiohttp

    url = f"{base_url.rstrip('/')}/agentcompose.v2.NodeService/FollowNodeSession"
    headers = {
        "Content-Type": "application/connect+proto",
        "Connect-Protocol-Version": "1",
        "Authorization": f"Bearer {token}",
    }
    timeout = aiohttp.ClientTimeout(total=None)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as client:
            async with client.post(url, data=bytes(body), headers=headers) as response:
                response_headers = []
                for key, value in response.headers.items():
                    if key.lower() not in {"content-length", "transfer-encoding", "connection"}:
                        response_headers.append((key.lower().encode(), value.encode()))
                await send({"type": "http.response.start", "status": response.status, "headers": response_headers})
                async for chunk in response.content.iter_chunked(64 * 1024):
                    await send({"type": "http.response.body", "body": chunk, "more_body": True})
                await send({"type": "http.response.body", "body": b"", "more_body": False})
    except (aiohttp.ClientError, asyncio.CancelledError):
        logger.debug("[nodeserver] follow proxy ended")


async def follow_node_session_asgi(scope: dict, receive, send, service: NodeService) -> None:
    """ASGI handler for one ``FollowNodeSession`` server-stream."""
    if scope["type"] != "http":  # pragma: no cover - mount guards this
        return

    await send({"type": "http.response.start", "status": 200, "headers": _ASGI_OK_HEADERS})

    async def _end(error: "RPCError | None") -> None:
        err_obj = None
        if error is not None:
            err_obj = {"code": error.code, "message": error.message}
        try:
            await send(
                {
                    "type": "http.response.body",
                    "body": envelope.encode_end_stream(err_obj),
                    "more_body": False,
                }
            )
        except Exception:  # noqa: BLE001
            pass

    # Resolve the session's live connection.
    try:
        req = await _read_first_request(receive)
        if req is None:
            await _end(RPCError(Code.INVALID_ARGUMENT, "follow node session: stream closed before request"))
            return
        conn, session_id = await service.resolve_follow(req.session_id)
    except RPCError as exc:
        await _end(exc)
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("[nodeserver] follow resolve failed")
        await _end(RPCError(Code.INTERNAL, str(exc)))
        return

    # Bind a sink that enqueues NodeSessionEvent envelopes; the loop below drains
    # it. The loop event carries the message + whether it is terminal.
    loop = asyncio.get_event_loop()
    events: asyncio.Queue = asyncio.Queue(maxsize=_FOLLOW_BUFFER)

    def _enqueue(evt: "pb.NodeSessionEvent") -> None:
        # Called from the upstream loop (same event loop); non-blocking put so a
        # slow consumer drops rather than stalling the node's upstream loop.
        try:
            events.put_nowait(evt)
        except asyncio.QueueFull:
            pass

    def on_output(out) -> None:
        evt = pb.NodeSessionEvent()
        evt.output.CopyFrom(out)
        _enqueue(evt)

    def on_result(res) -> None:
        evt = pb.NodeSessionEvent()
        evt.result.CopyFrom(res)
        _enqueue(evt)

    def on_structured(s) -> None:
        evt = pb.NodeSessionEvent()
        evt.structured.CopyFrom(s)
        _enqueue(evt)

    sink = OutputSink(on_output=on_output, on_result=on_result, on_structured=on_structured)
    conn.bind_sink(session_id, sink)

    # Watch for client disconnect concurrently so we stop when it goes away.
    disconnected = asyncio.Event()

    async def _watch_disconnect() -> None:
        try:
            while True:
                event = await receive()
                if event.get("type") == "http.disconnect":
                    disconnected.set()
                    return
        except Exception:  # noqa: BLE001
            disconnected.set()

    watch_task = loop.create_task(_watch_disconnect())
    try:
        while True:
            get_task = loop.create_task(events.get())
            done, _pending = await asyncio.wait(
                {get_task, watch_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if get_task in done:
                evt = get_task.result()
                await send(
                    {
                        "type": "http.response.body",
                        "body": envelope.encode_message(evt),
                        "more_body": True,
                    }
                )
                # A result frame is terminal for the session.
                if evt.WhichOneof("event") == "result":
                    break
            else:
                get_task.cancel()
                # Client disconnected.
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] follow loop ended for {}: {}", session_id, exc)
    finally:
        conn.unbind_sink(session_id)
        if not watch_task.done():
            watch_task.cancel()
        await asyncio.gather(watch_task, return_exceptions=True)
        await _end(None)
