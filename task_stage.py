"""Persist session preparation stages so a failed task can name the step.

Session bring-up on the node walks four steps: prepare the working tree, clone
the repository, pre-flight the agent runtime, spawn it. Historically none of that
was observable: the whole sequence happened inside one ``CreateSession`` call
whose only outcome was a boolean ack plus, on failure, one error string. When a
task did not run, the answer to "which part broke?" was not recorded anywhere —
so diagnosing it meant reading node logs by hand, if they still existed.

The node now emits one ``NodeSessionStage`` frame as it enters each step, and
again with ``ok=false`` if that step fails. This module writes those frames to
the task row so the UI can show progress ("正在拉取代码") and, when something
breaks, point at the step instead of showing a bare exit code.

Two things are written, for two different questions:

* ``config_snapshot.runtime_stage`` — the *current* step (overwritten each time).
  Answers "where is my task right now / where did it stop?".
* ``mc_task_events`` — an append-only trail of every step. Answers "what was the
  sequence?" after the fact, which is what you want when a failure is
  intermittent.

Like :mod:`.task_finalize`, node_server owns only its ``mc_ac_*`` models, so the
task-domain rows are reached with raw SQL over the shared
``db.PostgresClient.pool``. Every failure is swallowed: stage reporting is
diagnostics and must never disturb the frame loop it rides on.
"""
from __future__ import annotations

import json
import uuid

from loguru import logger

# Proto enum name → the words a user sees. The enum is an implementation detail
# of the node protocol; the task page must not render SESSION_STAGE_GIT_CLONE at
# somebody. Unknown values degrade to the raw name rather than being dropped, so
# a stage added to the proto without updating this map is still visible.
_STAGE_LABELS = {
    "SESSION_STAGE_WORKSPACE_PREPARE": "准备工作目录",
    "SESSION_STAGE_GIT_CLONE": "拉取代码",
    "SESSION_STAGE_RESOURCE_SYNC": "同步 Skill 与插件",
    "SESSION_STAGE_RUNTIME_PREFLIGHT": "检查运行环境",
    "SESSION_STAGE_RUNTIME_START": "启动运行环境",
    "SESSION_STAGE_RUNNING": "运行中",
}


def stage_label(stage_name: str) -> str:
    """Human-readable label for a proto stage name."""
    return _STAGE_LABELS.get(stage_name, stage_name or "准备中")


def stage_key(stage_name: str) -> str:
    """Short, stable identifier stored in ``mc_tasks.runtime_stage``.

    The proto name (``SESSION_STAGE_GIT_CLONE``) is the wire encoding; the column
    holds the lowercase suffix (``git_clone``) so the DB value stays readable and
    is not tied to the enum's prefix if the proto is ever reorganized.
    """
    name = (stage_name or "").strip()
    if name.startswith("SESSION_STAGE_"):
        name = name[len("SESSION_STAGE_"):]
    return name.lower()[:32]


async def record_session_stage(
    session_id: str,
    *,
    stage_name: str,
    ok: bool,
    detail: str = "",
    error: str = "",
) -> None:
    """Write one preparation stage to the task bound to ``session_id``.

    Never raises. A stage frame is progress reporting: losing one must not
    disturb the upstream frame loop, and must not fail the session it describes.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        return
    try:
        from .shared_store import pool

        if pool() is None:
            return
        entry = {
            "stage": stage_name,
            "label": stage_label(stage_name),
            "ok": bool(ok),
            "detail": (detail or "")[:500],
            "error": (error or "")[:800],
        }
        async with pool().acquire() as conn:
            # Resolve the task whether or not the gateway has back-filled
            # node_session_id yet. Stages are emitted *during* node create —
            # before the dispatch ack returns — so at this instant the task row
            # still has node_session_id IS NULL. Without the ``OR id=$1`` arm,
            # every preparation stage would match nothing and be dropped, which
            # is exactly the "no progress, no failing step" gap this module
            # exists to close. session_id equals the task id (see
            # task_service._build_session), so id=$1 is a sound fallback.
            row = await conn.fetchrow(
                "UPDATE mc_tasks SET "
                "runtime_stage=$2, runtime_stage_detail=$3, runtime_stage_ok=$4, "
                # config_snapshot is a ``json`` column, not ``jsonb``. json has no
                # ``||`` operator, so merging must round-trip through jsonb —
                # without the casts every stage write failed with
                # "COALESCE could not convert type jsonb to json" and was
                # swallowed by this module's catch-all, which is exactly why no
                # stage ever reached the task page.
                "config_snapshot = ((COALESCE(config_snapshot::jsonb, '{}'::jsonb) || $5::jsonb))::json, "
                "updated_at=now() "
                "WHERE (node_session_id=$1 OR id::text=$1) AND deleted_at IS NULL "
                "RETURNING id",
                session_id,
                stage_key(stage_name),
                # On failure the reason is the useful text; on success it is the
                # note ("拉取代码（分支 main）"). One column either way, so the UI
                # has a single place to render.
                (error or detail or "")[:2000],
                bool(ok),
                json.dumps({"runtime_stage": entry}, ensure_ascii=False),
            )
            if row is None:
                return  # unknown handle (editor session, or task already deleted)
            task_id = row["id"]
            # Append-only trail. seq is allocated from the shared
            # mc_task_events_seq SEQUENCE so it is globally unique + monotonic
            # across the gateway and node_server (both write mc_task_events);
            # MAX(seq)+1 raced across connections, producing duplicate seqs
            # that broke the (seq, id) paging cursor.
            seq_val = await conn.fetchval(
                "SELECT nextval('mc_task_events_seq')"
            )
            await conn.execute(
                "INSERT INTO mc_task_events (id, task_id, seq, kind, event_type, payload, created_at) "
                "VALUES ($1, $2, $3, 'stage', $4, $5::jsonb, now())",
                uuid.uuid4(),
                task_id,
                int(seq_val),
                stage_name[:64],
                json.dumps(entry, ensure_ascii=False),
            )
    except Exception:  # noqa: BLE001
        logger.exception(
            "[nodeserver] record stage {} for session {} failed", stage_name, session_id
        )
