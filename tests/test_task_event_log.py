"""Normalized conversation items are durable without an SSE subscriber.

The node control process persists every replayable item at the single upstream
choke point, so a task page opened after a turn ran (or while no browser is
attached) still shows the conversation. These run against a stubbed asyncpg
pool and a stubbed ClickHouse insert, so neither store needs to be live.

Storage split (see ``task_event_log.record_session_event``):

* ClickHouse ``task_messages``: one row per frame, append-only, merged on the
  read side by ``logical_event_id``.
* PostgreSQL ``mc_task_events``: a thin index row per frame
  (``kind='item_ref'``, ``logical_event_id``, NULL ``payload``) so the
  delivery-status machine and the seq paging cursor have something to join on.
* Fallback: when the CH insert reports failure, the PG row keeps the whole
  envelope in ``payload`` (``kind='item'``) — a CH-less install still renders
  history, just without the append-only trail.

Only ``insert_task_message`` is stubbed; ``build_row`` runs for real, so the
column-index assertions below also pin the row's column order against
``task_message_store.COLUMN_NAMES``.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

import node_server.task_message_store as task_message_store
from node_server.task_event_log import record_session_event

# Column positions in a ``task_messages`` row, by name, so the assertions read
# as the schema does rather than as bare integers.
_COL = {name: index for index, name in enumerate(task_message_store.COLUMN_NAMES)}


class _FakeConn:
    """Stub asyncpg connection.

    The writer now runs exactly three queries: the task lookup (``fetchrow``),
    the seq allocation (``fetchval``), and one INSERT (``execute``). There is no
    read-merge-update anymore — every frame appends, so nothing is read back
    before writing.
    """

    def __init__(self, task_row: dict | None, next_seq: int = 1):
        self.task_row = task_row
        self.next_seq = next_seq
        self.fetchrows: list[tuple[str, tuple[Any, ...]]] = []
        self.fetchvals: list[tuple[str, tuple[Any, ...]]] = []
        self.executes: list[tuple[str, tuple[Any, ...]]] = []

    async def fetchrow(self, query: str, *params: Any):
        self.fetchrows.append((query, params))
        return self.task_row

    async def fetchval(self, query: str, *params: Any):
        self.fetchvals.append((query, params))
        return self.next_seq

    async def execute(self, query: str, *params: Any):
        self.executes.append((query, params))
        return "INSERT 0 1"

    def seq_allocations(self) -> list[tuple[str, tuple[Any, ...]]]:
        """seq comes from the shared ``mc_task_events_seq`` SEQUENCE.

        It used to be a per-task ``MAX(seq)+1``, which raced across the two
        writers (gateway + node_server) on separate connections: both read the
        same max, both inserted max+1, and the ``(seq, id)`` paging cursor then
        repeated or skipped rows at a page boundary landing inside the tie.
        """
        return [call for call in self.fetchvals if "nextval(" in call[0]]

    def inserts(self) -> list[tuple[str, tuple[Any, ...]]]:
        return [call for call in self.executes if "INSERT INTO mc_task_events" in call[0]]


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self.conn = conn

    def acquire(self):
        conn = self.conn

        class _Ctx:
            async def __aenter__(self_inner):
                return conn

            async def __aexit__(self_inner, *_exc):
                return False

        return _Ctx()


class _CHRecorder:
    """Records the rows handed to ``insert_task_message`` and its verdict.

    ``ok=False`` covers both real-world failure modes with one switch, because
    the writer cannot tell them apart and must not: CH not configured at all
    (``_client is None``) and a CH write that errored. Both return False, and
    both must take the PostgreSQL fallback.
    """

    def __init__(self, ok: bool = True):
        self.ok = ok
        self.rows: list[list] = []

    async def __call__(self, row: list) -> bool:
        self.rows.append(row)
        return self.ok

    def field(self, index: int, column: str):
        return self.rows[index][_COL[column]]

    def item(self, index: int) -> dict:
        return json.loads(self.rows[index][_COL["item_json"]])


def _install(monkeypatch, task_row: dict | None, next_seq: int = 1, *, ch_ok: bool = True):
    conn = _FakeConn(task_row, next_seq)
    monkeypatch.setattr("node_server.shared_store._pool", _FakePool(conn))
    recorder = _CHRecorder(ok=ch_ok)
    monkeypatch.setattr(task_message_store, "insert_task_message", recorder)
    return conn, recorder


def _frame(item: dict, *, agent_id: str = "", runtime_seq: int = 1) -> str:
    """A runtime agent_event frame wrapping one normalized item."""
    return json.dumps({
        "v": 1,
        "seq": runtime_seq,
        "type": "agent_event",
        "agent_id": agent_id,
        "item": item,
    })


@pytest.mark.asyncio
async def test_content_goes_to_clickhouse_and_pg_keeps_a_thin_index_row(monkeypatch):
    conn, ch = _install(monkeypatch, {"id": "task-1"}, next_seq=9)

    await record_session_event(
        "session-1",
        seq=17,
        event_type="agent_event",
        item_type="agent_message",
        agent_id="agent-root",
        payload_json=_frame({"id": "m1", "type": "agent_message", "text": "完成了"}, runtime_seq=17),
    )

    lookup, lookup_params = conn.fetchrows[0]
    assert "node_session_id=$1 OR id::text=$1" in lookup
    assert lookup_params == ("session-1",)
    # Allocated from the shared sequence, so the call carries no task parameter.
    assert conn.seq_allocations()[0][1] == ()

    # ClickHouse holds the content, keyed by the runtime's own seq.
    assert ch.field(0, "task_id") == "task-1"
    assert ch.field(0, "logical_event_id") == "m1"
    assert ch.field(0, "seq") == 17
    assert ch.field(0, "item_type") == "agent_message"
    assert ch.field(0, "agent_id") == "agent-root"
    # version = seq, so a retry of the same frame collapses instead of duplicating.
    assert ch.field(0, "version") == 17
    envelope = ch.item(0)
    assert envelope["item"]["text"] == "完成了"
    assert envelope["runtime_seq"] == 17

    # PostgreSQL holds state + index only: no payload column in the INSERT.
    insert, params = conn.inserts()[0]
    assert "'item_ref'" in insert
    assert "payload" not in insert
    assert params[1] == "task-1"
    assert params[2] == 9  # replay cursor from mc_task_events_seq, not the runtime seq
    assert params[3] == "agent_message"  # resolved item type, not the frame type
    assert params[4] == "m1"  # the join key back to ClickHouse


@pytest.mark.asyncio
async def test_re_report_appends_a_second_frame_instead_of_merging_in_place(monkeypatch):
    """A tool call's opening and closing reports are two rows, not one.

    The old path read the stored row, merged the sparse completion onto it, and
    UPDATEd — which cost a read per frame and destroyed the trail: a merged row
    can no longer say what the runtime reported, or in what order. Appending
    keeps both reports; the read side merges by ``logical_event_id`` with the
    same field-level last-wins the client already does.
    """
    conn, ch = _install(monkeypatch, {"id": "task-1"}, next_seq=4)

    await record_session_event(
        "session-1", seq=18, event_type="agent_event", item_type="tool_call",
        agent_id="",
        payload_json=_frame({"id": "t1", "type": "tool_call", "title": "Read", "status": "running"}),
    )
    await record_session_event(
        "session-1", seq=19, event_type="agent_event", item_type="tool_call",
        agent_id="",
        payload_json=_frame({"id": "t1", "type": "tool_call", "output": "ok", "status": "done"}),
    )

    # Two CH rows: same logical item, different seq — that ordering is the merge input.
    assert [ch.field(i, "logical_event_id") for i in (0, 1)] == ["t1", "t1"]
    assert [ch.field(i, "seq") for i in (0, 1)] == [18, 19]
    assert ch.field(0, "status") == "running"
    assert ch.field(1, "status") == "done"
    # Two PG index rows, so the paging cursor can walk to either frame.
    assert len(conn.inserts()) == 2
    # Nothing was read back before writing.
    assert len(conn.fetchrows) == 2  # only the two task lookups


@pytest.mark.asyncio
async def test_sparse_completion_no_longer_needs_a_write_side_merge(monkeypatch):
    """The completion frame carries only {id, type, output, status}.

    Under the old blind-overwrite bug this erased the opening report's ``title``
    and ``input``, so a replayed transcript showed an untitled card whose label
    fell back to the raw protocol type ("tool_call") — the complaint behind the
    mobile fix, where an MCP tool call lost its ``mcp__server__tool`` name on
    refresh. Append-only makes that class of bug unreachable on the write side:
    the opening frame is still there, verbatim, as its own row.
    """
    conn, ch = _install(monkeypatch, {"id": "task-1"})

    await record_session_event(
        "session-1", seq=10, event_type="agent_event", item_type="tool_call",
        agent_id="",
        payload_json=_frame({
            "id": "t1", "type": "tool_call",
            "title": "mcp__github__search_code", "input": {"q": "x"}, "status": "running",
        }),
    )
    await record_session_event(
        "session-1", seq=11, event_type="agent_event", item_type="tool_call",
        agent_id="",
        payload_json=_frame({"id": "t1", "type": "tool_call", "output": "found", "status": "done"}),
    )

    opening = ch.item(0)["item"]
    completion = ch.item(1)["item"]
    assert opening["title"] == "mcp__github__search_code"
    assert opening["input"] == {"q": "x"}
    assert completion["output"] == "found"
    assert completion["status"] == "done"
    # The tool name is also a CH column, so the read path can label the card
    # without parsing item_json.
    assert ch.field(0, "tool_name") == "mcp__github__search_code"


@pytest.mark.asyncio
async def test_item_without_id_gets_a_per_frame_key(monkeypatch):
    """No id means no stable key, so nothing can ever merge onto this frame.

    A fresh uuid keeps it addressable anyway: ``logical_event_id`` is NOT NULL
    on the CH side and is the PG index row's only join key, so leaving it empty
    would make the frame unreachable from the reference row.
    """
    conn, ch = _install(monkeypatch, {"id": "task-1"}, next_seq=5)

    await record_session_event(
        "session-1", seq=1, event_type="agent_event", item_type="agent_message",
        agent_id="", payload_json=_frame({"type": "agent_message", "text": "no id"}),
    )

    key = ch.field(0, "logical_event_id")
    assert len(key) == 36  # uuid4
    # PG's index row points at the same synthetic key.
    assert conn.inserts()[0][1][4] == key


@pytest.mark.asyncio
async def test_unknown_session_writes_nothing(monkeypatch):
    conn, ch = _install(monkeypatch, None)

    await record_session_event(
        "missing", seq=1, event_type="agent_event", item_type="agent_message",
        agent_id="", payload_json=_frame({"id": "x", "type": "agent_message", "text": "hi"}),
    )

    assert ch.rows == []
    assert conn.fetchvals == []
    assert conn.executes == []


@pytest.mark.asyncio
async def test_non_replayable_items_are_skipped(monkeypatch):
    """Lifecycle/telemetry frames (turn started, usage, todos) drive live UI but
    are not conversation content — replaying them would add rows a reader can't
    use. The filter keeps only items that stand alone in history."""
    conn, ch = _install(monkeypatch, {"id": "task-1"})

    await record_session_event(
        "session-1", seq=1, event_type="agent_turn_started", item_type="",
        agent_id="", payload_json=_frame({"id": "lc", "type": "turn_started"}),
    )
    await record_session_event(
        "session-1", seq=2, event_type="agent_event", item_type="usage",
        agent_id="", payload_json=_frame({"id": "u", "type": "usage", "tokens": 10}),
    )

    assert ch.rows == []
    assert conn.executes == []


@pytest.mark.asyncio
async def test_large_tool_output_is_bounded(monkeypatch):
    conn, ch = _install(monkeypatch, {"id": "task-1"})

    big = "x" * (257 * 1024)
    await record_session_event(
        "session-1", seq=2, event_type="agent_event", item_type="tool_call",
        agent_id="",
        payload_json=_frame({"id": "t1", "type": "tool_call", "title": "Bash", "output": big}),
    )

    item = ch.item(0)["item"]
    assert item["truncated"] is True
    assert item["size"] > 256 * 1024


@pytest.mark.asyncio
async def test_canonical_envelope_fields_land_in_their_own_columns(monkeypatch):
    """The canonical fields are CH columns, not just envelope keys, so replay
    routes on protocol fields (subagent_id/event_kind/tool_name/…) without
    decoding ``item_json`` — and can filter on them server-side."""
    conn, ch = _install(monkeypatch, {"id": "task-1"})

    await record_session_event(
        "session-1", seq=5, event_type="agent_event", item_type="tool_call",
        agent_id="call_agent1",
        payload_json=_frame(
            {"id": "toolu_01", "type": "tool_call", "title": "WebSearch", "status": "done"},
            agent_id="call_agent1",
        ),
        logical_event_id="toolu_01",
        event_kind="tool",
        tool_name="WebSearch",
        subagent_id="call_agent1",
        phase="complete",
        status="done",
    )

    assert ch.field(0, "logical_event_id") == "toolu_01"
    assert ch.field(0, "event_kind") == "tool"
    assert ch.field(0, "tool_name") == "WebSearch"
    assert ch.field(0, "subagent_id") == "call_agent1"
    assert ch.field(0, "phase") == "complete"
    assert ch.field(0, "status") == "done"
    # The legacy alias stays inside the envelope for old readers.
    assert ch.item(0)["agent_id"] == "call_agent1"


@pytest.mark.asyncio
async def test_canonical_fields_recovered_from_item_and_frame(monkeypatch):
    """A sparse frame may drop the canonical fields the proto carried — they are
    recovered from the item body, then the frame root, before persisting."""
    conn, ch = _install(monkeypatch, {"id": "task-1"})

    frame = json.dumps({
        "v": 1, "seq": 3, "type": "agent_event",
        "agent_id": "call_agent2",
        "item": {"id": "toolu_02", "type": "tool_call", "title": "Edit", "status": "running", "phase": "start"},
    })
    await record_session_event(
        "session-1", seq=3, event_type="agent_event", item_type="tool_call",
        agent_id="call_agent2", payload_json=frame,
    )

    # tool_name from item.title, subagent_id from agent_id, phase/status from item.
    assert ch.field(0, "tool_name") == "Edit"
    assert ch.field(0, "subagent_id") == "call_agent2"
    assert ch.field(0, "phase") == "start"
    assert ch.field(0, "status") == "running"


@pytest.mark.asyncio
async def test_merge_key_prefers_the_explicit_logical_id(monkeypatch):
    """``logical_event_id`` is what collapses a re-report onto one item, so it
    is taken from the explicit parameter first and the legacy ``item.id`` only
    as a fallback — frames of either shape converge on the same key."""
    conn, ch = _install(monkeypatch, {"id": "task-1"})

    await record_session_event(
        "session-1", seq=8, event_type="agent_event", item_type="tool_call",
        agent_id="",
        payload_json=_frame({"id": "toolu_03", "type": "tool_call", "title": "Read", "status": "running"}),
    )
    await record_session_event(
        "session-1", seq=9, event_type="agent_event", item_type="tool_call",
        agent_id="",
        payload_json=_frame({"type": "tool_call", "output": "contents", "status": "done"}),
        logical_event_id="toolu_03",
        tool_name="Read",
    )

    assert [ch.field(i, "logical_event_id") for i in (0, 1)] == ["toolu_03", "toolu_03"]
    # And both PG index rows carry it, so either frame can be found from PG.
    assert [call[1][4] for call in conn.inserts()] == ["toolu_03", "toolu_03"]


@pytest.mark.asyncio
async def test_clickhouse_failure_falls_back_to_the_postgres_payload(monkeypatch):
    """A frame must never be lost because ClickHouse is down or absent.

    ``insert_task_message`` returns False for both "not configured" and "write
    failed"; either way the PG row keeps the whole envelope and is marked
    ``kind='item'``, which is exactly how rows written before the split read —
    so the read path needs no special case for a degraded install.
    """
    conn, ch = _install(monkeypatch, {"id": "task-1"}, next_seq=11, ch_ok=False)

    await record_session_event(
        "session-1", seq=20, event_type="agent_event", item_type="agent_message",
        agent_id="agent-root",
        payload_json=_frame({"id": "m1", "type": "agent_message", "text": "hi"}),
    )

    # The write was attempted, and its refusal is what chose the fallback.
    assert len(ch.rows) == 1
    insert, params = conn.inserts()[0]
    assert "'item'" in insert and "'item_ref'" not in insert
    assert "$6::jsonb" in insert
    assert params[2] == 11  # still ordered by the shared sequence
    assert params[4] == "m1"  # index row still carries the join key
    payload = json.loads(params[5])
    assert payload["logical_event_id"] == "m1"
    assert payload["agent_id"] == "agent-root"
    assert payload["item"]["text"] == "hi"
