"""NodeConnectManager: drive the node forward HTTP proxy (node mode).

Sits on top of the node registry (Connection objects). Provides a high-level
API for asking a node to perform one outbound HTTP request to an absolute URL
on the server's behalf, then streaming the node's HTTP response back.

The node is a pure I/O relay: it terminates TLS with its own HTTP client and
applies no business logic. The request descriptor (method/url/headers/body)
travels down as a ``NodeProxyRequest``; the response streams back up as
``NodeTunnelResponse`` frames (same shape as the reverse-proxy response),
multiplexed over the single NodeConnect stream by ``tunnel_id``.

Used by RequestInstance._request_via_node() for node-mode proxy.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import AsyncIterator, Optional

from loguru import logger

from . import agentcompose_v2_pb2 as pb
from . import crypto
from .registry import Connection, Registry

# How long the server waits for the node to begin (and keep) responding on a
# proxy tunnel before giving up — reset on every chunk (idle timeout).
PROXY_RESPONSE_TIMEOUT = 120.0

# 长连接流（SSE）的空闲上限。SSE 合法地可以长时间无数据（MCP 会话空闲时不发事件），
# 用 120s 会把节点托管 MCP 的连接切断，所以流式响应改用这个更宽的空闲上限；仍保留
# 上限而非无限等待，避免节点静默死亡后隧道队列永久挂住。
STREAM_RESPONSE_TIMEOUT = 3600.0


def _is_streaming(headers: dict) -> bool:
    """响应是否为开放式流（SSE）。据此选空闲超时，见 STREAM_RESPONSE_TIMEOUT。"""
    for key, value in (headers or {}).items():
        if key.lower() == "content-type" and "text/event-stream" in str(value).lower():
            return True
    return False


class NodeProxyTunnel:
    """One forward-HTTP-proxy request/response exchange over a node.

    Wraps a ``NodeProxyRequest`` → ``NodeTunnelResponse`` stream exchange,
    correlated by ``tunnel_id``. The first response frame carries status +
    headers; subsequent frames are body chunks; the frame with ``done`` ends
    the response.
    """

    def __init__(self, conn: Connection):
        self.tunnel_id = str(uuid.uuid4())
        self._conn = conn
        self._recv_queue: asyncio.Queue = conn.open_tunnel(self.tunnel_id)
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        body: bytes = b"",
    ) -> "NodeProxyResponse":
        """Send the request descriptor and await the first response frame.

        Returns a NodeProxyResponse whose status/headers come from the first
        frame; its body streams from subsequent frames.
        """
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.proxy_request.CopyFrom(
            pb.NodeProxyRequest(
                tunnel_id=self.tunnel_id,
                method=method,
                url=url,
                headers=headers or {},
                body=body,
                body_complete=True,
            )
        )
        try:
            self._conn.send(frame)
        except Exception:
            self._close()
            raise

        first = await _await_first(self._recv_queue)
        if first is None:
            self._close()
            raise ConnectionError("node did not respond to proxy request in time")
        if (first.error or "").strip():
            self._close()
            raise ConnectionError(f"node proxy request failed: {first.error}")

        return NodeProxyResponse(self, first)

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._conn.close_tunnel(self.tunnel_id)
        except Exception:
            pass


class NodeProxyResponse:
    """The node's HTTP response: status/headers + a streaming body."""

    def __init__(self, tunnel: NodeProxyTunnel, first: "pb.NodeTunnelResponse"):
        self._tunnel = tunnel
        self.status: int = int(first.status) or 200
        self.headers: dict = {k: v for k, v in first.headers.items()}
        self._first = first
        # SSE 等流式响应用更宽的空闲上限，否则空闲的 MCP 会话会被 120s 切断
        self._idle_timeout = (
            STREAM_RESPONSE_TIMEOUT if _is_streaming(self.headers) else PROXY_RESPONSE_TIMEOUT
        )

    async def iter_chunks(self) -> AsyncIterator[bytes]:
        """Yield body chunks until the response is done."""
        try:
            if self._first.body:
                yield bytes(self._first.body)
            if self._first.done:
                return
            while True:
                chunk = await _await_next(self._tunnel._recv_queue, self._idle_timeout)
                if chunk is None:
                    return
                if (chunk.error or "").strip():
                    raise ConnectionError(f"node proxy stream error: {chunk.error}")
                if chunk.body:
                    yield bytes(chunk.body)
                if chunk.done:
                    return
        finally:
            self._tunnel._close()

    async def close(self) -> None:
        """Stop receiving this response and release its tunnel queue."""
        self._tunnel._close()


async def _await_first(queue: asyncio.Queue) -> Optional["pb.NodeTunnelResponse"]:
    try:
        return await asyncio.wait_for(queue.get(), timeout=PROXY_RESPONSE_TIMEOUT)
    except asyncio.TimeoutError:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] proxy await-first failed: {}", exc)
        return None


async def _await_next(
    queue: asyncio.Queue, timeout: float = PROXY_RESPONSE_TIMEOUT
) -> Optional["pb.NodeTunnelResponse"]:
    try:
        return await asyncio.wait_for(queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("[nodeserver] proxy await-next failed: {}", exc)
        return None


class NodeConnectManager:
    """Manage forward-HTTP-proxy exchanges over nodes.

    Wraps the node registry and provides request(): ask a node to perform one
    outbound HTTP request and stream the response back.
    """

    def __init__(self, registry: Registry):
        self._registry = registry

    def _get_conn(self, node_id: str) -> Connection:
        conn = self._registry.lookup(node_id)
        if conn is None or conn.closed:
            raise ConnectionError(f"node {node_id} is not connected")
        return conn

    async def request(
        self,
        node_id: str,
        *,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        body: bytes = b"",
    ) -> NodeProxyResponse:
        """Ask ``node_id`` to perform an HTTP request to ``url`` and return the
        streamed response. Raises ConnectionError if the node is offline."""
        conn = self._get_conn(node_id)
        tunnel = NodeProxyTunnel(conn)
        try:
            return await tunnel.request(method=method, url=url, headers=headers, body=body)
        except Exception:
            tunnel._close()
            raise
