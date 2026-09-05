"""Session preparation stages are persisted so a failure can name its step.

``node_server.task_stage.record_session_stage`` writes each ``NodeSessionStage``
frame to the owning task: the current step onto ``config_snapshot.runtime_stage``
(for "where is it now / where did it stop") and an append-only row in
``mc_task_events`` (for "what was the sequence"). These run against a stubbed
asyncpg pool, so no live Postgres is needed.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from node_server.task_stage import record_session_stage, stage_label


class _FakeConn:
    """asyncpg-like connection recording every statement it is handed."""

    def __init__(self, task_row: dict | None, next_seq: int = 1):
        self._task_row = task_row
        self._next_seq = next_seq
        self.fetchrows: list[tuple[str, tuple[Any, ...]]] = []
        self.fetchvals: list[tuple[str, tuple[Any, ...]]] = []
        self.executes: list[tuple[str, tuple[Any, ...]]] = []

    async def fetchrow(self, query: str, *params: Any):
        self.fetchrows.append((query, params))
        return self._task_row

    async def fetchval(self, query: str, *params: Any):
        self.fetchvals.append((query, params))
        return self._next_seq

    async def execute(self, query: str, *params: Any):
        self.executes.append((query, params))
        return "INSERT 0 1"


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def acquire(self):
        conn = self._conn

        class _Ctx:
            async def __aenter__(self_inner):
                return conn

            async def __aexit__(self_inner, *exc):
                return False

        return _Ctx()


def _install(monkeypatch, task_row: dict | None, next_seq: int = 1) -> _FakeConn:
    conn = _FakeConn(task_row, next_seq)
    monkeypatch.setattr("node_server.shared_store._pool", _FakePool(conn))
    return conn


# The task row the handle lookup resolves to. The trail row's seq no longer comes
# from a per-task MAX(seq)+1 probe — it is allocated from the shared
# mc_task_events_seq SEQUENCE (fetchval), so it is stubbed separately.
def _task(task_id: str = "task-1") -> dict:
    return {"id": task_id}


@pytest.mark.asyncio
async def test_stage_is_written_to_snapshot_and_event_trail(monkeypatch):
    conn = _install(monkeypatch, _task(), next_seq=7)
    await record_session_stage(
        "sess-1", stage_name="SESSION_STAGE_GIT_CLONE", ok=True, detail="拉取代码（分支 main）"
    )

    # 1. Current step onto the task, scoped to this session handle. The task is
    # matched by handle OR id: stages are emitted during node create, before the
    # gateway back-fills node_session_id, so the id arm is what keeps early
    # stages (workspace/clone) from being dropped.
    update_query, update_params = conn.fetchrows[0]
    assert "UPDATE mc_tasks" in update_query
    assert "node_session_id=$1" in update_query
    assert "id::text=$1" in update_query
    assert update_params[0] == "sess-1"
    # Dedicated columns: the short stage key, its text, and the ok flag. These
    # are what the DTO and any query read — not the JSON blob.
    assert update_params[1] == "git_clone"
    assert update_params[2] == "拉取代码（分支 main）"
    assert update_params[3] is True
    entry = json.loads(update_params[4])["runtime_stage"]
    assert entry["stage"] == "SESSION_STAGE_GIT_CLONE"
    # The UI must not render the proto enum at a user.
    assert entry["label"] == "拉取代码"
    assert entry["ok"] is True
    assert entry["detail"] == "拉取代码（分支 main）"

    # 2. Append-only trail row, at the next per-task sequence.
    insert_query, insert_params = conn.executes[0]
    assert "INSERT INTO mc_task_events" in insert_query
    assert insert_params[1] == "task-1"
    assert insert_params[2] == 7
    assert insert_params[3] == "SESSION_STAGE_GIT_CLONE"
    assert json.loads(insert_params[4])["label"] == "拉取代码"


@pytest.mark.asyncio
async def test_failed_stage_carries_its_error(monkeypatch):
    """The whole point: a failed step records which step and why."""
    conn = _install(monkeypatch, _task())
    await record_session_stage(
        "sess-2",
        stage_name="SESSION_STAGE_RUNTIME_PREFLIGHT",
        ok=False,
        error="node agent runtime is not usable",
    )
    params = conn.fetchrows[0][1]
    # The failing step is recorded in the columns the UI reads: which step, that
    # it failed, and the reason (error wins over detail for the text column).
    assert params[1] == "runtime_preflight"
    assert "not usable" in params[2]
    assert params[3] is False
    entry = json.loads(params[4])["runtime_stage"]
    assert entry["ok"] is False
    assert entry["label"] == "检查运行环境"
    assert "not usable" in entry["error"]


@pytest.mark.asyncio
async def test_unknown_handle_writes_no_event(monkeypatch):
    """An editor session (or a deleted task) matches no task row: the snapshot
    update returns nothing, and no orphan event may be appended."""
    conn = _install(monkeypatch, None)
    await record_session_stage("sess-unknown", stage_name="SESSION_STAGE_RUNNING", ok=True)
    assert conn.executes == []
    # No task row means no seq may be consumed from the shared sequence either.
    assert conn.fetchvals == []


@pytest.mark.asyncio
async def test_blank_session_id_is_ignored(monkeypatch):
    conn = _install(monkeypatch, _task())
    await record_session_stage("   ", stage_name="SESSION_STAGE_RUNNING", ok=True)
    assert conn.fetchrows == []


@pytest.mark.asyncio
async def test_missing_pool_is_a_noop(monkeypatch):
    """node_server can receive frames before the shared pool is up."""
    import node_server.shared_store as shared_store

    monkeypatch.setattr(shared_store, "_pool", None)
    await record_session_stage("sess-3", stage_name="SESSION_STAGE_RUNNING", ok=True)


@pytest.mark.asyncio
async def test_db_failure_never_propagates(monkeypatch):
    """Stage reporting is diagnostics: it must not break the frame loop it rides."""

    class _Boom(_FakeConn):
        async def fetchrow(self, query: str, *params: Any):
            raise RuntimeError("connection reset")

    monkeypatch.setattr("node_server.shared_store._pool", _FakePool(_Boom(None)))
    await record_session_stage("sess-4", stage_name="SESSION_STAGE_GIT_CLONE", ok=False)


@pytest.mark.asyncio
async def test_long_text_is_bounded(monkeypatch):
    """A pathological error (a full stack trace) must not bloat the task row."""
    conn = _install(monkeypatch, _task())
    await record_session_stage(
        "sess-5",
        stage_name="SESSION_STAGE_RUNTIME_START",
        ok=False,
        detail="d" * 5000,
        error="e" * 5000,
    )
    params = conn.fetchrows[0][1]
    # The text column is bounded too — it is rendered verbatim on the task page.
    assert len(params[2]) <= 2000
    entry = json.loads(params[4])["runtime_stage"]
    assert len(entry["detail"]) <= 500
    assert len(entry["error"]) <= 800


def test_stage_label_falls_back_to_the_raw_name():
    """A stage added to the proto without updating the label map stays visible
    rather than silently rendering as an empty step."""
    assert stage_label("SESSION_STAGE_WORKSPACE_PREPARE") == "准备工作目录"
    assert stage_label("SESSION_STAGE_FUTURE_THING") == "SESSION_STAGE_FUTURE_THING"
    assert stage_label("") == "准备中"


@pytest.mark.asyncio
async def test_snapshot_merge_is_json_column_safe(monkeypatch):
    """Guard the column-type mismatch that silently killed stage recording.

    ``mc_tasks.config_snapshot`` is ``json``, not ``jsonb``. PostgreSQL defines
    ``||`` only for ``jsonb``, so the original
    ``COALESCE(config_snapshot, '{}'::jsonb) || $n::jsonb`` raised
    CannotCoerceError at execute time — and because this module swallows every
    exception (by design: diagnostics must not break the frame loop), the failure
    was invisible: every stage frame arrived, was written, and vanished.

    A stubbed connection cannot reproduce a server-side type error, so assert on
    the statement's shape instead: the column must be cast to jsonb for the merge
    and cast back to json for the assignment.
    """
    conn = _install(monkeypatch, _task())
    await record_session_stage("sess-9", stage_name="SESSION_STAGE_GIT_CLONE", ok=True)
    sql = conn.fetchrows[0][0]
    assert "config_snapshot::jsonb" in sql, sql
    # The merged value must be cast back to json for assignment to a json column.
    # Match the cast itself, not the character after it: the assignment is
    # followed by a comma (more SET clauses), not whitespace.
    assert "))::json" in sql, sql
    # The exact broken form must never come back.
    assert "COALESCE(config_snapshot, '{}'::jsonb)" not in sql, sql
