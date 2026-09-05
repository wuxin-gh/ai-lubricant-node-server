"""Standalone access to the shared PostgreSQL the data service owns.

node_server runs as its own process and owns its Tortoise ledger (``mc_ac_*``).
The task/config-domain rows it must reach (``mc_tasks``, ``mc_task_events``,
``mcp_users``, ``app_config``, git identities, notify outbox) live in the same
PostgreSQL database but belong to the data service's domain. Reaching them
needs only a plain asyncpg pool plus a handful of small readers/writers over
raw SQL — this module provides exactly that, with **no import of the data
service's code**, so the control plane stays a self-contained package.

What lives here and why:

* :func:`init` / :func:`close` — an asyncpg pool built from this service's own
  ``database_url`` setting. Table creation is deliberately NOT done here: the
  domain tables are the data service's, and it creates them idempotently on its
  own startup. In any deployment where both processes run (the only supported
  topology) the tables exist before tasks do; if the control plane starts first
  against an empty database the best-effort writers below simply no-op.
* :func:`read_main_config` — the proxy pool lives in the main config row
  (``app_config`` table, key ``main``). A direct SELECT replaces the data
  service's cached config store; the control plane reads it rarely (node
  onboarding / proxy binding), so no cache is warranted.
* :func:`resolve_proxy_fields` — map one proxy-pool entry to the three
  ``proxy_*`` fields carried by upgrade/connect frames. This is the control
  plane's own copy of the mapping (the data service has an equivalent in its
  upgrade path); the two must stay behaviourally in sync.
* :func:`enqueue_notification` — append one pending row to ``mc_notify_outbox``.
  The data service's worker drains that table and performs the actual channel
  delivery (in-app bell, webhooks), so nothing but the row is needed here.

Everything is best-effort / never raises where the caller must not be
disturbed; the SQL text mirrors the data service's schemas exactly (same
tables, same columns) so both processes agree on one database.
"""
from __future__ import annotations

import json
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

import asyncpg
from loguru import logger

_pool: asyncpg.Pool | None = None


def pool() -> asyncpg.Pool | None:
    return _pool


async def init(database_url: str) -> None:
    """Build the pool from the service's own ``database_url`` setting.

    Settings carry the Tortoise-style ``asyncpg://`` DSN, but the raw asyncpg
    driver only accepts ``postgres://`` / ``postgresql://`` — rewrite the
    scheme before handing it to :func:`asyncpg.create_pool`.
    """
    global _pool
    if _pool is not None:
        return
    if not (database_url or "").strip():
        logger.warning("[nodeserver] shared database url not set; task/config rows unreachable")
        return
    parts = urlsplit(database_url)
    if parts.scheme in ("asyncpg", "postgres+asyncpg"):
        database_url = urlunsplit(("postgresql",) + parts[1:])
    try:
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
        logger.info("[nodeserver] shared postgres pool ready")
    except Exception:  # noqa: BLE001
        logger.exception("[nodeserver] shared postgres pool init failed")


async def close() -> None:
    global _pool
    if _pool is None:
        return
    try:
        await _pool.close()
    except Exception:  # noqa: BLE001
        logger.debug("[nodeserver] shared postgres pool close failed", exc_info=True)
    _pool = None


# ── main config (proxy pool) ────────────────────────────────────────────────
async def read_main_config() -> dict:
    """Read the ``main`` row from ``app_config``; empty dict when unreachable.

    The proxy pool is ``main["proxies"]``. Raises nothing: callers treat an
    unreadable config as "no proxy" and degrade to a direct connection.
    """
    if _pool is None:
        return {}
    try:
        async with _pool.acquire() as conn:
            value = await conn.fetchval("SELECT data FROM app_config WHERE key='main'")
    except Exception:  # noqa: BLE001
        logger.exception("[nodeserver] read main config failed")
        return {}
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
    return dict(value)


class ProxyResolveError(ValueError):
    """A proxy-pool entry could not be resolved. Message is user-facing."""


# Proxy modes: network = classic CONNECT/forward proxy (aiohttp proxy=);
# url_prefix = prepend-prefix forwarding (the full upstream URL is appended to
# a base address); direct = explicitly no proxy. (``node`` tunnels through
# another execution node and is meaningless for the node's own egress, so it is
# rejected by the resolver below.)
_MODE_NETWORK = "network"
_MODE_URL_PREFIX = "url_prefix"
_MODE_DIRECT = "direct"
_VALID_MODES = {_MODE_NETWORK, _MODE_URL_PREFIX, _MODE_DIRECT}


def _find_entry(proxies: list, ref: str) -> dict | None:
    ref = (ref or "").strip()
    if not ref:
        return None
    for proxy in proxies or []:
        if isinstance(proxy, dict) and ref in {proxy.get("id"), proxy.get("name"), proxy.get("url")}:
            return proxy
    return None


def _entry_mode(entry: dict) -> str:
    mode = str(entry.get("mode") or "").strip().lower()
    return mode if mode in _VALID_MODES else _MODE_NETWORK


def _prefix_base(entry: dict) -> str:
    value = entry.get("url")
    if not isinstance(value, str):
        return ""
    return value.strip().rstrip("/") or ""


def _network_url(entry: dict) -> str:
    """network 模式的有效代理 URL（用户名/密码注入进 userinfo）。"""
    url = str(entry.get("url") or "").strip()
    username = str(entry.get("username") or "").strip()
    password = entry.get("password") or ""
    if not url or not username:
        return url
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc or not parts.hostname:
        return url
    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parts.port:
        host = f"{host}:{parts.port}"
    auth = quote(username, safe="")
    if password:
        auth += ":" + quote(str(password), safe="")
    return urlunsplit((parts.scheme, f"{auth}@{host}", parts.path, parts.query, parts.fragment))


async def resolve_proxy_fields(proxy_config_id: str) -> dict:
    """Resolve a proxy-pool entry id to the ``proxy_*`` frame fields.

    Returns ``{}`` for empty/unknown/direct. Raises :class:`ProxyResolveError`
    for entries that cannot back a node's own download (``node`` mode, or a
    network/url_prefix entry without an address) — the admin path surfaces the
    message, the connect path degrades to direct.
    """
    wanted = (proxy_config_id or "").strip()
    if not wanted:
        return {}
    main = await read_main_config()
    entry = _find_entry(main.get("proxies") if isinstance(main, dict) else None, wanted)
    if entry is None:
        raise ProxyResolveError(f"代理配置 {wanted} 不存在")
    raw_mode = str(entry.get("mode") or "").strip().lower()
    if raw_mode == "node":
        raise ProxyResolveError("节点隧道代理不能用于节点自身下载，请选择网络代理或 URL 前缀代理")
    mode = _entry_mode(entry)
    if mode == _MODE_DIRECT:
        return {}
    if mode == _MODE_URL_PREFIX:
        prefix = _prefix_base(entry)
        if not prefix:
            raise ProxyResolveError("URL 前缀代理未配置前缀地址")
        return {"proxy_mode": "url_prefix", "proxy_url_prefix": prefix}
    url = _network_url(entry)
    if not url:
        raise ProxyResolveError("网络代理未配置地址")
    return {"proxy_mode": "network", "proxy_url": url}


# ── notify outbox ───────────────────────────────────────────────────────────
async def enqueue_notification(
    *,
    event_type: str,
    params: dict,
    envelope: dict,
    owner_type: str,
    owner_id: object,
) -> str | None:
    """Append one pending row to ``mc_notify_outbox``; never raises.

    The data service's worker drains this table and performs channel delivery
    (in-app bell, webhooks), so writing the row is all the control plane does.
    Mirrors the data service's outbox insert (same columns) so both writers
    produce interchangeable rows.
    """
    if _pool is None:
        return None
    oid = uuid.uuid4()
    try:
        owner = None
        if owner_id is not None:
            text = str(owner_id)
            try:
                owner = uuid.UUID(text)
            except (ValueError, AttributeError):
                owner = text
        async with _pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO mc_notify_outbox "
                "(id, notification_id, event_type, params, envelope, owner_type, owner_id, status) "
                "VALUES ($1, NULL, $2, $3::jsonb, $4::jsonb, $5, $6, 'pending')",
                oid,
                (event_type or "")[:64],
                json.dumps(params, ensure_ascii=False),
                json.dumps(envelope, ensure_ascii=False),
                (owner_type or "platform")[:16],
                owner,
            )
        return str(oid)
    except Exception:  # noqa: BLE001
        logger.exception("[nodeserver] notify outbox insert failed for {}", event_type)
        return None
