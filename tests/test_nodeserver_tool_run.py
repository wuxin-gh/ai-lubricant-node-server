"""Tool-run registry dispatch: open/deliver/close a tool-run event stream.

Exercises the Connection-level primitives the tunnel manager's dispatch
depends on, without sockets or the control-plane HTTP surface: a node streams
NodeToolRunEvent frames by run_id and a consumer drains them as a queue.
"""
from __future__ import annotations

import asyncio

import pytest

from node_server import agentcompose_v2_pb2 as pb
from node_server.registry import Connection


def _conn() -> Connection:
    return Connection(node_id="node-1", caps=None, peer_address="127.0.0.1:1")


def test_open_deliver_close_tool_run():
    conn = _conn()
    ch = conn.open_tool_run("run-1")

    async def drain():
        # An event for a different run_id is dropped (no consumer registered).
        conn.deliver_tool_run_event(pb.NodeToolRunEvent(run_id="other", kind=pb.NODE_TOOL_RUN_KIND_STDOUT, data=b"x"))
        # Events for run-1 reach the consumer in order.
        conn.deliver_tool_run_event(pb.NodeToolRunEvent(run_id="run-1", kind=pb.NODE_TOOL_RUN_KIND_STDOUT, data=b"hello"))
        conn.deliver_tool_run_event(pb.NodeToolRunEvent(run_id="run-1", kind=pb.NODE_TOOL_RUN_KIND_STDERR, data=b"err"))
        conn.deliver_tool_run_event(pb.NodeToolRunEvent(run_id="run-1", kind=pb.NODE_TOOL_RUN_KIND_EXITED, exit_code=0))
        first = await asyncio.wait_for(ch.get(), timeout=1)
        second = await asyncio.wait_for(ch.get(), timeout=1)
        third = await asyncio.wait_for(ch.get(), timeout=1)
        return first, second, third

    first, second, third = asyncio.run(drain())
    assert (first.kind, first.data) == (pb.NODE_TOOL_RUN_KIND_STDOUT, b"hello")
    assert (second.kind, second.data) == (pb.NODE_TOOL_RUN_KIND_STDERR, b"err")
    assert (third.kind, third.exit_code) == (pb.NODE_TOOL_RUN_KIND_EXITED, 0)
    conn.close_tool_run("run-1")
    # After close, events are dropped silently.
    conn.deliver_tool_run_event(pb.NodeToolRunEvent(run_id="run-1", kind=pb.NODE_TOOL_RUN_KIND_STDOUT, data=b"late"))


def test_active_tool_run_inventory():
    conn = Connection("node-1", None)
    conn.note_active_tool_runs([
        pb.NodeActiveToolRun(run_id="tunnel-runtime:r1", revision=3, pid=4321),
    ])
    assert conn.active_tool_runs() == [
        {"run_id": "tunnel-runtime:r1", "revision": 3, "pid": 4321}
    ]


def test_started_event_fields_are_available():
    evt = pb.NodeToolRunEvent(
        run_id="tunnel-runtime:r1",
        kind=pb.NODE_TOOL_RUN_KIND_STARTED,
        revision=7,
        pid=9876,
    )
    assert evt.kind == pb.NODE_TOOL_RUN_KIND_STARTED
    assert evt.revision == 7
    assert evt.pid == 9876


def test_close_wakes_blocked_consumer():
    conn = _conn()
    ch = conn.open_tool_run("run-2")

    async def main() -> None:
        conn.close()
        # close() enqueues a None sentinel for every tool-run consumer.
        item = await asyncio.wait_for(ch.get(), timeout=1)
        assert item is None

    asyncio.run(main())
