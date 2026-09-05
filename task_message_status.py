"""Advance user-message delivery state from runtime/node status events.

The node control process sees every session frame even when no browser SSE
follower is attached — the same argument that gave us ``task_finalize`` and
``task_event_log``. The runtime and the execution node report a user message's
lifecycle as schema-light structured events:

* ``input_status``    — node ACK (received) / runtime result (failed, cancelled)
* ``agent_turn_started``  — the turn began executing (running)
* ``agent_turn_completed`` — the turn ended (completed / cancelled / failed)

This module maps those onto ``mc_task_events.delivery_status`` with the same
conditional (state-machine) UPDATE semantics as the gateway's
``TaskService._transition_message_status`` — keep the two transition tables in
sync. It runs in the node-server process, so it writes via raw SQL over the
shared pool (scope-limited, consistent with task_finalize.py) rather than the
gateway's Tortoise models.
"""
from __future__ import annotations

import json

from loguru import logger

from .task_status_history import record_status_transition

# from-state → allowed to-states. MUST mirror the gateway's authoritative
# ``monkeycode_compat/message_status_machine.py::MESSAGE_STATUS_TRANSITIONS``
# exactly. node_server does not import gateway code (self-contained package,
# see shared_store.py), so the two are separate physical copies kept in sync
# by ``tests/test_message_status_machine_parity.py`` — a CI failure there means
# someone edited one side without the other. Do not edit this in isolation.
_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"dispatching", "failed", "cancelled"}),
    "dispatching": frozenset({"received", "failed"}),
    "received": frozenset({"running", "completed", "failed", "cancelled"}),
    "running": frozenset({"completed", "failed", "cancelled"}),
    # failed → pending: same-id explicit retry, re-enters the queue.
    # failed → completed: a turn that errored then finished normally;
    #   the authoritative turn-end frame wins.
    "failed": frozenset({"pending", "completed"}),
    "cancelled": frozenset({"pending"}),  # same-id explicit retry, re-enters
}


def _resolve_target(event_type: str, payload: dict) -> str | None:
    """Map one structured event onto a delivery status or None."""
    if event_type == "input_status":
        status = str(payload.get("status") or "").strip()
        return status if status in ("received", "failed", "cancelled") else None
    if event_type == "agent_turn_started":
        return "running"
    if event_type == "agent_turn_completed":
        status = str(payload.get("status") or "").strip()
        if status == "cancelled":
            return "cancelled"
        if status == "failed":
            return "failed"
        return "completed"
    return None


def error_reason_from_payload(payload_json: str) -> str:
    """Best-effort short reason from a runtime error frame's payload.

    Error frames arrive as ``{"item": {"type": "error", "text": …}}`` (or bare
    ``message``/``error``/``detail``). Truncated — it lands in
    ``failure_reason`` which the UI renders inline.
    """
    try:
        payload = json.loads(payload_json) if payload_json else {}
    except Exception:  # noqa: BLE001 — reason extraction must never raise
        return ""
    if not isinstance(payload, dict):
        return ""
    item = payload.get("item")
    text = ""
    if isinstance(item, dict):
        text = str(item.get("text") or item.get("message") or "")
    if not text:
        text = str(payload.get("message") or payload.get("error") or payload.get("detail") or "")
    return text.strip()[:200]


def error_message_id_from_payload(payload_json: str) -> str:
    """Pull the failing message's id out of a runtime error frame's payload.

    Error frames (payload-embedded scheme) carry the failing user message's id
    as ``message_id`` / ``messageId`` when the runtime knew which turn failed.
    Empty when the runtime had no message context (parse failure, outer
    fallback) — caller falls back to session-wide failure marking.
    """
    try:
        payload = json.loads(payload_json) if payload_json else {}
    except Exception:  # noqa: BLE001
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("message_id") or payload.get("messageId") or "").strip()


async def fail_inflight_messages(
    session_id: str, reason: str, *, client_message_id: str | None = None
) -> None:
    """Mark still-in-flight user messages of this session as failed.

    Runtime error frames (provider 429, upstream 5xx, agent crash) are
    turn-level signals: the runtime process may stay up (so ``task_finalize``
    never fires and ``mc_tasks.status`` stays ``processing``), yet the turn
    is dead. ``delivery_status`` would otherwise stick at ``received``/``running``
    forever, and the UI keeps showing "Agent 正在处理" + a phantom cancel button.

    When the caller supplies ``client_message_id`` (parsed from the error
    frame's payload via :func:`error_message_id_from_payload`), we target that
    one message precisely, capturing the pre-image so the history trail's
    ``from_val`` is exact. When it is empty — the runtime had no message
    context — we fall back to closing out every in-flight message of the
    session. The conditional UPDATE (``delivery_status = ANY(in-flight
    states)``) makes both paths safe: already-completed/failed rows are
    untouched, and a same-id re-send later flips ``failed → pending`` as usual.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        return
    try:
        from .shared_store import pool

        if pool() is None:
            return
        in_flight = ["pending", "dispatching", "received", "running"]
        async with pool().acquire() as conn:
            if client_message_id:
                # Precise single-row path. ``prev`` captures the pre-image
                # ``delivery_status`` for the history trail, mirroring
                # ``record_message_status`` so ``from_val`` is exact rather
                # than empty. ``(task_id, client_message_id)`` is a partial
                # unique index, so at most one row matches.
                prev_cte = (
                    "WITH prev AS ("
                    "  SELECT id, delivery_status FROM mc_task_events"
                    "   WHERE task_id=(SELECT id FROM mc_tasks WHERE node_session_id=$1)"
                    "     AND client_message_id=$3"
                    ") "
                )
                row = await conn.fetchrow(
                    prev_cte
                    + "UPDATE mc_task_events SET delivery_status='failed', "
                    "failure_reason=COALESCE($2, failure_reason) "
                    "WHERE task_id=(SELECT id FROM mc_tasks WHERE node_session_id=$1) "
                    "AND client_message_id=$3 "
                    "AND delivery_status = ANY($4::text[]) "
                    "RETURNING id, task_id, client_message_id, delivery_attempt, "
                    "(SELECT p.delivery_status FROM prev p WHERE p.id = mc_task_events.id) AS prev_status",
                    session_id,
                    reason or None,
                    client_message_id,
                    in_flight,
                )
                if row:
                    await record_status_transition(
                        row["task_id"], "delivery_status", "failed",
                        frm=str(row["prev_status"] or ""),
                        reason=reason or "runtime error frame",
                        message_id=row["client_message_id"],
                        delivery_attempt=row["delivery_attempt"],
                        conn=conn,
                    )
                    logger.debug(
                        "[nodeserver] failed inflight message {} for session {} (reason: {})",
                        row["client_message_id"], session_id, reason or "<runtime error>",
                    )
            else:
                updated = await conn.fetch(
                    "UPDATE mc_task_events SET delivery_status='failed', "
                    "failure_reason=COALESCE($2, failure_reason) "
                    "WHERE task_id=(SELECT id FROM mc_tasks WHERE node_session_id=$1) "
                    "AND delivery_status = ANY($3::text[]) "
                    "RETURNING id, task_id, client_message_id, delivery_attempt",
                    session_id,
                    reason or None,
                    in_flight,
                )
                if updated:
                    # One history row per message actually closed out. The pre-image
                    # is not recoverable per row here (the statement matches four
                    # states at once), so ``from_val`` stays empty rather than
                    # guessing — an empty from is honest about what we saw.
                    for row in updated:
                        await record_status_transition(
                            row["task_id"], "delivery_status", "failed",
                            reason=reason or "runtime error frame (session-wide)",
                            message_id=row["client_message_id"],
                            delivery_attempt=row["delivery_attempt"],
                            conn=conn,
                        )
                    logger.debug(
                        "[nodeserver] failed inflight messages for session {} (reason: {})",
                        session_id, reason or "<runtime error>",
                    )
    except Exception:  # noqa: BLE001
        logger.exception(
            "[nodeserver] fail_inflight_messages failed for session {}", session_id or "<unknown>"
        )


async def record_message_status(session_id: str, event_type: str, payload_json: str) -> None:
    """Best-effort delivery-status advance for one message event. Never raises."""
    session_id = (session_id or "").strip()
    if not session_id:
        return
    try:
        payload = json.loads(payload_json) if payload_json else {}
        if not isinstance(payload, dict):
            return
        message_id = str(payload.get("message_id") or payload.get("messageId") or "").strip()
        if not message_id:
            return
        to_status = _resolve_target(event_type, payload)
        if to_status is None:
            return
        attempt = int(payload.get("delivery_attempt") or payload.get("deliveryAttempt") or 1) or 1

        from .shared_store import pool

        if pool() is None:
            return
        from_states = sorted(
            state for state, targets in _TRANSITIONS.items() if to_status in targets
        )
        if not from_states:
            return
        async with pool().acquire() as conn:
            # The ``prev`` CTE captures the pre-image delivery_status for the
            # history trail. A separate SELECT would race the gateway's own
            # transition of the same row; every part of one statement reads the
            # same snapshot, so ``prev_status`` is exactly what this move
            # overwrote. ``from_states`` still gates the move — the CTE only
            # observes.
            prev_cte = (
                "WITH prev AS ("
                "  SELECT id, delivery_status FROM mc_task_events"
                "   WHERE task_id=(SELECT id FROM mc_tasks WHERE node_session_id=$1)"
                "     AND client_message_id=$2"
                ") "
            )
            returning = (
                " RETURNING id, task_id, "
                "(SELECT p.delivery_status FROM prev p WHERE p.id = mc_task_events.id) AS prev_status"
            )
            if to_status == "failed":
                reason = str(payload.get("error") or "") or None
                updated = await conn.fetchrow(
                    prev_cte
                    + "UPDATE mc_task_events SET delivery_status=$3, failure_reason=COALESCE($4, failure_reason) "
                    "WHERE task_id=(SELECT id FROM mc_tasks WHERE node_session_id=$1) "
                    "AND client_message_id=$2 AND delivery_attempt=$5 "
                    "AND delivery_status = ANY($6::text[])" + returning,
                    session_id, message_id, to_status, reason, attempt, from_states,
                )
            else:
                reason = None
                status_column = {
                    "received": "received_at",
                    "running": "started_at",
                    "completed": "completed_at",
                    "cancelled": "completed_at",
                }.get(to_status)
                sets = "delivery_status=$3" + (
                    f", {status_column}=now()" if status_column else ""
                )
                updated = await conn.fetchrow(
                    prev_cte
                    + f"UPDATE mc_task_events SET {sets} "
                    "WHERE task_id=(SELECT id FROM mc_tasks WHERE node_session_id=$1) "
                    "AND client_message_id=$2 AND delivery_attempt=$4 "
                    "AND delivery_status = ANY($5::text[])" + returning,
                    session_id, message_id, to_status, attempt, from_states,
                )
            if updated:
                await record_status_transition(
                    updated["task_id"], "delivery_status", to_status,
                    frm=str(updated["prev_status"] or ""),
                    reason=reason or f"runtime event {event_type}",
                    message_id=message_id,
                    delivery_attempt=attempt,
                    conn=conn,
                )
                logger.debug(
                    "[nodeserver] message {} attempt {} -> {} (event {})",
                    message_id, attempt, to_status, event_type,
                )
    except Exception:  # noqa: BLE001
        logger.exception(
            "[nodeserver] message status update failed for session {}", session_id
        )
