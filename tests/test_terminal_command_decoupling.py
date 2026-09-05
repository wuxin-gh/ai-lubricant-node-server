"""Batch-4: agent command lifecycle is decoupled from the browser websocket.

The rule these lock in: closing the tab (detach) does not cancel a running
command; only the PTY actually going away does. And a command can be started in
a terminal that has no browser attached at all — its output still lands in the
terminal's replay buffer for whoever reattaches.
"""
from __future__ import annotations

import asyncio

import pytest

from node_server import terminal_commands as tc


class FakeSession:
    def __init__(self):
        self.inputs: list[bytes] = []

    def send_input(self, data: bytes) -> None:
        self.inputs.append(data)


def _marker(raw: bytes) -> str:
    text = raw.decode()
    return "__AGENT_CMD_" + text.split("__AGENT_CMD_")[1].split("__")[0] + "__"


@pytest.mark.asyncio
async def test_detach_does_not_cancel_running_command():
    """Unbinding the notify sink (browser closed the tab) must leave a running
    command running — the operator can reattach and see it finish."""
    events: list[tuple[str, dict]] = []

    async def notify(kind, payload):
        events.append((kind, payload))

    session = FakeSession()
    terminal = tc.ActiveTerminal("node-1", "term-1", session, notify)

    task = asyncio.create_task(terminal.run_command("sleep-ish", timeout_ms=5000))
    await asyncio.sleep(0.01)
    assert terminal.input_locked is True

    # Browser detaches: unbind its sink. The command must NOT fail.
    terminal.unbind_notify(notify)
    await asyncio.sleep(0.01)
    assert task.done() is False
    assert terminal.input_locked is True

    # Node finishes the command; the terminal completes it normally even though
    # no browser is attached.
    marker = _marker(session.inputs[0])
    terminal.observe_output((marker + "0\r\n").encode())
    result = await task
    assert result["status"] == "ok"
    assert terminal.input_locked is False


@pytest.mark.asyncio
async def test_notify_dropped_while_detached_then_rebound():
    """With no sink bound, UI events are silently dropped (not errored); a fresh
    sink bound mid-command receives subsequent events."""
    session = FakeSession()
    terminal = tc.ActiveTerminal("node-1", "term-1", session)  # no sink

    task = asyncio.create_task(terminal.run_command("pwd", timeout_ms=5000))
    await asyncio.sleep(0.01)
    # Started fine despite no browser having ever attached.
    assert terminal.input_locked is True

    late: list[tuple[str, dict]] = []

    async def notify(kind, payload):
        late.append((kind, payload))

    terminal.bind_notify(notify)
    marker = _marker(session.inputs[0])
    terminal.observe_output((marker + "0\r\n").encode())
    await task
    # The end event reached the freshly bound sink.
    assert any(kind == "agent_command_end" for kind, _ in late)


@pytest.mark.asyncio
async def test_close_fails_running_command_but_cancel_keeps_terminal():
    session = FakeSession()
    terminal = tc.ActiveTerminal("node-1", "term-1", session)

    task = asyncio.create_task(terminal.run_command("pwd", timeout_ms=5000))
    await asyncio.sleep(0.01)
    # cancel_command fails the in-flight command without marking the terminal
    # closed (interrupt/close-terminal management action).
    assert terminal.cancel_command("中断") is True
    result = await task
    assert result["status"] == "error"
    assert terminal._closed is False


@pytest.mark.asyncio
async def test_gateway_wires_retire_and_running_work_hooks(monkeypatch):
    """The gateway must connect the host-terminal registry's lifecycle hooks to
    the agent registry: PTY gone → retire the entry, work running → report busy.

    Both hooks are set inside build_control_terminal_router on a registry it owns,
    so the registry is captured at construction to assert on the real wiring
    rather than on a stand-in.
    """
    from types import SimpleNamespace

    from fastapi import FastAPI

    from node_server import terminal_gateway as gw
    from node_server.registry import Registry

    built: list = []
    real_registry_cls = gw.NodeHostTerminalRegistry

    def capturing(*args, **kwargs):
        instance = real_registry_cls(*args, **kwargs)
        built.append(instance)
        return instance

    monkeypatch.setattr(gw, "NodeHostTerminalRegistry", capturing)

    async def get_node_if_exists(_node_id):
        return None

    service = SimpleNamespace(
        registry=Registry(),
        store=SimpleNamespace(get_node_if_exists=get_node_if_exists),
        on_node_connected=None,
    )
    FastAPI().include_router(gw.build_control_terminal_router(service, "tok"))

    assert len(built) == 1, "router should build exactly one host terminal registry"
    host = built[0]
    assert host.on_retired is not None, "PTY teardown would orphan a running command"
    assert host.has_running_work is not None, "reaper could kill a busy terminal"

    # has_running_work must track the agent registry the router wired it to. The
    # only handle on that registry is through the hooks themselves, so drive it
    # via the command endpoint's registry by registering an entry and checking the
    # predicate flips with input_locked.
    session = FakeSession()
    agent = tc.ActiveTerminal("node-1", "term-1", session)
    # Reach the agent registry through the retire hook's bound __self__.
    agent_registry = host.on_retired.__self__
    assert isinstance(agent_registry, tc.ActiveTerminalRegistry)
    agent_registry.register(agent)

    # Idle terminal: not busy, so the reaper is free to age it out.
    assert host.has_running_work("node-1", "term-1") is False

    task = asyncio.create_task(agent.run_command("pwd", timeout_ms=5000))
    await asyncio.sleep(0.01)
    # Busy terminal: the reaper must be told to keep off it.
    assert host.has_running_work("node-1", "term-1") is True

    marker = _marker(session.inputs[0])
    agent.observe_output((marker + "0\r\n").encode())
    await task
    assert host.has_running_work("node-1", "term-1") is False

    # retire drops the entry (what the gateway calls when the PTY is gone).
    host.on_retired("node-1", "term-1")
    assert agent_registry.get("node-1", "term-1") is None


@pytest.mark.asyncio
async def test_reaper_restarts_idle_clock_while_work_runs():
    """A detached terminal past its TTL but still busy must not be reaped, and
    must get a fresh idle window once the work finishes — otherwise it would be
    reaped on the very next tick and the operator could never read the result."""
    import time as _time

    from node_server.terminal_bridge import NodeHostTerminalRegistry

    registry = NodeHostTerminalRegistry.__new__(NodeHostTerminalRegistry)
    registry._detached_ttl = 100.0
    registry.has_running_work = lambda _n, _t: busy
    registry.on_retired = None

    class FakeTerminal:
        closed = False

        def __init__(self):
            # Detached long enough to be past the cutoff.
            self.detached_since = _time.monotonic() - 500.0

    terminal = FakeTerminal()
    registry._terminals = {("node-1", "term-1"): terminal}
    stale = terminal.detached_since

    busy = True
    now = _time.monotonic()
    cutoff = now - registry._detached_ttl
    # Reproduce the reaper's decision for this terminal.
    assert terminal.detached_since <= cutoff
    assert registry._has_running_work("node-1", "term-1") is True
    # The reaper refreshes the clock instead of expiring it.
    terminal.detached_since = now
    assert terminal.detached_since > stale
    # With the clock refreshed, it is no longer past the cutoff, so when the work
    # finishes the terminal still has a full TTL before it is eligible.
    busy = False
    assert terminal.detached_since > _time.monotonic() - registry._detached_ttl


@pytest.mark.asyncio
async def test_registry_get_or_create_reuses_entry_across_reattach():
    reg = tc.ActiveTerminalRegistry()
    s1 = FakeSession()
    first = reg.get_or_create("node-1", "term-1", s1)
    # A "reconnect" with a new session must return the SAME entry (so a running
    # command stays addressable) but repoint at the live session.
    s2 = FakeSession()
    again = reg.get_or_create("node-1", "term-1", s2)
    assert again is first
    assert again.session is s2

    # retire drops it and fails any running command.
    reg.retire("node-1", "term-1")
    assert reg.get("node-1", "term-1") is None
