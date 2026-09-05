from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from node_server.terminal_bridge import NodeTerminalSession, PersistentTerminalRegistry


class FakeSession:
    def __init__(self, terminal_id: str):
        self.terminal_id = terminal_id
        self.closed = False
        self.inputs: list[bytes] = []
        self._output: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def iter_output(self):
        try:
            while True:
                item = await self._output.get()
                if item is None:
                    return
                yield item
        finally:
            self.closed = True

    def send_input(self, data: bytes) -> None:
        self.inputs.append(data)

    def resize(self, rows: int, cols: int) -> None:
        pass

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self._output.put_nowait(None)


class FakeManager:
    def __init__(self):
        self.sessions: dict[str, FakeSession] = {}

    def open(self, node_id: str, *, terminal_id: str, **kwargs):
        session = FakeSession(terminal_id)
        self.sessions[terminal_id] = session
        return session


@pytest.mark.asyncio
async def test_persistent_terminals_list_reconnect_and_delete():
    manager = FakeManager()
    registry = PersistentTerminalRegistry(manager, inactivity_timeout=3600)

    first = await registry.get_or_create("workspace-a", "node-a", "term-1")
    second = await registry.get_or_create("workspace-a", "node-a", "term-2")
    assert await registry.get_or_create("workspace-a", "node-a", "term-1") is first

    listed = await registry.list("workspace-a")
    assert {item["id"] for item in listed} == {"term-1", "term-2"}
    assert await registry.list("workspace-b") == []

    subscriber = first.subscribe()
    await manager.sessions["term-1"]._output.put(b"hello")
    assert await asyncio.wait_for(subscriber.get(), timeout=1) == b"hello"
    first.unsubscribe(subscriber)

    replay = first.subscribe()
    assert await asyncio.wait_for(replay.get(), timeout=1) == b"hello"
    first.unsubscribe(replay)

    assert await registry.delete("workspace-a", "term-1") is True
    assert first.closed is True
    assert await registry.delete("workspace-a", "term-1") is False
    assert [item["id"] for item in await registry.list("workspace-a")] == [second.terminal_id]

    await registry.delete("workspace-a", "term-2")


class _FakeConn:
    """Minimum Connection surface for NodeTerminalSession: a terminal queue
    plus the register/deregister calls."""

    def __init__(self) -> None:
        self._terminals: dict[str, asyncio.Queue] = {}

    def open_terminal(self, terminal_id: str) -> asyncio.Queue:
        ch: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._terminals[terminal_id] = ch
        return ch

    def close_terminal(self, terminal_id: str) -> None:
        self._terminals.pop(terminal_id, None)

    def send(self, _frame) -> None:  # noqa: ANN001 - shape not used by this test
        pass


@pytest.mark.asyncio
async def test_terminal_session_release_wakes_blocked_pump():
    """_release() must enqueue a None sentinel so a pump blocked on
    queue.get() returns instead of hanging close()/delete()."""
    conn = _FakeConn()
    session = NodeTerminalSession(conn, terminal_id="t-rel")
    async def collect() -> list[bytes]:
        return [chunk async for chunk in session.iter_output()]

    pump = asyncio.create_task(collect())
    session._release()
    chunks = await asyncio.wait_for(pump, timeout=1)
    assert chunks == []
    assert session.closed is True
    assert "t-rel" not in conn._terminals
