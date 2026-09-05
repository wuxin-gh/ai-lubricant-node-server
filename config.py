"""Independent configuration for the node control service, loaded from .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote

from loguru import logger

_TRUE = {"1", "true", "yes", "on"}


def _value(env: str, default: str = "", legacy: str | None = None) -> str:
    """Read ``env``; fall back to a pre-rebrand ``legacy`` name with a warning."""
    raw = os.getenv(env)
    value = raw.strip() if raw is not None and raw.strip() else ""
    if value or legacy is None:
        return value or default
    legacy_raw = os.getenv(legacy)
    legacy_value = legacy_raw.strip() if legacy_raw is not None and legacy_raw.strip() else ""
    if legacy_value:
        logger.warning("[node-server] legacy env {} used; rename to {}", legacy, env)
        return legacy_value
    return default


def _value_first(envs: tuple[str, ...], default: str = "") -> str:
    for env in envs:
        value = _value(env)
        if value:
            return value
    return default


def _integer(env: str, default: int) -> int:
    try:
        return int(_value(env, str(default)))
    except (TypeError, ValueError):
        return default


def _floating(env: str, default: float) -> float:
    try:
        return float(_value(env, str(default)))
    except (TypeError, ValueError):
        return default


def _boolean(env: str, default: bool) -> bool:
    raw = os.getenv(env)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in _TRUE


@dataclass(frozen=True)
class NodeServerSettings:
    database_url: str
    clickhouse_addr: str
    clickhouse_database: str
    clickhouse_username: str
    clickhouse_password: str
    node_server_enabled: bool
    node_credential_encryption_key: str
    node_control_token: str
    node_server_public_url: str
    agent_compose_agent_image: str
    agent_compose_node_bin_dir: str
    node_default_session_cpu: float
    node_default_session_memory: int
    host: str
    port: int
    node_terminal_max_active_per_node: int
    node_terminal_detached_ttl_seconds: float


def load_settings() -> NodeServerSettings:
    database_url = _value("AI_LUBRICANT_DATABASE_URL", legacy="MONKEYCODE_DATABASE_URL")
    if not database_url:
        user = quote(_value("POSTGRES_USER"), safe="")
        password = quote(_value("POSTGRES_PASSWORD"), safe="")
        host = _value("POSTGRES_HOST", "127.0.0.1")
        port = _integer("POSTGRES_PORT", 5432)
        database = _value("POSTGRES_DATABASE", "ai-lubricant")
        database_url = f"asyncpg://{user}:{password}@{host}:{port}/{database}"
    return NodeServerSettings(
        database_url=database_url,
        clickhouse_addr=_value("CLICKHOUSE_ADDR", ""),
        clickhouse_database=_value("CLICKHOUSE_DATABASE", "ai_lubricant_logs"),
        clickhouse_username=_value("CLICKHOUSE_USERNAME", ""),
        clickhouse_password=_value("CLICKHOUSE_PASSWORD", ""),
        node_server_enabled=_boolean("AGENT_COMPOSE_NODE_SERVER_ENABLED", True),
        node_credential_encryption_key=_value_first(("NODE_CREDENTIAL_ENCRYPTION_KEY",)),
        node_control_token=_value_first(("NODE_CONTROL_TOKEN",)),
        node_server_public_url=_value("AGENT_COMPOSE_NODE_SERVER_PUBLIC_URL"),
        agent_compose_agent_image=_value("AGENT_COMPOSE_AGENT_IMAGE", "ai-lubricant-node:local"),
        agent_compose_node_bin_dir=_value("AGENT_COMPOSE_NODE_BIN_DIR"),
        node_default_session_cpu=max(0.0, _floating("NODE_DEFAULT_SESSION_CPU", 1.0)),
        node_default_session_memory=max(0, _integer("NODE_DEFAULT_SESSION_MEMORY", 1 << 30)),
        host=_value("NODE_CONTROL_HOST", "0.0.0.0"),
        port=_integer("NODE_CONTROL_PORT", 8003),
        node_terminal_max_active_per_node=max(1, _integer("NODE_TERMINAL_MAX_ACTIVE_PER_NODE", 10)),
        node_terminal_detached_ttl_seconds=max(60.0, _floating("NODE_TERMINAL_DETACHED_TTL_SECONDS", 1800.0)),
    )


settings = load_settings()


def reload_settings() -> NodeServerSettings:
    global settings
    settings = load_settings()
    return settings
