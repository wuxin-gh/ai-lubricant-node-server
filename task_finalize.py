"""Server-side terminal-state finalizer for node session results.

When an execution node's session ends it emits a ``NodeSessionResult`` frame
upstream. Historically that frame was only fanned out to any live
``FollowNodeSession`` subscriber's in-memory queue (``registry.deliver_result``)
— so if no frontend SSE client happened to be attached at that instant, the
terminal outcome was **dropped**: ``mc_tasks.status`` stayed ``processing``
forever and the task's MCP principal was never disabled. A session that dies
immediately (e.g. the node's agent runtime is not installed, exit code 1) is
exactly the case with no subscriber, so its status never advanced.

This module closes that gap from the node-control side, independent of any
subscriber. It mirrors the gateway's ``TaskService.task_events`` finalize
(status=finished/error + completed_at + disable principal) but is driven by the
frame arriving, not by a client consuming a stream. Both paths are idempotent —
whichever runs first wins; a later replay is a no-op.

node_server owns only its ``mc_ac_*`` Tortoise models, so — like
``git_proxy`` — the task-domain rows (``mc_tasks``, ``mcp_users``) are reached
via raw SQL over the shared ``db.PostgresClient.pool``. This is a scope-limited
write dependency, consistent with the existing read dependency in git_proxy.
"""
from __future__ import annotations

import json

from loguru import logger

from .task_status_history import record_status_transition

# Task states that are already terminal; a result frame for one of these needs
# no write (idempotent replay / gateway already finalized).
_TERMINAL_STATUSES = frozenset({"finished", "error"})


def _failure_reason(error: str, exit_code: int, stderr_tail: str = "") -> str:
    """Translate a node's raw runtime failure into a cause + a next action.

    Two inputs, in order of usefulness. ``stderr_tail`` is what the provider
    actually printed before dying (a Node.js ``ERR_MODULE_NOT_FOUND`` stack
    naming the missing package, a permission error, …); ``error`` is the node's
    own wrapper, frequently just "exit status 1". So both are matched, and the
    tail wins as the fallback text when nothing is recognized — "exit status 1"
    tells the reader nothing, the stack tells them everything.

    Keep this mapping in sync with the gateway's
    ``task_service._runtime_failure_reason`` — the two run in different packages
    and whichever fires first writes the reason the task page shows.
    """
    text = (error or "").strip()
    tail = (stderr_tail or "").strip()
    lowered = f"{text}\n{tail}".lower()
    runtime_markers = (
        "agent-compose-runtime not found",
        "agent runtime is not usable",
        "node agent runtime",
        "err_module_not_found",
        "cannot find package",
        "cannot find module",
        "node.js is missing",
    )
    if any(marker in lowered for marker in runtime_markers):
        return "节点上的 Agent 运行环境不可用（未安装或依赖缺失），需要管理员在节点管理页升级该节点的运行环境后重新运行任务。"
    # Unrecognized failure: show the real output rather than a generic line. The
    # tail's *end* is kept — a stack trace's root cause is at the bottom.
    if tail:
        detail = tail[-800:]
        return f"运行环境异常退出（退出码 {exit_code}）。节点输出：\n{detail}"
    if text:
        return text[:800]
    return f"运行环境启动后立即退出（退出码 {exit_code}），未返回错误信息。请联系管理员检查该节点的运行环境。"


async def _notify_task_ended(
    *,
    user_id: object,
    task_id: object,
    title: object,
    status: str,
    reason: str,
) -> None:
    """Append a ``task.ended`` row to the shared ``mc_notify_outbox`` table.

    The row carries everything the data service's notify worker needs (the
    bell-facing fields are stashed in ``envelope``); that worker — running in
    the data-service process, which owns the consume loop — drains the table
    and performs channel delivery, so a restart never loses the notification.

    Swallows everything — a task's terminal state must never depend on whether a
    chat webhook answered.
    """
    if not user_id:
        return
    try:
        from .shared_store import enqueue_notification

        label = str(title or "").strip() or str(task_id)
        outcome = "成功" if status == "finished" else "失败"
        severity = "info" if status == "finished" else "warn"
        await enqueue_notification(
            event_type="task.ended",
            params={
                "task_id": str(task_id),
                "task": label,
                "status": status,
                "result": outcome,
                "reason": reason or "",
                "severity": severity,
            },
            envelope={
                "severity": severity,
                "kind": "task",
                "source": "task_finalize",
                "title": None,
                "message": f"任务「{label}」已结束：{outcome}",
                "detail": reason or "",
                "dedupe_key": None,
                "dedupe_window_seconds": 300,
                "request_log_id": None,
            },
            owner_type="user",
            owner_id=user_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception("[nodeserver] task.ended notify for {} failed", task_id)


async def finalize_task_for_session(
    session_id: str,
    *,
    success: bool,
    exit_code: int,
    error: str,
    stderr_tail: str = "",
) -> None:
    """Best-effort: persist a task's terminal status from its session result.

    Resolves the owning task via ``mc_tasks.node_session_id`` (the canonical
    task→runtime handle), advances ``status`` to ``finished``/``error`` with
    ``completed_at``, records *why* it failed, and disables the task's MCP
    principal + parks its task child API key so neither grant can be reused
    after the task ends. Never raises: a failure here must not disturb the
    upstream frame loop — the gateway's SSE path remains a second chance.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        return
    try:
        from .shared_store import pool

        if pool() is None:
            return
        new_status = "finished" if success and exit_code == 0 else "error"
        reason = (
            ""
            if new_status == "finished"
            else _failure_reason(error, exit_code, stderr_tail)
        )
        async with pool().acquire() as conn:
            # Conditional single-statement transition: only a live, non-terminal,
            # non-deleted task bound to THIS handle flips. RETURNING tells us
            # whether we won (so the principal disable runs once) and yields the
            # principal id in the same round-trip. On failure the human-readable
            # reason is folded into the snapshot the task page already renders
            # (dispatch_error), so the UI can state the cause, not just the outcome.
            #
            # The ``prev`` CTE captures the pre-image status for the history trail:
            # the UPDATE itself cannot report what it overwrote, and a separate
            # SELECT would race the gateway's SSE finalizer. All parts of one
            # statement see the same snapshot, so ``prev_status`` is exactly the
            # value this transition moved away from.
            if reason:
                row = await conn.fetchrow(
                    "WITH prev AS ("
                    "  SELECT id, status FROM mc_tasks WHERE node_session_id=$1"
                    ") "
                    "UPDATE mc_tasks SET status=$2, completed_at=now(), updated_at=now(), "
                    # mc_tasks.config_snapshot is ``json``, not ``jsonb``, and
                    # ``json`` has no ``||`` operator — merging directly raised
                    # "could not convert type jsonb to json" and made every
                    # failure-reason write silently fail. Cast to jsonb to merge,
                    # then back to json to match the column type.
                    "config_snapshot = ((COALESCE(config_snapshot::jsonb, '{}'::jsonb) || $3::jsonb))::json "
                    "WHERE node_session_id=$1 AND deleted_at IS NULL "
                    "AND status NOT IN ('finished','error') "
                    "RETURNING id, mcp_user_id, api_key_id, user_id, title, "
                    "(SELECT p.status FROM prev p WHERE p.id = mc_tasks.id) AS prev_status",
                    session_id,
                    new_status,
                    json.dumps({"dispatch_error": reason}),
                )
            else:
                row = await conn.fetchrow(
                    "WITH prev AS ("
                    "  SELECT id, status FROM mc_tasks WHERE node_session_id=$1"
                    ") "
                    "UPDATE mc_tasks SET status=$2, completed_at=now(), updated_at=now() "
                    "WHERE node_session_id=$1 AND deleted_at IS NULL "
                    "AND status NOT IN ('finished','error') "
                    "RETURNING id, mcp_user_id, api_key_id, user_id, title, "
                    "(SELECT p.status FROM prev p WHERE p.id = mc_tasks.id) AS prev_status",
                    session_id,
                    new_status,
                )
            if row is None:
                return  # unknown handle, already terminal, or deleted — nothing to do
            # Won the transition: record it before the grant teardown, on the same
            # connection, so the trail exists even if a later step fails.
            await record_status_transition(
                row["id"], "status", new_status,
                frm=str(row["prev_status"] or ""),
                reason=reason or f"node result success (exit={exit_code})",
                conn=conn,
            )
            principal_id = row["mcp_user_id"]
            if principal_id:
                await conn.execute(
                    "UPDATE mcp_users SET enabled=false, updated_at=now() WHERE id=$1",
                    int(principal_id),
                )
            # Park the task child key as well (same terminal-state contract as the
            # gateway's task_events path). The row is kept bound so a later
            # resume flips it back. The gateway's in-memory key snapshot cannot
            # be refreshed from here — the conditional transition above makes
            # this the only writer, and the 60s snapshot reconcile picks the
            # flip up; when an SSE follower is attached the gateway path wins
            # instead and refreshes immediately.
            key_id = row["api_key_id"]
            if key_id:
                await conn.execute(
                    "UPDATE api_keys SET disabled=true WHERE id=$1 AND disabled=false",
                    int(key_id),
                )
        logger.info(
            "[nodeserver] finalized task for session {} -> {} (exit={}, success={})",
            session_id, new_status, exit_code, success,
        )
        # Only the winner of the conditional transition notifies, so a replayed
        # frame or the gateway's SSE path cannot double-send. Fired after the
        # connection is released and awaited here rather than backgrounded: this
        # coroutine is not on a request path, and awaiting keeps the send from
        # being cut short if the frame loop's task group unwinds.
        await _notify_task_ended(
            user_id=row["user_id"],
            task_id=row["id"],
            title=row["title"],
            status=new_status,
            reason=reason,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "[nodeserver] finalize task for session {} failed", session_id or "<unknown>"
        )
