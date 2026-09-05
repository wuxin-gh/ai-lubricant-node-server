"""Disconnect-driven reconcile: mark a node's hosted MCPs dead + preserve the
terminal-reattach hook. Pins two regressions fixed together:

* the reconcile used to ``from mcp_runtime.node_hosted import reconcile_node``.
  That module top-level-imports the data-service ``mcp_plugin_store`` (a flat
  import that only resolves when ``server/`` is on sys.path), and the standalone
  control service (``python -m node_server``, its own container, no ``server/``
  on path) raised ``ModuleNotFoundError`` — so hosted MCPs were never marked
  dead on drop and the agent ready-gate let an unreachable MCP through to
  call_tool. The reconcile now runs in-process over the shared pool with raw
  SQL mirroring the data-service ``mark_host_state``/``mark_install_state``
  offline branch.
* ``on_node_connected`` is a wiring-time hook (terminal gateway reattaches host
  terminals to a fresh connection after a drop). It once sat misindented at the
  tail of ``_on_node_disconnect``, so every disconnect nulled it — after the
  FIRST drop, no reconnect ever reattached host terminals again.
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from node_server import crypto, shared_store
from node_server.node_hosted_reconcile import mark_node_hosted_offline
from node_server.registry import Registry
from node_server.service import NodeService

_MASTER_KEY_HEX = "00" * 32


def _service() -> NodeService:
    """Real NodeService: exercises the genuine __init__ + _on_node_disconnect."""
    return NodeService(
        master_key=crypto.parse_master_key(_MASTER_KEY_HEX),
        server_url="http://127.0.0.1:8001",
        store=object(),
        registry=Registry(),
    )


class _Conn:
    """Minimal asyncpg-shaped connection: records every SQL call."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self._rows = rows or []

    async def fetch(self, sql: str, *args: Any):
        self.calls.append((sql, args))
        return self._rows

    async def execute(self, sql: str, *args: Any):
        self.calls.append((sql, args))
        return "UPDATE 1"


class _Pool:
    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def acquire(self):
        conn = self._conn

        class _Ctx:
            async def __aenter__(self_inner):
                return conn

            async def __aexit__(self_inner, *exc):
                return False

        return _Ctx()


# --- mark_node_hosted_offline ------------------------------------------------


@pytest.mark.asyncio
async def test_marks_each_hosted_service_dead_and_error(monkeypatch):
    conn = _Conn(rows=[{"id": 7}, {"id": 9}])
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await mark_node_hosted_offline("node-1")

    updates = [c for c in conn.calls if c[0].startswith("UPDATE")]
    assert len(updates) == 2
    sql, params = updates[0]
    assert "host_status='dead'" in sql
    assert "install_state='error'" in sql
    assert "install_step=$2" in sql
    assert "install_error=$3" in sql
    assert "updated_at=now()" in sql
    # Identity columns are deliberately untouched: reconcile-on-reconnect needs
    # host_node_id + host_port + host_pid to find the process again.
    assert "host_node_id" not in sql
    assert "host_port" not in sql
    assert "host_pid" not in sql
    assert params == (7, "托管节点离线", "node node-1 offline")
    # Second row gets the same treatment.
    assert updates[1][1] == (9, "托管节点离线", "node node-1 offline")


@pytest.mark.asyncio
async def test_select_filters_to_node_hosted_scope(monkeypatch):
    conn = _Conn(rows=[])
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    await mark_node_hosted_offline("node-1")

    (select_sql, _) = conn.calls[0]
    assert "deploy_scope='node_hosted'" in select_sql
    assert "host_node_id=$1" in select_sql
    assert not any(c[0].startswith("UPDATE") for c in conn.calls)


@pytest.mark.asyncio
async def test_no_pool_is_a_silent_noop(monkeypatch):
    monkeypatch.setattr(shared_store, "_pool", None)
    await mark_node_hosted_offline("node-1")  # must not raise


@pytest.mark.asyncio
async def test_db_error_is_swallowed(monkeypatch):
    class _BoomConn:
        async def fetch(self, sql: str, *args: Any):
            raise RuntimeError("db down")

    monkeypatch.setattr(shared_store, "_pool", _Pool(_BoomConn()))
    await mark_node_hosted_offline("node-1")  # must not raise


@pytest.mark.asyncio
async def test_empty_node_id_is_a_noop():
    await mark_node_hosted_offline("")  # returns before touching the pool
    await mark_node_hosted_offline("   ")  # whitespace-only is empty too


# --- _on_node_disconnect wiring ----------------------------------------------


def test_on_node_connected_defaults_to_none_in_init():
    """__init__ seeds the hook to None so fire_node_connected can read it
    unconditionally — the old misindentation left it unset until a disconnect."""
    assert _service().on_node_connected is None


def test_disconnect_does_not_clear_on_node_connected():
    """The hook is wired once at startup; a disconnect must not null it. Run as a
    sync test so there is no running loop — the reconcile task is skipped via the
    RuntimeError branch, isolating the hook-preservation assertion."""
    svc = _service()

    async def _hook(node_id: str, conn: Any) -> None:
        return None

    svc.on_node_connected = _hook
    svc._on_node_disconnect("node-1")
    assert svc.on_node_connected is _hook


@pytest.mark.asyncio
async def test_disconnect_schedules_offline_marking(monkeypatch):
    """In a running loop, _on_node_disconnect fires the reconcile as a task."""
    conn = _Conn(rows=[{"id": 3}])
    monkeypatch.setattr(shared_store, "_pool", _Pool(conn))
    svc = _service()
    svc._on_node_disconnect("node-1")
    # Drain the task the disconnect scheduled.
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        await asyncio.gather(*pending)
    assert any(c[0].startswith("UPDATE") for c in conn.calls)
