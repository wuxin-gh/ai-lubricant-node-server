"""Append-only ClickHouse store for a task's conversation content.

``shared_store`` reaches the data service's PostgreSQL over an asyncpg pool with
**no import of the data service's code** — that keeps the node control plane a
self-contained package. The same constraint applies here: conversation content
belongs in ClickHouse (state/index stays in PostgreSQL), but the node control
process has to write it *itself* — it cannot call into ``integrations.clickhouse``
because that module lives in the data service's tree.

So this is the node control plane's own minimal ``clickhouse-connect`` facade:
its own client, its own schema (mirrored on the data-service side by
``integrations.clickhouse.ClickHousePayloadClient.ensure_task_messages_schema``,
which runs at gateway startup), its own insert path. The two never share code;
they share only the SQL DDL text and the column order of the row, kept aligned
the same way ``message_status_machine`` / ``task_status_history`` are — by a
shared test (``test_task_messages_schema_parity``).

Write model is append-only: every runtime frame the node sees is one insert.
``ReplacingMergeTree(version)`` with ``ORDER BY (task_id, seq)`` collapses an
accidental re-insert of the same frame (same ``seq``) on a retry; reads take the
highest ``version`` (the largest ``seq`` seen for that key) via ``FINAL``. In
practice the frame loop allocates a fresh ``seq`` per frame and never retries,
so each frame stays its own row — the merge engine is just cheap insurance.

Never raises: this rides the same frame loop as ``record_session_event`` and
``task_finalize``; a ClickHouse hiccup must not drop live frames.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from loguru import logger

_client = None  # clickhouse-connect Client, or None when disabled/unconnected
_lock: asyncio.Lock | None = None


def _lock_obj() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


# Column order of one ``task_messages`` row. MUST match the DDL in both
# ``ensure_schema`` below and ``integrations.clickhouse.ensure_task_messages_schema``;
# ``tests/test_task_messages_schema_parity`` compares the two.
COLUMN_NAMES = [
    "id",
    "task_id",
    "logical_event_id",
    "seq",
    "item_type",
    "item_json",
    "agent_id",
    "subagent_id",
    "event_kind",
    "tool_name",
    "phase",
    "status",
    "created_at",
    "version",
]


_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS task_messages
(
    id String,
    task_id String,
    logical_event_id String,
    seq UInt64,
    item_type LowCardinality(String),
    item_json String CODEC(ZSTD(9)),
    agent_id String,
    subagent_id String,
    event_kind LowCardinality(String),
    tool_name String,
    phase LowCardinality(String),
    status LowCardinality(String),
    created_at DateTime64(3),
    version UInt64
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (task_id, seq)
TTL toDateTime(created_at) + INTERVAL 365 DAY
"""


def client():
    """The connected clickhouse-connect client, or ``None`` when not configured."""
    return _client


async def init(addr: str, *, database: str, username: str = "", password: str = "") -> None:
    """Connect to ClickHouse and ensure the ``task_messages`` schema exists.

    Empty ``addr`` means the deployment doesn't run ClickHouse — the store stays
    a no-op and writers fall back to the PostgreSQL payload column (see
    ``record_session_event``), so a CH-less install still renders history.
    """
    global _client
    if _client is not None:
        return
    addr = (addr or "").strip()
    if not addr:
        logger.info("[nodeserver] task_messages clickhouse addr not set; content stays in postgres")
        return
    try:
        import clickhouse_connect
    except Exception:  # noqa: BLE001
        logger.warning("[nodeserver] clickhouse-connect not installed; task_messages store disabled")
        return
    host, port = _parse_addr_local(addr)

    kwargs: dict[str, Any] = {
        "host": host,
        "database": database,
    }
    if port is not None:
        kwargs["port"] = port
    if username:
        kwargs["username"] = username
    if password:
        kwargs["password"] = password
    try:
        async with _lock_obj():
            _client = await asyncio.to_thread(clickhouse_connect.get_client, **kwargs)
            await asyncio.to_thread(_client.command, _SCHEMA_DDL)
        logger.info("[nodeserver] task_messages clickhouse ready, schema ensured")
    except Exception:  # noqa: BLE001
        logger.exception("[nodeserver] task_messages clickhouse init failed; content falls back to postgres")
        _client = None


async def close() -> None:
    global _client
    if _client is None:
        return
    client, _client = _client, None
    try:
        close = getattr(client, "close", None)
        if close is not None:
            await asyncio.to_thread(close)
    except Exception:  # noqa: BLE001
        logger.debug("[nodeserver] task_messages clickhouse close failed", exc_info=True)


def _parse_addr_local(addr: str) -> tuple[str, int | None]:
    """Minimal host[:port] split for environments without ``integrations.clickhouse``."""
    text = (addr or "").strip()
    if not text:
        return "", None
    if text.startswith("["):
        end = text.find("]")
        if end == -1:
            return text, None
        host = text[1:end]
        rest = text[end + 1:]
        if rest.startswith(":") and rest[1:].isdigit():
            return host, int(rest[1:])
        return host, None
    if text.count(":") > 1 and not text.rsplit(":", 1)[-1].isdigit():
        return text, None
    if ":" in text:
        host, _, port = text.rpartition(":")
        if port.isdigit():
            return host, int(port)
    return text, None


async def insert_task_message(row: list) -> bool:
    """Append one frame. Returns False (no-op) when CH is not connected.

    Serialized through the operation lock: clickhouse-connect's synchronous
    client carries a session that rejects concurrent queries on the same
    instance. The frame loop is serial per session, but a second task's frame
    can arrive on another coroutine — the lock keeps the client safe.
    """
    if _client is None:
        return False
    try:
        async with _lock_obj():
            await asyncio.to_thread(
                _client.insert,
                "task_messages",
                [row],
                column_names=COLUMN_NAMES,
            )
        return True
    except Exception:  # noqa: BLE001
        logger.debug("[nodeserver] task_messages insert failed; frame dropped from CH")
        return False


def build_row(
    *,
    row_id: str,
    task_id: str,
    logical_event_id: str,
    seq: int,
    item_type: str,
    item: dict,
    agent_id: str = "",
    subagent_id: str = "",
    event_kind: str = "",
    tool_name: str = "",
    phase: str = "",
    status: str = "",
    created_at: str,
) -> list:
    """Assemble one ``task_messages`` row in ``COLUMN_NAMES`` order.

    ``item_json`` carries the canonical envelope (the item plus the routing
    fields the read path needs), matching what ``task_event_log._envelope_json``
    persists today so the read-side merge can be the same field-level last-wins
    it already is.
    """
    envelope: dict[str, Any] = {
        "item": item,
        "agent_id": agent_id or "",
        "runtime_seq": int(seq or 0),
    }
    if logical_event_id:
        envelope["logical_event_id"] = logical_event_id
    if event_kind:
        envelope["event_kind"] = event_kind
    if tool_name:
        envelope["tool_name"] = tool_name
    if subagent_id:
        envelope["subagent_id"] = subagent_id
    if phase:
        envelope["phase"] = phase
    if status:
        envelope["status"] = status
    return [
        str(row_id),
        str(task_id),
        str(logical_event_id or ""),
        int(seq or 0),
        str(item_type or "")[:64],
        json.dumps(envelope, ensure_ascii=False, default=str),
        str(agent_id or ""),
        str(subagent_id or ""),
        str(event_kind or ""),
        str(tool_name or ""),
        str(phase or ""),
        str(status or ""),
        str(created_at),
        int(seq or 0),  # version = seq; a re-insert of the same seq keeps the newer write
    ]
