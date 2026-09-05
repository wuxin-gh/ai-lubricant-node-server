"""Server-side terminal-state finalizer for node session results.

``node_server.task_finalize.finalize_task_for_session`` must persist a task's
terminal status the moment the node's ``NodeSessionResult`` frame arrives, with
no SSE subscriber involved. These exercise it against a stubbed asyncpg pool, so
no live Postgres is needed.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from node_server.task_finalize import finalize_task_for_session


class _FakeConn:
    """asyncpg-like connection recording every statement it is handed.

    ``fetchrow`` returns queued rows in call order (None once drained), which is
    how the conditional UPDATE ... RETURNING reports win/no-op.
    """

    def __init__(self, rows: list[dict | None]):
        self._rows = list(rows)
        self.fetchrows: list[tuple[str, tuple[Any, ...]]] = []
        self.executes: list[tuple[str, tuple[Any, ...]]] = []

    async def fetchrow(self, query: str, *params: Any):
        self.fetchrows.append((query, params))
        if not self._rows:
            return None
        row = self._rows.pop(0)
        # The UPDATE ... RETURNING now also yields ``prev_status`` (the CTE
        # pre-image) for the history trail. Tests that don't care about history
        # leave it out of their row dict; default it so the finalizer's
        # ``row["prev_status"]`` access does not KeyError. Real Postgres returns
        # the column because it is in the RETURNING list.
        if isinstance(row, dict) and "prev_status" not in row:
            row["prev_status"] = "pending"
        if isinstance(row, dict) and "api_key_id" not in row:
            # The conditional UPDATE also yields ``api_key_id``; tests asserting
            # on the principal disable don't care, but a later ``key_id`` access
            # must not KeyError. Default to None (no key to park).
            row["api_key_id"] = None
        if isinstance(row, dict) and "user_id" not in row:
            # The notify path reads ``user_id``; tests that don't exercise the
            # notify still reach that branch after a won transition.
            row["user_id"] = None
            row["title"] = None
        return row

    async def execute(self, query: str, *params: Any):
        self.executes.append((query, params))
        return "UPDATE 1"


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


def _install(monkeypatch, rows: list[dict | None]) -> _FakeConn:
    conn = _FakeConn(rows)
    monkeypatch.setattr("node_server.shared_store._pool", _FakePool(conn))
    return conn


@pytest.mark.asyncio
async def test_success_marks_finished_and_disables_principal(monkeypatch):
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": 42}])
    await finalize_task_for_session("sess-1", success=True, exit_code=0, error="")

    query, params = conn.fetchrows[0]
    assert "UPDATE mc_tasks" in query
    assert params == ("sess-1", "finished")
    # The principal must be disabled in the same transition so its MCP grants
    # cannot be reused after the task ends. The history INSERT fires first.
    principal_updates = [e for e in conn.executes if "mcp_users" in e[0]]
    assert principal_updates and principal_updates[0][1] == (42,)


@pytest.mark.asyncio
async def test_nonzero_exit_marks_error(monkeypatch):
    """An instant exit-1 (e.g. the node's agent runtime is missing) must land as
    ``error``, not be silently dropped for lack of a stream subscriber."""
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": None}])
    await finalize_task_for_session(
        "sess-2", success=False, exit_code=1, error="runtime not installed"
    )
    query, params = conn.fetchrows[0]
    assert params[:2] == ("sess-2", "error")
    # A failure also records *why*, folded into the snapshot slot the task page
    # renders, so the UI can state a cause instead of a bare "error".
    assert "config_snapshot" in query
    assert "dispatch_error" in json.loads(params[2])


@pytest.mark.asyncio
async def test_success_flag_false_with_zero_exit_is_error(monkeypatch):
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": None}])
    await finalize_task_for_session("sess-3", success=False, exit_code=0, error="boom")
    params = conn.fetchrows[0][1]
    assert params[:2] == ("sess-3", "error")
    assert json.loads(params[2])["dispatch_error"] == "boom"


@pytest.mark.asyncio
async def test_success_writes_no_failure_reason(monkeypatch):
    """A clean finish must not leave a stale ``dispatch_error`` behind: the
    two-arg statement (no snapshot merge) is the one that runs."""
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": None}])
    await finalize_task_for_session("sess-ok", success=True, exit_code=0, error="")
    query, params = conn.fetchrows[0]
    assert params == ("sess-ok", "finished")
    assert "config_snapshot" not in query


@pytest.mark.asyncio
async def test_stderr_tail_becomes_the_reason_when_error_is_uninformative(monkeypatch):
    """``error`` is often just "exit status 1"; the provider's own stderr is what
    explains the failure, so it must reach the persisted reason."""
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": None}])
    await finalize_task_for_session(
        "sess-4",
        success=False,
        exit_code=1,
        error="exit status 1",
        stderr_tail="Traceback: something specific blew up at line 42",
    )
    reason = json.loads(conn.fetchrows[0][1][2])["dispatch_error"]
    assert "something specific blew up" in reason


@pytest.mark.asyncio
async def test_missing_runtime_is_translated_to_an_actionable_reason(monkeypatch):
    """The known "runtime not usable" shapes must map to a plain-language cause
    plus the fix, not surface a Node.js stack to the end user."""
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": None}])
    await finalize_task_for_session(
        "sess-5",
        success=False,
        exit_code=1,
        error="exit status 1",
        stderr_tail="Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'commander'",
    )
    reason = json.loads(conn.fetchrows[0][1][2])["dispatch_error"]
    assert "运行环境" in reason
    assert "ERR_MODULE_NOT_FOUND" not in reason


@pytest.mark.asyncio
async def test_no_principal_skips_principal_update(monkeypatch):
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": None}])
    await finalize_task_for_session("sess-4", success=True, exit_code=0, error="")
    # No principal disable when there is no principal to park; but the history
    # trail INSERT is still emitted (source='node', both fields moved).
    assert not any("mcp_users" in sql for sql, _ in conn.executes)


@pytest.mark.asyncio
async def test_already_terminal_or_unknown_handle_is_noop(monkeypatch):
    """The conditional UPDATE matches nothing (task already finished/error,
    deleted, or the handle is unknown) — no principal write follows."""
    conn = _install(monkeypatch, [None])
    await finalize_task_for_session("sess-5", success=True, exit_code=0, error="")
    assert conn.executes == []


@pytest.mark.asyncio
async def test_update_is_conditional_on_live_nonterminal_task(monkeypatch):
    """Guard the SQL predicate itself: a replayed frame must not resurrect a
    deleted task nor overwrite an existing terminal status."""
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": None}])
    await finalize_task_for_session("sess-6", success=True, exit_code=0, error="")
    query = conn.fetchrows[0][0]
    assert "node_session_id=$1" in query
    assert "deleted_at IS NULL" in query
    assert "status NOT IN ('finished','error')" in query
    assert "completed_at=now()" in query


@pytest.mark.asyncio
async def test_blank_session_id_is_ignored(monkeypatch):
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": 1}])
    await finalize_task_for_session("   ", success=True, exit_code=0, error="")
    assert conn.fetchrows == []


@pytest.mark.asyncio
async def test_missing_pool_is_ignored(monkeypatch):
    monkeypatch.setattr("node_server.shared_store._pool", None)
    # Must not raise: the frame loop cannot be disturbed by a cold pool.
    await finalize_task_for_session("sess-7", success=True, exit_code=0, error="")


@pytest.mark.asyncio
async def test_db_failure_is_swallowed(monkeypatch):
    """A DB error must never propagate into the upstream frame loop — the
    gateway's SSE finalize remains a second chance."""

    class _BoomConn(_FakeConn):
        async def fetchrow(self, query: str, *params: Any):
            raise RuntimeError("connection reset")

    monkeypatch.setattr("node_server.shared_store._pool", _FakePool(_BoomConn([])))
    await finalize_task_for_session("sess-8", success=True, exit_code=0, error="")


@pytest.mark.asyncio
async def test_reason_merge_is_json_column_safe(monkeypatch):
    """Same column-type guard as the stage writer, for the failure-reason merge.

    ``config_snapshot`` is a ``json`` column; ``||`` is a jsonb-only operator, so
    merging without casting raised CannotCoerceError and — since this finalizer
    swallows exceptions to protect the frame loop — silently dropped the reason
    the task page was supposed to show.
    """
    conn = _install(monkeypatch, [{"id": "t1", "mcp_user_id": None}])
    await finalize_task_for_session("sess-9", success=False, exit_code=1, error="boom")
    sql = conn.fetchrows[0][0]
    assert "config_snapshot::jsonb" in sql, sql
    assert "COALESCE(config_snapshot, '{}'::jsonb)" not in sql, sql
