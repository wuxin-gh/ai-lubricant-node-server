"""Compose and mount the standalone node control service."""
from __future__ import annotations

import asyncio
import secrets
from typing import Optional

from loguru import logger

from . import config, crypto
from .bootstrap_ini import update_ini_section
from .config import settings
from .registry import Registry
from .service import NodeService
from .store import node_store

_REAP_INTERVAL = 30.0
_REAP_TIMEOUT = 60.0
_service: Optional[NodeService] = None
_reaper_task: Optional[asyncio.Task] = None


def get_service() -> Optional[NodeService]:
    return _service


def _persist(section: str, key: str, value: str) -> None:
    """Persist a security-critical value to ``.env`` or refuse to start.

    An ephemeral master key would make sealed credentials undecryptable after
    restart; an ephemeral token would make the data service unable to reconnect.
    """
    env_name = _PERSIST_KEY_MAP.get((section, key))
    if not env_name:
        raise RuntimeError(f"cannot persist unknown {section}.{key}")
    try:
        update_ini_section(section, {env_name: value})
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"cannot persist {key} to .env: {exc}") from exc


_PERSIST_KEY_MAP = {
    ("ai_lubricant", "node_credential_encryption_key"): "NODE_CREDENTIAL_ENCRYPTION_KEY",
    ("ai_lubricant", "node_control_token"): "NODE_CONTROL_TOKEN",
}


def _master_key() -> bytes:
    raw = (settings.node_credential_encryption_key or "").strip()
    if raw:
        return crypto.parse_master_key(raw)
    generated = secrets.token_hex(32)
    _persist("ai_lubricant", "node_credential_encryption_key", generated)
    config.reload_settings()
    logger.info("[node-server] generated and persisted node_credential_encryption_key")
    return crypto.parse_master_key(generated)


def _api_token() -> str:
    raw = (settings.node_control_token or "").strip()
    if raw:
        return raw
    generated = secrets.token_urlsafe(32)
    _persist("ai_lubricant", "node_control_token", generated)
    config.reload_settings()
    logger.info("[node-server] generated and persisted node_control_token")
    return generated


def build_service() -> NodeService:
    global _service
    if _service is None:
        _service = NodeService(
            master_key=_master_key(),
            server_url=settings.node_server_public_url,
            store=node_store,
            registry=Registry(),
            agent_image=settings.agent_compose_agent_image,
        )
    return _service


def mount(app) -> bool:
    """Mount NodeConnect and token-gated internal control surfaces."""
    if not settings.node_server_enabled:
        return False
    service = build_service()
    api_token = _api_token()

    from .connect_stream import node_connect_asgi
    from .stream_follow import follow_node_session_asgi
    from .stream_follow_toolrun import follow_tool_run_asgi
    from .stream_follow_json import (
        follow_node_session_json_asgi,
        follow_tool_run_json_asgi,
    )
    from starlette.routing import Route

    class _NodeConnectASGI:
        async def __call__(self, scope, receive, send) -> None:
            if scope.get("type") == "http":
                await node_connect_asgi(scope, receive, send, service)

    class _FollowSessionASGI:
        async def __call__(self, scope, receive, send) -> None:
            if scope.get("type") == "http":
                await follow_node_session_asgi(scope, receive, send, service)

    class _FollowToolRunASGI:
        async def __call__(self, scope, receive, send) -> None:
            if scope.get("type") == "http":
                await follow_tool_run_asgi(scope, receive, send, service)

    class _FollowSessionJSONASGI:
        async def __call__(self, scope, receive, send) -> None:
            if scope.get("type") == "http":
                await follow_node_session_json_asgi(scope, receive, send, service, api_token=api_token)

    class _FollowToolRunJSONASGI:
        async def __call__(self, scope, receive, send) -> None:
            if scope.get("type") == "http":
                await follow_tool_run_json_asgi(scope, receive, send, service, api_token=api_token)

    app.router.routes.insert(0, Route(
        "/agentcompose.v2.NodeService/NodeConnect", _NodeConnectASGI(), methods=["POST"]
    ))
    app.router.routes.insert(1, Route(
        "/agentcompose.v2.NodeService/FollowNodeSession", _FollowSessionASGI(), methods=["POST"]
    ))
    app.router.routes.insert(2, Route(
        "/agentcompose.v2.NodeService/FollowToolRun", _FollowToolRunASGI(), methods=["POST"]
    ))
    # NDJSON variants of the two follow streams (for the data service's node
    # client, which must not link the generated protobuf bindings). Same events,
    # one JSON object per line instead of Connect envelope + protobuf.
    app.router.routes.insert(3, Route(
        "/agentcompose.v2.NodeService/FollowNodeSessionJSON", _FollowSessionJSONASGI(), methods=["POST"]
    ))
    app.router.routes.insert(4, Route(
        "/agentcompose.v2.NodeService/FollowToolRunJSON", _FollowToolRunJSONASGI(), methods=["POST"]
    ))

    from .scripts import build_scripts_router
    from .binaries import build_public_binaries_router
    from .git_proxy import build_git_proxy_router
    from .tunnel import build_tunnel_router
    from .terminal_gateway import build_control_terminal_router
    from .node_proxy_gateway import build_node_proxy_router
    from .unary_api import build_unary_router

    app.include_router(build_scripts_router(service))
    # Public binary/docker mirror. The node self-upgrades and one-click install
    # scripts fetch from THIS origin (the control service they connect to), so
    # the /api/v1/public/nodes/* download routes must live here, not only on the
    # data service.
    app.include_router(build_public_binaries_router())
    app.include_router(build_git_proxy_router())
    app.include_router(build_tunnel_router(get_service, api_token=api_token))
    app.include_router(build_control_terminal_router(service, api_token))
    app.include_router(build_node_proxy_router(get_service, api_token))
    app.include_router(build_unary_router(service, api_token=api_token))
    logger.info("[node-server] NodeService mounted (NodeConnect + tunnel + terminal + proxy + unary token-gated)")
    return True


async def start_reaper() -> None:
    global _reaper_task
    if _service is None or (_reaper_task is not None and not _reaper_task.done()):
        return
    _reaper_task = asyncio.create_task(_reaper_loop(), name="node-liveness-reaper")
    logger.info("[node-server] liveness reaper started")


async def _reaper_loop() -> None:
    from datetime import datetime, timezone

    while True:
        try:
            await asyncio.sleep(_REAP_INTERVAL)
            if _service is not None:
                stale = _service.registry.reap_stale(datetime.now(timezone.utc), _REAP_TIMEOUT)
                if stale:
                    logger.debug("[node-server] reaped stale connections: {}", stale)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.debug("[node-server] reaper tick failed: {}", exc)


async def stop_reaper() -> None:
    global _reaper_task
    if _reaper_task is None:
        return
    _reaper_task.cancel()
    await asyncio.gather(_reaper_task, return_exceptions=True)
    _reaper_task = None
