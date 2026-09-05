"""Raw ASGI handler for the ``FollowToolRun`` server-stream RPC.

Mirrors :mod:`.stream_follow` but for long-running external tool runs (tunnel
manager clients: frpc / cloudflared / npc). A client (the data-service
dispatcher) opens this Connect *server-stream* with one ``FollowToolRunRequest``
(node_id + run_id); the server replays the node's ``NodeToolRunEvent`` stream
as it arrives on the live connection's tool-run queue, and ends after the
``EXITED`` event (or when the node disconnects).

Used by the tunnel manager to capture cloudflared's trycloudflare domain from
the client's stdout (the one cloudflared quick-mode case where the public
address is minted at runtime rather than allocated up front).
"""
from __future__ import annotations

import asyncio

from loguru import logger

from . import agentcompose_v2_pb2 as pb
from . import envelope
from .service import NodeService, RPCError, Code


_ASGI_OK_HEADERS = [
    (b"content-type", envelope.CONTENT_TYPE.encode("ascii")),
    (b"connect-content-encoding", b"identity"),
]


async def _read_first_request(receive) -> "pb.FollowToolRunRequest | None":
    decoder = envelope.FrameDecoder()
    eof = False
    while True:
        frame = decoder.next_frame()
        if frame is not None:
            flags, payload = frame
            if flags & envelope.FLAG_END_STREAM:
                return None
            msg = pb.FollowToolRunRequest()
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


async def proxy_follow_toolrun_asgi(scope: dict, receive, send, *, base_url: str, token: str) -> None:
    """Pass the Connect server-stream through the data service unchanged."""
    if not (base_url or "").strip() or not (token or "").strip():
        await send({"type": "http.response.start", "status": 503, "headers": []})
        await send({"type": "http.response.body", "body": b"control plane unavailable", "more_body": False})
        return
    if scope["type"] != "http" or scope.get("method") != "POST":
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

    url = f"{base_url.rstrip('/')}/agentcompose.v2.NodeService/FollowToolRun"
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
        logger.debug("[nodeserver] follow-toolrun proxy ended")


async def follow_tool_run_asgi(scope: dict, receive, send, service: NodeService) -> None:
    """ASGI handler for one ``FollowToolRun`` server-stream."""
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

    try:
        req = await _read_first_request(receive)
        if req is None:
            await _end(RPCError(Code.INVALID_ARGUMENT, "follow tool run: stream closed before request"))
            return
        node_id = (req.node_id or "").strip()
        run_id = (req.run_id or "").strip()
        if not node_id or not run_id:
            await _end(RPCError(Code.INVALID_ARGUMENT, "node_id and run_id are required"))
            return
    except Exception as exc:  # noqa: BLE001
        await _end(RPCError(Code.INTERNAL, str(exc)))
        return

    # Open the event queue BEFORE we (the server) confirm the run exists. A
    # tool-run queue is created on demand; the node streams events into it as
    # they arrive. The queue lives on the connection; if the node is offline we
    # get an UNAVAILABLE and end cleanly.
    try:
        events = service.open_tool_run(node_id, run_id)
    except RPCError as exc:
        await _end(exc)
        return
    except Exception as exc:  # noqa: BLE001
        await _end(RPCError(Code.INTERNAL, str(exc)))
        return

    # Watch for client disconnect concurrently.
    loop = asyncio.get_event_loop()
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
                if evt is None:
                    # None sentinel: the node disconnected (close() woke us).
                    break
                await send(
                    {
                        "type": "http.response.body",
                        "body": envelope.encode_message(evt),
                        "more_body": True,
                    }
                )
                # EXITED is terminal for this run.
                if evt.kind == pb.NODE_TOOL_RUN_KIND_EXITED:
                    break
            else:
                get_task.cancel()
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] follow-toolrun loop ended for {}: {}", run_id, exc)
    finally:
        service.close_tool_run(node_id, run_id)
        if not watch_task.done():
            watch_task.cancel()
        await asyncio.gather(watch_task, return_exceptions=True)
        await _end(None)
