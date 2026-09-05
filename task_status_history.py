"""Append node-observed state transitions to ``mc_task_status_history``.

The task surface runs four state machines — ``mc_tasks.status``,
``mc_tasks.workspace_state``, ``mc_tasks.runtime_stage`` and
``mc_task_events.delivery_status`` — as mutable columns updated in place. That
made a task which ended somewhere unexpected unexplainable after the fact: the
column held the final value and nothing recorded the path or the cause.

Both processes write those columns by design, not by accident: node_server must
close out a session whose browser never subscribed (see ``task_finalize``), so
consolidating the writes into the gateway was never an option. What the trail
needs instead is attribution — hence ``source='node'`` here versus
``source='gateway'`` in ``TaskService._record_status_transition``. The table is
owned by the gateway (it registers the Tortoise model and creates the schema);
this module only INSERTs into it over the shared pool, the same scope-limited
write dependency ``task_finalize`` and ``task_stage`` already take.

Never raises: diagnostics must not break the frame loop they ride, and a
dropped row means "history lost it", not "the transition did not happen".
"""
from __future__ import annotations

import uuid

from loguru import logger


async def record_status_transition(
    task_id: object,
    field: str,
    to_val: str,
    *,
    frm: str = "",
    reason: str | None = None,
    message_id: str | None = None,
    delivery_attempt: int | None = None,
    conn: object | None = None,
) -> None:
    """Append one transition. Pass ``conn`` to reuse an open connection.

    ``conn`` matters where the caller already holds one inside an ``async with
    pool().acquire()`` block: acquiring a second connection from inside the first
    can deadlock a saturated pool, and the insert belongs to the same logical
    step as the UPDATE that preceded it.
    """
    try:
        from .shared_store import pool

        if conn is None and pool() is None:
            return
        sql = (
            "INSERT INTO mc_task_status_history "
            "(id, task_id, field, from_val, to_val, reason, source, "
            " message_id, delivery_attempt, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, 'node', $7, $8, now())"
        )
        params = (
            uuid.uuid4(),
            task_id,
            (field or "")[:32],
            (frm or "")[:64],
            (to_val or "")[:64],
            (reason or None),
            (message_id or None),
            delivery_attempt,
        )
        if conn is not None:
            await conn.execute(sql, *params)  # type: ignore[attr-defined]
            return
        async with pool().acquire() as own:
            await own.execute(sql, *params)
    except Exception:  # noqa: BLE001
        # debug, not exception: on an installation that predates the table this
        # would otherwise log a stack trace for every single frame.
        logger.debug(
            "[nodeserver] status history {} {}→{} for task {} not recorded",
            field, frm or "?", to_val, task_id,
        )
