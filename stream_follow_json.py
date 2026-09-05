"""Raw ASGI handlers for NDJSON variants of the two follow server-streams.

These are internal endpoints for the data service's node client. The proto
variants (``FollowNodeSession`` / ``FollowToolRun`` in :mod:`.stream_follow` /
:mod:`.stream_follow_toolrun`) speak the Connect streaming framing (5-byte
envelope + protobuf), which forces a caller to link the generated protobuf
bindings. The data service must not do that, so these variants offer the same
event streams over plain NDJSON: one JSON object per line, ``text/event``
frames become lines, the stream ends after the terminal event.

Internally these handlers consume the same protobuf event objects as the
proto variants (the sinks enqueue ``pb.NodeSessionEvent`` /
``pb.NodeToolRunEvent``); the conversion to JSON-safe dicts happens here, on
the control-plane side, before anything crosses the process boundary.
"""
from __future__ import annotations

import asyncio
import base64
import json

from loguru import logger

from . import agentcompose_v2_pb2 as pb
from .service import NodeService, RPCError, Code

_NDJSON_HEADERS = [(b"content-type", b"application/x-ndjson")]

_KIND_TOOL_RUN = {
    pb.NODE_TOOL_RUN_KIND_STDOUT: "stdout",
    pb.NODE_TOOL_RUN_KIND_STDERR: "stderr",
    pb.NODE_TOOL_RUN_KIND_EXITED: "exited",
    pb.NODE_TOOL_RUN_KIND_STARTED: "started",
}


def session_event_to_dict(evt: "pb.NodeSessionEvent") -> dict | None:
    """Project one protobuf ``NodeSessionEvent`` onto a JSON-safe dict.

    ``payload_json`` is parsed here so the consumer gets a real object instead
    of a JSON-string-inside-JSON; an unparseable payload degrades to raw text.

    The canonical envelope fields (``logical_event_id``/``event_name``/
    ``event_kind``/``tool_name``/``subagent_id``/``phase``/``status``) are passed
    through verbatim: they are filled once by the runtime and normalized at the
    node boundary, so every consumer downstream routes on them instead of
    re-deriving intent from a provider's payload.
    """
    which = evt.WhichOneof("event")
    if which == "output":
        out = evt.output
        return {
            "kind": "output",
            "session_id": out.session_id,
            "stream": "stderr" if out.stream == 2 else "stdout",
            "offset": out.offset,
            "text": out.data.decode("utf-8", "replace"),
            "created_at": out.created_at,
        }
    if which == "structured":
        item = evt.structured
        payload: object = None
        if item.payload_json:
            try:
                payload = json.loads(item.payload_json)
            except (ValueError, TypeError):
                payload = {"raw": item.payload_json}
        return {
            "kind": "structured",
            "session_id": item.session_id,
            "seq": item.seq,
            "event_type": item.event_type,
            "item_type": item.item_type,
            "agent_id": item.agent_id,
            "logical_event_id": item.logical_event_id,
            "event_name": item.event_name,
            "event_kind": item.event_kind,
            "tool_name": item.tool_name,
            "subagent_id": item.subagent_id,
            "phase": item.phase,
            "status": item.status,
            "payload": payload,
            "created_at": item.created_at,
        }
    if which == "result":
        res = evt.result
        return {
            "kind": "result",
            "session_id": res.session_id,
            "exit_code": res.exit_code,
            "success": res.success,
            "error": res.error,
        }
    return None


def tool_run_event_to_dict(evt: "pb.NodeToolRunEvent") -> dict:
    """Project one protobuf ``NodeToolRunEvent`` onto a JSON-safe dict.

    ``data`` is base64-encoded because JSON cannot carry raw bytes; the client
    decodes it back before handing the event to consumers.
    """
    return {
        "kind": _KIND_TOOL_RUN.get(evt.kind, "unknown"),
        "data": base64.b64encode(bytes(evt.data)).decode("ascii"),
        "exit_code": int(evt.exit_code),
        "error": evt.error or "",
        "revision": int(evt.revision or 0),
        "pid": int(evt.pid or 0),
    }


def _bearer_ok(scope: dict, api_token: str) -> bool:
    """Match the unary router's Bearer check for the ASGI surface."""
    import hmac

    expected = (api_token or "").strip()
    if not expected:
        return True
    for key, value in scope.get("headers") or []:
        if key.decode("latin-1").lower() != "authorization":
            continue
        header = value.decode("latin-1")
        prefix = "Bearer "
        if header.startswith(prefix):
            return hmac.compare_digest(header[len(prefix):].strip(), expected)
    return False


async def _read_json_body(receive) -> dict | None:
    """Accumulate the request body and parse it as one JSON object."""
    body = bytearray()
    eof = False
    while True:
        if eof:
            break
        event = await receive()
        etype = event.get("type")
        if etype == "http.disconnect":
            return None
        if etype != "http.request":
            continue
        body.extend(event.get("body") or b"")
        if not event.get("more_body", False):
            eof = True
    if not body:
        return {}
    try:
        parsed = json.loads(bytes(body).decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


async def _send_line(send, obj: dict) -> None:
    await send(
        {
            "type": "http.response.body",
            "body": (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"),
            "more_body": True,
        }
    )


async def follow_node_session_json_asgi(
    scope: dict, receive, send, service: NodeService, *, api_token: str = ""
) -> None:
    """ASGI handler for the NDJSON variant of ``FollowNodeSession``."""
    if scope.get("type") != "http":  # pragma: no cover - mount guards this
        return
    if scope.get("method") != "POST" or not _bearer_ok(scope, api_token):
        await send({"type": "http.response.start", "status": 405 if scope.get("method") != "POST" else 403, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        return

    await send({"type": "http.response.start", "status": 200, "headers": _NDJSON_HEADERS})

    async def _end(error: "RPCError | None") -> None:
        # Errors land on the stream (the status line is already sent); the
        # client treats a line without ``kind`` as end-of-stream.
        if error is not None:
            try:
                await _send_line(send, {"error": {"code": error.code, "message": error.message}})
            except Exception:  # noqa: BLE001
                pass
        try:
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        except Exception:  # noqa: BLE001
            pass

    try:
        payload = await _read_json_body(receive)
        if payload is None:
            await _end(RPCError(Code.INVALID_ARGUMENT, "follow session: invalid JSON body"))
            return
        session_id = str(payload.get("sessionId") or "").strip()
        if not session_id:
            await _end(RPCError(Code.INVALID_ARGUMENT, "follow session: sessionId is required"))
            return
        conn, session_id = await service.resolve_follow(session_id)
    except RPCError as exc:
        await _end(exc)
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("[nodeserver] follow-json resolve failed")
        await _end(RPCError(Code.INTERNAL, str(exc)))
        return

    from .registry import OutputSink

    loop = asyncio.get_event_loop()
    events: asyncio.Queue = asyncio.Queue(maxsize=256)

    def _enqueue(evt: "pb.NodeSessionEvent") -> None:
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
                decoded = session_event_to_dict(evt)
                if decoded is not None:
                    await _send_line(send, decoded)
                if evt.WhichOneof("event") == "result":
                    break
            else:
                get_task.cancel()
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] follow-json loop ended for {}: {}", session_id, exc)
    finally:
        conn.unbind_sink(session_id)
        if not watch_task.done():
            watch_task.cancel()
        await asyncio.gather(watch_task, return_exceptions=True)
        await _end(None)


async def follow_tool_run_json_asgi(
    scope: dict, receive, send, service: NodeService, *, api_token: str = ""
) -> None:
    """ASGI handler for the NDJSON variant of ``FollowToolRun``."""
    if scope.get("type") != "http":  # pragma: no cover - mount guards this
        return
    if scope.get("method") != "POST" or not _bearer_ok(scope, api_token):
        await send({"type": "http.response.start", "status": 405 if scope.get("method") != "POST" else 403, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        return

    await send({"type": "http.response.start", "status": 200, "headers": _NDJSON_HEADERS})

    async def _end(error: "RPCError | None") -> None:
        if error is not None:
            try:
                await _send_line(send, {"error": {"code": error.code, "message": error.message}})
            except Exception:  # noqa: BLE001
                pass
        try:
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        except Exception:  # noqa: BLE001
            pass

    try:
        payload = await _read_json_body(receive)
        if payload is None:
            await _end(RPCError(Code.INVALID_ARGUMENT, "follow tool run: invalid JSON body"))
            return
        node_id = str(payload.get("nodeId") or "").strip()
        run_id = str(payload.get("runId") or "").strip()
        if not node_id or not run_id:
            await _end(RPCError(Code.INVALID_ARGUMENT, "nodeId and runId are required"))
            return
    except Exception as exc:  # noqa: BLE001
        await _end(RPCError(Code.INTERNAL, str(exc)))
        return

    try:
        events = service.open_tool_run(node_id, run_id)
    except RPCError as exc:
        await _end(exc)
        return
    except Exception as exc:  # noqa: BLE001
        await _end(RPCError(Code.INTERNAL, str(exc)))
        return

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
                await _send_line(send, tool_run_event_to_dict(evt))
                if evt.kind == pb.NODE_TOOL_RUN_KIND_EXITED:
                    break
            else:
                get_task.cancel()
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] follow-toolrun-json loop ended for {}: {}", run_id, exc)
    finally:
        service.close_tool_run(node_id, run_id)
        if not watch_task.done():
            watch_task.cancel()
        await asyncio.gather(watch_task, return_exceptions=True)
        await _end(None)
