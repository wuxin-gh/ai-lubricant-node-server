from __future__ import annotations

import json

import pytest

from node_server import shared_store
from node_server.task_message_status import record_message_status


class _Conn:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []

    async def fetchrow(self, sql: str, *args):
        self.calls.append((sql, args))
        # UPDATE ... RETURNING now returns a row that also carries the pre-image
        # ``prev_status`` (via the prev CTE) for the history trail. The history
        # helper only needs the post-update values, but the column must be in
        # the result to match real Postgres.
        return {
            "id": "event-id",
            "task_id": "task-1",
            "prev_status": "dispatching",
        }

    async def fetchval(self, sql: str, *args):
        return await self.fetchrow(sql, *args)

    async def execute(self, sql: str, *args):
        return None


class _Acquire:
    def __init__(self, conn: _Conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *_args):
        return False


class _Pool:
    def __init__(self, conn: _Conn):
        self.conn = conn

    def acquire(self):
        return _Acquire(self.conn)


@pytest.mark.asyncio
async def test_input_received_updates_matching_attempt(monkeypatch):
    conn = _Conn()
    pool = _Pool(conn)
    monkeypatch.setattr(shared_store, "pool", lambda: pool)

    await record_message_status(
        "session-1",
        "input_status",
        json.dumps({
            "message_id": "message-1",
            "delivery_attempt": 2,
            "status": "received",
        }),
    )

    assert len(conn.calls) == 1
    sql, args = conn.calls[0]
    assert "received_at=now()" in sql
    assert "delivery_attempt=$4" in sql
    assert args[:4] == ("session-1", "message-1", "received", 2)
    # Only a dispatching message may be ACKed. node_server used to also allow
    # ``pending → received``, which the gateway rejects — that drift is what the
    # shared table (and tests/test_message_status_machine_parity.py) removed: a
    # message the gateway never dispatched must not appear ACKed.
    assert set(args[4]) == {"dispatching"}


@pytest.mark.asyncio
async def test_completed_turn_cannot_regress_old_attempt(monkeypatch):
    conn = _Conn()
    pool = _Pool(conn)
    monkeypatch.setattr(shared_store, "pool", lambda: pool)

    await record_message_status(
        "session-1",
        "agent_turn_completed",
        json.dumps({
            "messageId": "message-1",
            "deliveryAttempt": 3,
            "status": "completed",
        }),
    )

    sql, args = conn.calls[0]
    assert "completed_at=now()" in sql
    assert args[2] == "completed"
    assert args[3] == 3
    # received/running are the normal paths; ``failed → completed`` is allowed
    # because a turn that emitted an error frame and then finished normally must
    # end up completed — the authoritative turn-end frame wins over the
    # in-flight failure that ``fail_inflight_messages`` recorded. A late ACK for
    # an older attempt is still blocked by the delivery_attempt predicate in the
    # same statement.
    assert set(args[4]) == {"received", "running", "failed"}


@pytest.mark.asyncio
async def test_failed_turn_records_reason(monkeypatch):
    conn = _Conn()
    pool = _Pool(conn)
    monkeypatch.setattr(shared_store, "pool", lambda: pool)

    await record_message_status(
        "session-1",
        "input_status",
        json.dumps({
            "message_id": "message-1",
            "delivery_attempt": 1,
            "status": "failed",
            "error": "provider unavailable",
        }),
    )

    sql, args = conn.calls[0]
    assert "failure_reason" in sql
    assert args[:5] == (
        "session-1", "message-1", "failed", "provider unavailable", 1,
    )
    assert set(args[5]) == {"dispatching", "pending", "received", "running"}


@pytest.mark.asyncio
async def test_unrelated_structured_event_is_ignored(monkeypatch):
    conn = _Conn()
    pool = _Pool(conn)
    monkeypatch.setattr(shared_store, "pool", lambda: pool)

    await record_message_status(
        "session-1",
        "agent_event",
        json.dumps({"message_id": "message-1", "status": "completed"}),
    )

    assert conn.calls == []


# --- error frame message-id extraction (payload-embedded scheme) ------------


def test_error_message_id_reads_snake_case_field():
    from node_server.task_message_status import error_message_id_from_payload

    assert error_message_id_from_payload(
        json.dumps({"type": "error", "message_id": "msg-1", "code": "x"})
    ) == "msg-1"


def test_error_message_id_reads_camel_case_field():
    from node_server.task_message_status import error_message_id_from_payload

    # The runtime emits messageId (camelCase); both spellings are accepted so a
    # rename on one side never silently drops the join key.
    assert error_message_id_from_payload(
        json.dumps({"type": "error", "messageId": "msg-2"})
    ) == "msg-2"


def test_error_message_id_is_empty_when_frame_has_no_id():
    from node_server.task_message_status import error_message_id_from_payload

    # An error frame with no message context (parse failure / outer fallback).
    # Empty → caller falls back to session-wide failure marking.
    assert error_message_id_from_payload(
        json.dumps({"type": "error", "code": "runtime_stream_error", "message": "boom"})
    ) == ""
    assert error_message_id_from_payload("") == ""
    assert error_message_id_from_payload("not json") == ""


def test_error_message_id_is_empty_when_json_is_not_an_object():
    from node_server.task_message_status import error_message_id_from_payload

    # json.loads succeeds but yields a scalar/array — the helper guards against
    # non-dict payloads before reaching .get().
    assert error_message_id_from_payload(json.dumps([1, 2, 3])) == ""
    assert error_message_id_from_payload(json.dumps("x")) == ""
