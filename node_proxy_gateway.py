"""Cross-process node forward-proxy: control endpoint + data-side client.

The live NodeConnect stream lives only in the control process, so the data
process cannot drive the node proxy directly. This module keeps the same
``status`` / ``headers`` / ``iter_chunks()`` / ``close()`` surface the local
:class:`NodeProxyResponse` exposes, but backs it with an HTTP stream to the
control process:

* control side — :func:`build_node_proxy_router` mounts
  ``POST /internal/node-proxy/{node_id}`` (internal Bearer token). The request
  body is a small JSON descriptor (method/url/headers/body-b64/timeout); the
  response streams the node's bytes back with the node status/headers projected
  into response headers.
* data side — :class:`RemoteNodeConnectManager` mirrors
  :class:`NodeConnectManager.request` and returns a :class:`RemoteNodeProxyResponse`
  that streams chunks off the HTTP body.
"""
from __future__ import annotations

import base64
import hmac
import json
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

# The node status/headers are projected into these response headers so the data
# side can reconstruct the response without reading the streamed body first.
_STATUS_HEADER = "x-node-proxy-status"
_HEADERS_HEADER = "x-node-proxy-headers"
_REQUEST_BODY_LIMIT = 32 << 20  # match the node tunnel request bound
_RESPONSE_HEADERS_LIMIT = 32 << 10


def build_node_proxy_router(get_service, token: str) -> APIRouter:
    """Mount the internal node forward-proxy streaming endpoint (control side)."""
    router = APIRouter(tags=["internal-node-proxy"])
    expected = (token or "").strip()

    def _authorized(request: Request) -> bool:
        if not expected:
            return True
        header = request.headers.get("authorization", "")
        return header.startswith("Bearer ") and hmac.compare_digest(header[7:].strip(), expected)

    @router.post("/internal/node-proxy/{node_id}")
    async def node_proxy(node_id: str, request: Request):
        if not _authorized(request):
            return JSONResponse(status_code=403, content={"message": "invalid or missing bearer token"})
        service = get_service()
        if service is None:
            return JSONResponse(status_code=503, content={"message": "node service unavailable"})
        from .node_connect_manager import NodeConnectManager

        try:
            descriptor = json.loads((await request.body()) or b"{}")
        except (TypeError, ValueError):
            return JSONResponse(status_code=400, content={"message": "invalid descriptor"})

        manager = NodeConnectManager(service.registry)
        body = base64.b64decode(descriptor.get("body") or "")
        try:
            proxy_resp = await manager.request(
                node_id,
                method=descriptor.get("method") or "GET",
                url=descriptor.get("url") or "",
                headers=descriptor.get("headers") or {},
                body=body,
            )
        except ConnectionError as exc:
            return JSONResponse(status_code=502, content={"message": str(exc)})

        async def stream() -> AsyncIterator[bytes]:
            try:
                async for chunk in proxy_resp.iter_chunks():
                    yield chunk
            finally:
                await proxy_resp.close()

        headers = {
            _STATUS_HEADER: str(proxy_resp.status),
            _HEADERS_HEADER: json.dumps(proxy_resp.headers),
        }
        return StreamingResponse(stream(), status_code=200, headers=headers)

    return router


class RemoteNodeProxyResponse:
    """Data-side view over the control node-proxy HTTP stream.

    Mirrors :class:`NodeProxyResponse`: ``status`` / ``headers`` /
    ``iter_chunks()`` / ``close()``.
    """

    def __init__(self, session, response, status: int, headers: dict):
        self._session = session
        self._response = response
        self.status = status
        self.headers = headers
        self._closed = False

    async def iter_chunks(self) -> AsyncIterator[bytes]:
        try:
            async for chunk in self._response.content.iter_chunked(64 * 1024):
                yield chunk
        finally:
            await self.close()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._response.release()
        except Exception:  # noqa: BLE001
            pass
        try:
            await self._session.close()
        except Exception:  # noqa: BLE001
            pass


class RemoteNodeConnectManager:
    """Data-role stand-in for :class:`NodeConnectManager` over HTTP."""

    def __init__(self, *, base_url: str, token: str, timeout: float = 120.0):
        self._base_url = (base_url or "").rstrip("/")
        self._token = (token or "").strip()
        self._timeout = timeout

    async def request(
        self,
        node_id: str,
        *,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        body: bytes = b"",
    ) -> RemoteNodeProxyResponse:
        if not self._base_url or not self._token:
            raise ConnectionError("control plane node proxy is not configured")
        import aiohttp

        descriptor = {
            "method": method,
            "url": url,
            "headers": headers or {},
            "body": base64.b64encode(body or b"").decode("ascii"),
        }
        endpoint = f"{self._base_url}/internal/node-proxy/{node_id}"
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, sock_read=self._timeout))
        try:
            response = await session.post(
                endpoint,
                json=descriptor,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except Exception:
            await session.close()
            raise ConnectionError("control plane node proxy unreachable")
        if response.status >= 400:
            message = (await response.text())[:500]
            response.release()
            await session.close()
            raise ConnectionError(f"node proxy failed: HTTP {response.status} {message}")
        try:
            status = int(response.headers.get(_STATUS_HEADER) or 200)
            headers = json.loads(response.headers.get(_HEADERS_HEADER) or "{}")
        except (TypeError, ValueError):
            status, headers = 200, {}
        return RemoteNodeProxyResponse(session, response, status, headers)
