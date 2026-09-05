"""Batch-3 management console: list / interrupt / close host terminals.

These exercise the real route handlers against a fake node connection so the
wiring is proven end to end: the downstream frame the service emits, the
upstream reply delivered through the registry's correlation map, and the
server-side overlay that turns the node's raw report into what the console
renders.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from node_server import agentcompose_v2_pb2 as pb
from node_server.registry import Connection, Registry
from node_server.store import NODE_STATUS_APPROVED
from node_server.terminal_gateway import build_control_terminal_router

TOKEN = "test-token"
AUTH = {"authorization": f"Bearer {TOKEN}"}
NODE = "node-a"


class _FakeStore:
    """Only the node lookups the terminal routes actually reach."""

    def __init__(self, *, status: str = NODE_STATUS_APPROVED) -> None:
        self._status = status

    async def get_node_if_exists(self, node_id: str):
        if node_id != NODE:
            return None
        return type(
            "Rec",
            (),
            {
                "id": node_id,
                "status": self._status,
                "capabilities": {"terminal": "true"},
                "role": "execution",
            },
        )()


class _FakeService:
    """NodeService surface the router uses, with a real Registry + Connection."""

    def __init__(self, store: _FakeStore) -> None:
        self.store = store
        self.registry = Registry()
        self.on_node_connected = None

    # The routes call these two; delegate to the genuine implementations by
    # importing them unbound so the correlation logic under test is the real one.
    async def query_terminals(self, node_id: str):
        from node_server.service import NodeService

        return await NodeService.query_terminals(self, node_id)

    async def interrupt_terminal(self, node_id: str, terminal_id: str):
        from node_server.service import NodeService

        return await NodeService.interrupt_terminal(self, node_id, terminal_id)


def _client(service) -> AsyncClient:
    app = FastAPI()
    app.include_router(build_control_terminal_router(service, TOKEN))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _answer_terminal_list(conn: Connection, terminals: list[dict]) -> None:
    """Play the node: read the downstream list request, reply upstream."""
    frame = await asyncio.wait_for(conn.downstream_get(), timeout=2)
    assert frame.WhichOneof("frame") == "terminal_list"
    request_id = frame.terminal_list.request_id
    result = pb.NodeTerminalListResult(request_id=request_id)
    for spec in terminals:
        result.terminals.append(pb.NodeTerminalStatus(**spec))
    conn.deliver_terminal_list(result)


@pytest.mark.asyncio
async def test_list_reports_node_terminals_with_server_overlay():
    service = _FakeService(_FakeStore())
    conn = service.registry.register(NODE, None)

    async with _client(service) as client:
        task = asyncio.create_task(
            client.get(f"/internal/node-terminals/{NODE}", headers=AUTH)
        )
        await _answer_terminal_list(
            conn,
            [
                {
                    "terminal_id": "t-1",
                    "current_command": "npm run dev",
                    "running": True,
                    "created_at": "2026-08-08T10:00:00Z",
                    "started_at": "2026-08-08T10:01:00Z",
                    "attached": True,
                },
                {
                    "terminal_id": "t-2",
                    "current_command": "",
                    "running": False,
                    "created_at": "2026-08-08T09:00:00Z",
                    "attached": False,
                },
            ],
        )
        resp = await asyncio.wait_for(task, timeout=3)

    assert resp.status_code == 200
    terminals = resp.json()["terminals"]
    # Newest first.
    assert [t["id"] for t in terminals] == ["t-1", "t-2"]
    running = terminals[0]
    assert running["current_command"] == "npm run dev"
    assert running["running"] is True
    assert running["node_attached"] is True
    # No control-plane bridge exists for either terminal in this test, so the
    # server reports them as unmanaged with no browser attached — but it still
    # lists them, because the PTYs are real on the node.
    assert running["managed"] is False
    assert running["browser_attached"] is False
    # Nothing in ActiveTerminalRegistry, so attribution falls back to personal.
    assert running["source"] == "personal"
    assert terminals[1]["current_command"] == ""
    assert terminals[1]["running"] is False


@pytest.mark.asyncio
async def test_list_offline_node_is_503_and_unknown_node_is_404():
    service = _FakeService(_FakeStore())
    async with _client(service) as client:
        # Approved but never connected: no live Connection in the registry.
        offline = await client.get(f"/internal/node-terminals/{NODE}", headers=AUTH)
        assert offline.status_code == 503

        missing = await client.get("/internal/node-terminals/nope", headers=AUTH)
        assert missing.status_code == 404


@pytest.mark.asyncio
async def test_list_requires_bearer_token():
    service = _FakeService(_FakeStore())
    async with _client(service) as client:
        resp = await client.get(f"/internal/node-terminals/{NODE}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_interrupt_sends_frame_to_node():
    service = _FakeService(_FakeStore())
    conn = service.registry.register(NODE, None)

    async with _client(service) as client:
        resp = await client.post(
            f"/internal/node-terminals/{NODE}/t-1/interrupt", headers=AUTH
        )

    assert resp.status_code == 200
    assert resp.json() == {"interrupted": True, "agent_command_interrupted": False}
    frame = await asyncio.wait_for(conn.downstream_get(), timeout=2)
    assert frame.WhichOneof("frame") == "terminal_interrupt"
    assert frame.terminal_interrupt.terminal_id == "t-1"


@pytest.mark.asyncio
async def test_close_unbridged_terminal_sends_terminal_close():
    """A PTY with no server bridge (e.g. it outlived a restart) is still
    closable: the route falls through to a bare terminal_close frame."""
    service = _FakeService(_FakeStore())
    conn = service.registry.register(NODE, None)

    async with _client(service) as client:
        resp = await client.delete(
            f"/internal/node-terminals/{NODE}/t-ghost", headers=AUTH
        )

    assert resp.status_code == 200
    assert resp.json() == {"closed": True}
    frame = await asyncio.wait_for(conn.downstream_get(), timeout=2)
    assert frame.WhichOneof("frame") == "terminal_close"
    assert frame.terminal_close.terminal_id == "t-ghost"


@pytest.mark.asyncio
async def test_list_times_out_when_node_never_answers(monkeypatch):
    """A node that accepts the request but never replies must surface 504
    rather than pinning the request until the dispatch timeout."""
    import node_server.service as service_mod

    monkeypatch.setattr(service_mod, "DISPATCH_ACK_TIMEOUT", 0.05)
    service = _FakeService(_FakeStore())
    service.registry.register(NODE, None)

    async with _client(service) as client:
        resp = await client.get(f"/internal/node-terminals/{NODE}", headers=AUTH)

    assert resp.status_code == 504


@pytest.mark.asyncio
async def test_pending_list_waiter_fails_when_node_disconnects():
    """Connection.close() must fail an in-flight list waiter, otherwise the
    console's request hangs for the full dispatch timeout after a drop."""
    service = _FakeService(_FakeStore())
    conn = service.registry.register(NODE, None)

    async with _client(service) as client:
        task = asyncio.create_task(
            client.get(f"/internal/node-terminals/{NODE}", headers=AUTH)
        )
        # Let the request reach the node, then drop the connection.
        frame = await asyncio.wait_for(conn.downstream_get(), timeout=2)
        assert frame.WhichOneof("frame") == "terminal_list"
        service.registry.disconnect(NODE)
        resp = await asyncio.wait_for(task, timeout=3)

    assert resp.status_code == 503
