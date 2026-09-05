"""The append-only status trail written from the node-control side.

``mc_task_status_history`` exists because all four task state machines
(``status``, ``workspace_state``, ``runtime_stage``, ``delivery_status``) are
mutable columns: once a task ended somewhere unexpected, nothing recorded how it
got there. These tests pin the two properties that make the trail trustworthy:

* a row is appended **only** when the conditional UPDATE actually moved the row
  (never a claimed move the state machine rejected), and it carries the
  pre-image so the path can be replayed;
* recording is strictly best-effort — a failing INSERT must not break the
  transition it describes, nor the upstream frame loop.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from node_server import shared_store
from node_server.task_status_history import record_status_transition


class _Conn:
    """asyncpg-like connection recording executes; fetch/fetchrow are canned."""

    def __init__(self, row: dict | None = None, rows: list[dict] | None = None):
        self.executes: list[tuple[str, tuple[Any, ...]]] = []
        self._row = row
        self._rows = rows or []

    async def execute(self, sql: str, *args: Any):
        self.executes.append((sql, args))
        return "INSERT 0 1"

    async def fetchrow(self, sql: str, *args: Any):
        self.executes.append((sql, args))
        return self._row

    async def fetch(self, sql: str, *args: Any):
        self.executes.append((sql, args))
        return self._rows

    def history_rows(self) -> list[tuple[str, tuple[Any, ...]]]:
        return [e for e in self.executes if "mc_task_status_history" in e[0]]


class _Pool:
    def __init__(self, conn: _Conn):
        self.conn = conn
        self.acquired = 0

    def acquire(self):
        pool = self

        class _Ctx:
            async def __aenter__(self_inner):
                pool.acquired += 1
                return pool.conn

            async def __aexit__(self_inner, *exc):
                return False

        return _Ctx()


def _fields(sql: str, params: tuple) -> dict:
    """Name the positional params of the history INSERT for readable asserts."""
    assert "INSERT INTO mc_task_status_history" in sql
    _id, task_id, field, from_val, to_val, reason, message_id, attempt = params
    return {
        "task_id": task_id,
        "field": field,
        "from_val": from_val,
        "to_val": to_val,
        "reason": reason,
        "message_id": message_id,
        "delivery_attempt": attempt,
    }


@pytest.mark.asyncio
async def test_transition_is_recorded_with_node_as_source(monkeypatch):
    """``source`` is hard-coded in the SQL: a row's writer must be attributable.

    Both processes legitimately write these columns (node_server has to close out
    a session nobody subscribed to), so "who moved it" is the whole point of the
    trail.
    """
    conn = _Conn()
    await record_status_transition(
        "task-1", "status", "error", frm="processing", reason="boom", conn=conn,
    )
    sql, params = conn.history_rows()[0]
    assert "'node'" in sql
    assert _fields(sql, params) == {
        "task_id": "task-1",
        "field": "status",
        "from_val": "processing",
        "to_val": "error",
        "reason": "boom",
        "message_id": None,
        "delivery_attempt": None,
    }


@pytest.mark.asyncio
async def test_delivery_rows_carry_message_identity(monkeypatch):
    """A task has many user messages, so a ``delivery_status`` row is meaningless
    without which message and which attempt moved."""
    conn = _Conn()
    await record_status_transition(
        "task-1", "delivery_status", "completed",
        frm="running", message_id="msg-9", delivery_attempt=3, conn=conn,
    )
    fields = _fields(*conn.history_rows()[0])
    assert fields["message_id"] == "msg-9"
    assert fields["delivery_attempt"] == 3


@pytest.mark.asyncio
async def test_passed_connection_is_reused_not_reacquired(monkeypatch):
    """Callers insert from inside their own ``pool().acquire()`` block; taking a
    second connection there can deadlock a saturated pool."""
    conn = _Conn()
    pool = _Pool(_Conn())
    monkeypatch.setattr(shared_store, "_pool", pool)
    await record_status_transition("task-1", "status", "finished", conn=conn)
    assert pool.acquired == 0
    assert conn.history_rows()


@pytest.mark.asyncio
async def test_without_connection_it_acquires_one(monkeypatch):
    pool = _Pool(_Conn())
    monkeypatch.setattr(shared_store, "_pool", pool)
    await record_status_transition("task-1", "status", "finished")
    assert pool.acquired == 1
    assert pool.conn.history_rows()


@pytest.mark.asyncio
async def test_missing_pool_is_ignored(monkeypatch):
    monkeypatch.setattr(shared_store, "_pool", None)
    await record_status_transition("task-1", "status", "finished")


@pytest.mark.asyncio
async def test_insert_failure_never_propagates(monkeypatch):
    """An installation predating the table (or any DB hiccup) must not turn a
    successful transition into an exception on the frame loop."""

    class _Boom(_Conn):
        async def execute(self, sql: str, *args: Any):
            raise RuntimeError("relation \"mc_task_status_history\" does not exist")

    await record_status_transition("task-1", "status", "finished", conn=_Boom())


@pytest.mark.asyncio
async def test_over_long_values_are_truncated_to_column_width(monkeypatch):
    conn = _Conn()
    await record_status_transition(
        "task-1", "x" * 80, "y" * 80, frm="z" * 80, conn=conn,
    )
    fields = _fields(*conn.history_rows()[0])
    assert len(fields["field"]) == 32
    assert len(fields["to_val"]) == 64
    assert len(fields["from_val"]) == 64


# ---------------------------------------------------------------------------
# The two node writers, end to end: history must follow the real transition.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalizer_records_the_status_move_it_won(monkeypatch):
    from node_server.task_finalize import finalize_task_for_session

    conn = _Conn(row={
        "id": "t1", "mcp_user_id": None, "api_key_id": None,
        "user_id": None, "title": None, "prev_status": "processing",
    })
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await finalize_task_for_session("sess-1", success=True, exit_code=0, error="")

    fields = _fields(*conn.history_rows()[0])
    assert fields["task_id"] == "t1"
    assert fields["field"] == "status"
    # The pre-image comes from the UPDATE's own ``prev`` CTE, not a second
    # SELECT — that read would race the gateway's SSE finalizer.
    assert (fields["from_val"], fields["to_val"]) == ("processing", "finished")


@pytest.mark.asyncio
async def test_finalizer_records_nothing_when_the_update_matched_no_row(monkeypatch):
    """Already terminal / deleted / unknown handle: claiming a move in history
    that the machine rejected is worse than no row at all."""
    from node_server.task_finalize import finalize_task_for_session

    conn = _Conn(row=None)
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await finalize_task_for_session("sess-1", success=True, exit_code=0, error="")
    assert conn.history_rows() == []


@pytest.mark.asyncio
async def test_message_status_records_delivery_move_with_pre_image(monkeypatch):
    from node_server.task_message_status import record_message_status

    conn = _Conn(row={"id": "e1", "task_id": "t1", "prev_status": "dispatching"})
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await record_message_status(
        "sess-1", "input_status",
        json.dumps({"message_id": "msg-1", "delivery_attempt": 2, "status": "received"}),
    )
    fields = _fields(*conn.history_rows()[0])
    assert fields["task_id"] == "t1"
    assert fields["field"] == "delivery_status"
    assert (fields["from_val"], fields["to_val"]) == ("dispatching", "received")
    assert (fields["message_id"], fields["delivery_attempt"]) == ("msg-1", 2)


@pytest.mark.asyncio
async def test_message_status_records_nothing_when_transition_is_rejected(monkeypatch):
    from node_server.task_message_status import record_message_status

    conn = _Conn(row=None)  # conditional UPDATE matched nothing
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await record_message_status(
        "sess-1", "input_status",
        json.dumps({"message_id": "msg-1", "status": "received"}),
    )
    assert conn.history_rows() == []


@pytest.mark.asyncio
async def test_inflight_failure_records_one_row_per_closed_message(monkeypatch):
    """A runtime error frame carries no message id, so the session-wide statement
    closes every in-flight message — each one is its own history row."""
    from node_server.task_message_status import fail_inflight_messages

    conn = _Conn(rows=[
        {"id": "e1", "task_id": "t1", "client_message_id": "msg-1", "delivery_attempt": 1},
        {"id": "e2", "task_id": "t1", "client_message_id": "msg-2", "delivery_attempt": 4},
    ])
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await fail_inflight_messages("sess-1", "provider 429")

    rows = [_fields(*e) for e in conn.history_rows()]
    assert len(rows) == 2
    assert [(r["message_id"], r["delivery_attempt"]) for r in rows] == [
        ("msg-1", 1), ("msg-2", 4),
    ]
    assert all(r["to_val"] == "failed" for r in rows)
    # The statement matches four from-states at once, so no per-row pre-image is
    # recoverable. An empty ``from`` is honest; a guessed one would not be.
    assert all(r["from_val"] == "" for r in rows)
    assert all(r["reason"] == "provider 429" for r in rows)


@pytest.mark.asyncio
async def test_inflight_failure_records_nothing_when_no_message_was_inflight(monkeypatch):
    from node_server.task_message_status import fail_inflight_messages

    conn = _Conn(rows=[])
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await fail_inflight_messages("sess-1", "provider 429")
    assert conn.history_rows() == []


@pytest.mark.asyncio
async def test_inflight_failure_targets_one_message_when_id_is_known(monkeypatch):
    """When the error frame carries the failing message's id, the precise UPDATE
    closes just that one row and recovers its pre-image from the ``prev`` CTE —
    so ``from_val`` is no longer the honest-but-empty session-wide guess."""
    from node_server.task_message_status import fail_inflight_messages

    conn = _Conn(row={
        "id": "e1", "task_id": "t1",
        "client_message_id": "msg-1", "delivery_attempt": 1,
        "prev_status": "running",
    })
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await fail_inflight_messages("sess-1", "provider 429", client_message_id="msg-1")

    rows = [_fields(*e) for e in conn.history_rows()]
    assert len(rows) == 1
    assert rows[0]["task_id"] == "t1"
    assert rows[0]["field"] == "delivery_status"
    assert (rows[0]["from_val"], rows[0]["to_val"]) == ("running", "failed")
    assert (rows[0]["message_id"], rows[0]["delivery_attempt"]) == ("msg-1", 1)
    assert rows[0]["reason"] == "provider 429"


@pytest.mark.asyncio
async def test_inflight_failure_precise_records_nothing_when_update_matched_no_row(monkeypatch):
    """The precise path's conditional UPDATE may match nothing (the message was
    already terminal, or the id doesn't belong to this session). A claimed
    history row for a move the machine rejected would be worse than none."""
    from node_server.task_message_status import fail_inflight_messages

    conn = _Conn(row=None)  # precise UPDATE matched no row
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await fail_inflight_messages("sess-1", "provider 429", client_message_id="msg-x")
    assert conn.history_rows() == []


@pytest.mark.asyncio
async def test_inflight_failure_falls_back_to_session_when_id_is_blank(monkeypatch):
    """An empty client_message_id (helper returned "" because the error frame had
    no message context) must behave like None — session-wide close-out, not a
    precise UPDATE against an empty id."""
    from node_server.task_message_status import fail_inflight_messages

    conn = _Conn(rows=[
        {"id": "e1", "task_id": "t1", "client_message_id": "msg-1", "delivery_attempt": 1},
    ])
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await fail_inflight_messages("sess-1", "provider 429", client_message_id="")
    # Fallback path uses fetch (session-wide), so the row is recorded with an
    # empty from_val — same shape as the no-id case.
    rows = [_fields(*e) for e in conn.history_rows()]
    assert len(rows) == 1
    assert rows[0]["from_val"] == ""
