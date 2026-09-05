"""HTTP reverse-proxy over the node's ``NodeConnect`` stream.

Port of ``pkg/agentcompose/api/node_tunnel.go``. A session-local HTTP service
(jupyter, a files endpoint, an arbitrary port) is reached by turning an inbound
HTTP request into a ``NodeTunnelRequest``, pushing it down the owning node's
already-established outbound stream, and streaming the node's
``NodeTunnelResponse`` chunks back to the client. The node is always the dialer,
so the server never connects inward — the tunnel rides the one bidi stream,
multiplexed by ``tunnel_id``.

Mounted at ``/api/nodes/sessions/{session_id}/{service}/{sub_path:path}``.
"""
from __future__ import annotations

import asyncio
import hmac
import uuid

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
from loguru import logger

from . import agentcompose_v2_pb2 as pb
from . import crypto
from .service import NodeService

# Bounds how much request body the proxy reads before forwarding it in a single
# tunnel request (guards against an unbounded body in server memory).
TUNNEL_REQUEST_BODY_LIMIT = 32 << 20  # 32 MiB

# How long the proxy waits for the node to begin (and keep) responding on a
# tunnel before giving up — reset on every chunk (idle timeout).
TUNNEL_RESPONSE_TIMEOUT = 60.0  # seconds


async def proxy_session_request(
    svc: NodeService,
    *,
    session_id: str,
    service: str,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> Response:
    """Dispatch one already-authorized request through a session tunnel.

    Route layers own authentication/ownership. Keeping the transport primitive
    separate lets the editor facade reuse the exact node tunnel without making an
    internal HTTP self-request (or exposing node_session_id to the browser).
    """
    session_id = (session_id or "").strip()
    service = (service or "").strip()
    if not session_id or not service:
        return Response("session id and service are required", status_code=400)
    binding = await svc.store.get_session_node(session_id)
    if binding is None:
        return Response(f"session {session_id} is not placed on any node", status_code=404)
    conn = svc.registry.lookup(binding.node_id)
    if conn is None:
        return Response(f"node {binding.node_id} for session {session_id} is offline", status_code=502)
    if len(body) > TUNNEL_REQUEST_BODY_LIMIT:
        body = body[:TUNNEL_REQUEST_BODY_LIMIT]

    tunnel_id = str(uuid.uuid4())
    resp_ch = conn.open_tunnel(tunnel_id)
    frame = pb.NodeDownstreamFrame(
        server_frame_id=str(uuid.uuid4()),
        created_at=crypto.rfc3339nano(crypto.utc_now()),
    )
    frame.tunnel_request.CopyFrom(
        pb.NodeTunnelRequest(
            tunnel_id=tunnel_id,
            session_id=session_id,
            service=service,
            method=method,
            path=path if path.startswith("/") else "/" + path,
            headers=headers or {},
            body=body,
            body_complete=True,
        )
    )
    try:
        conn.send(frame)
    except Exception as exc:  # noqa: BLE001
        conn.close_tunnel(tunnel_id)
        return Response(f"dispatch tunnel to node {binding.node_id}: {exc}", status_code=502)

    first = await _await_first(resp_ch)
    if first is None:
        conn.close_tunnel(tunnel_id)
        return Response("node did not respond in time", status_code=504)
    if (first.error or "").strip():
        conn.close_tunnel(tunnel_id)
        return Response(first.error, status_code=502)

    status = int(first.status) or 200
    resp_headers = {k: v for k, v in first.headers.items()}
    for h in ("content-length", "transfer-encoding", "connection"):
        resp_headers.pop(h, None)
        resp_headers.pop(h.title(), None)

    async def body_iter():
        try:
            if first.body:
                yield bytes(first.body)
            if first.done:
                return
            while True:
                try:
                    chunk = await asyncio.wait_for(resp_ch.get(), timeout=TUNNEL_RESPONSE_TIMEOUT)
                except asyncio.TimeoutError:
                    return
                if chunk is None:
                    return
                if chunk.body:
                    yield bytes(chunk.body)
                if chunk.done:
                    return
        finally:
            conn.close_tunnel(tunnel_id)

    return StreamingResponse(body_iter(), status_code=status, headers=resp_headers)


def build_tunnel_router(get_service, *, api_token: str = "", control_plane: bool = False) -> APIRouter:
    """Build the tunnel router for the live control service."""
    router = APIRouter(tags=["agent-compose-tunnel"])
    expected_token = (api_token or "").strip()

    def _authorized(request: Request) -> bool:
        if not expected_token:
            return True
        header = request.headers.get("authorization", "")
        return header.startswith("Bearer ") and hmac.compare_digest(
            header[7:].strip(), expected_token
        )

    @router.api_route(
        "/api/nodes/sessions/{session_id}/{service}/{sub_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def serve_session(session_id: str, service: str, sub_path: str, request: Request):
        svc: NodeService | None = get_service()
        if svc is None:
            return Response("node tunnel gateway is unavailable", status_code=503)
        if not _authorized(request):
            return Response("invalid or missing bearer token", status_code=403)
        session_id = (session_id or "").strip()
        service = (service or "").strip()
        if not session_id or not service:
            return Response("session id and service are required", status_code=400)

        # The raw transport remains an internal compatibility surface. Browser-
        # facing editor routes use an ownership-checked facade and call
        # proxy_session_request directly.
        body = await request.body()
        path = sub_path if sub_path.startswith("/") else "/" + sub_path
        if request.url.query.strip():
            path = f"{path}?{request.url.query}"
        return await proxy_session_request(
            svc,
            session_id=session_id,
            service=service,
            method=request.method,
            path=path,
            headers={k: v for k, v in request.headers.items()},
            body=body,
        )

    return router


async def _await_first(resp_ch: asyncio.Queue):
    """Await the first tunnel response chunk within the response timeout."""
    try:
        return await asyncio.wait_for(resp_ch.get(), timeout=TUNNEL_RESPONSE_TIMEOUT)
    except asyncio.TimeoutError:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] tunnel await-first failed: {}", exc)
        return None
