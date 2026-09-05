"""Durably persist normalized conversation items received from execution nodes.

The node control process sees every session frame, unlike the gateway SSE
follower which only sees frames while a browser is connected. Recording the
item trail here is what makes a task's conversation replayable when the page is
opened after a turn has already run — or failed.

Storage is split by what the data *is*: conversation **content** goes to
ClickHouse ``task_messages`` (append-only, one row per frame — see
``task_message_store``), while PostgreSQL ``mc_task_events`` keeps only a thin
**index/state** row per frame (``kind='item_ref'`` + ``logical_event_id``) so
the gateway's delivery-status machine and the paging cursor have something to
join on. The old arrangement — full payload in PG, read-merge-update per frame
— made every frame a read plus a write on a growing jsonb blob, and lost the
frame trail: a merged row can no longer say what the runtime actually reported,
in what order. Appending keeps that history; the read side merges by
``logical_event_id`` instead (the same field-level last-wins the client already
does in ``mergeNormalizedItem``).

When ClickHouse is not configured or unreachable, the PG row falls back to
carrying the whole envelope in ``payload`` — a CH-less install still renders
history, just without the append-only trail.

Every runner normalizes its provider's output into the shared ``item`` shape
before it reaches this module, so no provider-specific decoding happens here.
"""
from __future__ import annotations

import json
import time
import uuid

from loguru import logger

# Items that belong in a task's conversation history. Lifecycle/telemetry frames
# (turn started/completed, usage, todo lists) drive live UI state but are not
# conversation content, so replaying them would add rows a reader cannot use.
_REPLAYABLE_ITEM_TYPES = frozenset({
    "user_input",
    "agent_message",
    "reasoning",
    "tool_call",
    "command_execution",
    "mcp_tool_call",
    "file_change",
    "web_search",
    "error",
})


def _item_of(payload: object) -> dict | None:
    """Extract the normalized item from a runtime frame payload."""
    if not isinstance(payload, dict):
        return None
    item = payload.get("item")
    if isinstance(item, dict):
        return item
    event = payload.get("event")
    if isinstance(event, dict):
        nested = event.get("item")
        if isinstance(nested, dict):
            return nested
    return None


def _envelope_json(
    item: dict,
    *,
    agent_id: str,
    runtime_seq: int,
    logical_event_id: str,
    event_kind: str,
    tool_name: str,
    subagent_id: str,
    phase: str,
    status: str,
) -> str:
    """Serialize the persisted payload envelope with the canonical fields.

    The canonical envelope (``logical_event_id``/``event_kind``/``tool_name``/
    ``subagent_id``/``phase``/``status``) is stored top-level next to the
    legacy ``agent_id`` alias so replay consumers route on protocol fields
    instead of re-deriving intent from a provider payload. Empty canonical
    fields are omitted — for most rows they coincide with what ``item``
    already carries (e.g. ``logical_event_id == item.id``), and omitting them
    keeps the blob small and the old row shape recognizable.
    """
    envelope: dict = {
        "item": item,
        "agent_id": agent_id or "",
        "runtime_seq": int(runtime_seq or 0),
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
    return json.dumps(envelope, ensure_ascii=False, default=str)


async def record_session_event(
    session_id: str,
    *,
    seq: int,
    event_type: str,
    item_type: str,
    agent_id: str,
    payload_json: str,
    logical_event_id: str = "",
    event_kind: str = "",
    tool_name: str = "",
    subagent_id: str = "",
    phase: str = "",
    status: str = "",
) -> None:
    """Best-effort append of one conversation frame to ClickHouse ``task_messages``.

    Every frame the node sees gets one CH row (append-only; ReplacingMergeTree
    collapses a re-insert of the same ``seq`` on retry). The node also writes a
    thin reference row in PostgreSQL ``mc_task_events`` (``kind='item_ref'``,
    ``logical_event_id``, ``message_ref``→CH id) so the gateway's delivery-status
    machine and the task-event list can be joined. When CH is unreachable the
    PG row carries the full payload as a fallback — the UI still renders history.

    Only items in ``_REPLAYABLE_ITEM_TYPES`` are stored. ``logical_event_id``
    is derived from the explicit parameter, ``item.logical_event_id``,
    or ``item.id`` (they coincide on tool calls). The canonical envelope fields
    arrive already normalised (runtime fills them, the stream parser recovers
    any a sparse frame dropped).
    """
    session_id = (session_id or "").strip()
    if not session_id:
        return
    try:
        from .shared_store import pool

        if pool() is None:
            return
        try:
            payload = json.loads(payload_json) if payload_json else None
        except (TypeError, ValueError):
            return
        item = _item_of(payload)
        if item is None:
            return
        resolved_type = str(item.get("type") or item_type or "").strip()
        if resolved_type not in _REPLAYABLE_ITEM_TYPES:
            return

        # Canonical merge id: prefer explicit, fall back to item's own id.
        logical_id = (
            logical_event_id
            or str(item.get("logical_event_id") or "").strip()
            or str(item.get("id") or "").strip()
        )
        if not logical_id:
            # No id means no stable key; we must still write every frame so the
            # seq cursor can walk them. Use a fresh uuid per frame — it is never
            # re-reported without its own stable id.
            logical_id = str(uuid.uuid4())

        # Recover canonical fields a sparse frame may have dropped.
        frame_root = payload if isinstance(payload, dict) else {}
        resolved_subagent = (
            subagent_id
            or str(item.get("subagent_id") or "").strip()
            or str(frame_root.get("subagent_id") or "").strip()
            or agent_id
        )
        resolved_tool = (
            tool_name
            or str(item.get("tool_name") or "").strip()
            or str(item.get("title") or "").strip()
        )
        resolved_phase = phase or str(item.get("phase") or "").strip()
        resolved_status = status or str(item.get("status") or "").strip()

        # Truncate large items to keep PG fallback rows bounded.
        persisted_item: dict = dict(item)
        blob = json.dumps(persisted_item, ensure_ascii=False, default=str)
        if len(blob) > 256 * 1024:
            persisted_item = {
                "id": item.get("id"),
                "type": resolved_type,
                "truncated": True,
                "size": len(blob),
            }

        ch_row_id = str(uuid.uuid4())
        created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + f".{int((time.time() % 1) * 1000):03d}"
        seq_int = int(seq or 0)

        from . import task_message_store

        async with pool().acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id FROM mc_tasks
                   WHERE deleted_at IS NULL
                     AND (node_session_id=$1 OR id::text=$1)
                   LIMIT 1""",
                session_id,
            )
            if row is None:
                return
            task_id = str(row["id"])

            # Content → ClickHouse first: it owns the id the PG row points at,
            # and a CH failure must be known before the PG row claims the
            # content lives there. ``insert_task_message`` never raises; it
            # returns False when CH is unconfigured or the write failed.
            ch_ok = await task_message_store.insert_task_message(
                task_message_store.build_row(
                    row_id=ch_row_id,
                    task_id=task_id,
                    logical_event_id=logical_id,
                    seq=seq_int,
                    item_type=resolved_type,
                    item=persisted_item,
                    agent_id=agent_id,
                    subagent_id=resolved_subagent,
                    event_kind=event_kind,
                    tool_name=resolved_tool,
                    phase=resolved_phase,
                    status=resolved_status,
                    created_at=created_at,
                )
            )

            # The replay cursor is allocated from the shared sequence either way,
            # so PG stays the ordered index over every frame regardless of where
            # the content ended up.
            pg_seq = await conn.fetchval("SELECT nextval('mc_task_events_seq')")

            if ch_ok:
                # Primary path: state/index only. A NULL payload is the signal to
                # the read path that content must be joined from ClickHouse.
                await conn.execute(
                    """INSERT INTO mc_task_events
                       (id, task_id, seq, kind, event_type, logical_event_id, created_at)
                       VALUES ($1, $2, $3, 'item_ref', $4, $5, now())""",
                    uuid.uuid4(),
                    task_id,
                    int(pg_seq or 1),
                    resolved_type[:64],
                    logical_id,
                )
            else:
                # Fallback: keep the whole envelope in PG. Non-NULL payload means
                # "content is here", which is also how pre-split rows read.
                await conn.execute(
                    """INSERT INTO mc_task_events
                       (id, task_id, seq, kind, event_type, logical_event_id, payload, created_at)
                       VALUES ($1, $2, $3, 'item', $4, $5, $6::jsonb, now())""",
                    uuid.uuid4(),
                    task_id,
                    int(pg_seq or 1),
                    resolved_type[:64],
                    logical_id,
                    _envelope_json(
                        persisted_item,
                        agent_id=agent_id,
                        runtime_seq=seq_int,
                        logical_event_id=logical_id,
                        event_kind=event_kind,
                        tool_name=resolved_tool,
                        subagent_id=resolved_subagent,
                        phase=resolved_phase,
                        status=resolved_status,
                    ),
                )
    except Exception:  # noqa: BLE001
        # Diagnostics must never interrupt frame delivery to a live follower.
        logger.exception("[nodeserver] persist session item {} failed", session_id)
