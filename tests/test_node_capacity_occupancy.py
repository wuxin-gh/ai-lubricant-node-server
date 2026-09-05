from __future__ import annotations

from types import SimpleNamespace

import pytest

from node_server import service as service_module
from node_server.store import NodeRecord, normalize_node_capacity


def test_normalize_node_capacity_drops_invalid_and_zero_values():
    assert normalize_node_capacity({
        "max_sessions": "3",
        "cpu_total": "4.5",
        "memory_total": str(8 * 1024**3),
        "unknown": 1,
    }) == {
        "max_sessions": 3,
        "cpu_total": 4.5,
        "memory_total": 8 * 1024**3,
    }
    assert normalize_node_capacity({"max_sessions": 0, "cpu_total": -1, "memory_total": "bad"}) == {}


class FakeConnection:
    capabilities = None

    def __init__(self, active: int):
        self._active = [f"s-{i}" for i in range(active)]

    def active_sessions(self):
        return list(self._active)


@pytest.mark.asyncio
async def test_capacity_rejects_max_sessions(monkeypatch):
    monkeypatch.setattr(
        service_module,
        "_node_capability_satisfies_spec",
        lambda _conn, _spec: ("", True),
    )
    svc = object.__new__(service_module.NodeService)
    record = NodeRecord(id="node-1", capacity={"max_sessions": 2})

    reason, ok = await svc._node_satisfies_spec(record, FakeConnection(2), SimpleNamespace())

    assert ok is False
    assert reason == "node session capacity reached (2/2)"


@pytest.mark.asyncio
async def test_capacity_charges_global_cpu_and_memory_defaults(monkeypatch):
    monkeypatch.setattr(
        service_module,
        "_node_capability_satisfies_spec",
        lambda _conn, _spec: ("", True),
    )
    from node_server import config

    monkeypatch.setattr(
        config,
        "settings",
        SimpleNamespace(node_default_session_cpu=1.0, node_default_session_memory=1024),
    )
    svc = object.__new__(service_module.NodeService)
    conn = FakeConnection(1)

    reason, ok = await svc._node_satisfies_spec(
        NodeRecord(id="node-1", capacity={"cpu_total": 1.5}), conn, SimpleNamespace()
    )
    assert (reason, ok) == ("node CPU capacity reached", False)

    reason, ok = await svc._node_satisfies_spec(
        NodeRecord(id="node-1", capacity={"memory_total": 1500}), conn, SimpleNamespace()
    )
    assert (reason, ok) == ("node memory capacity reached", False)

    reason, ok = await svc._node_satisfies_spec(
        NodeRecord(id="node-1", capacity={"cpu_total": 2, "memory_total": 2048}),
        conn,
        SimpleNamespace(),
    )
    assert (reason, ok) == ("", True)
