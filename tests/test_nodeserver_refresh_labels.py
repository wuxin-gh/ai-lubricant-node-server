"""RefreshLabels control-plane contract + label fold.

Pins what the console「刷新标签」button depends on:

* guard policy: node must exist and be online (a passive grouping container
  cannot answer — but one has no client either, so offline covers it);
* the frame on the wire is the (empty) NodeRefreshLabelsRequest;
* a successful ack with refreshed_capabilities folds the node's freshly probed
  labels into the stored capabilities — merged over the existing labels so
  server bookkeeping (role / hostname / server_seen_address) survives;
* an ack without capabilities, an ok=False ack, and an offline node all
  surface errors instead of silently no-oping.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import pytest

from node_server import agentcompose_v2_pb2 as pb
from node_server import crypto
from node_server.registry import Registry
from node_server.service import NodeService, RPCError
from node_server.store import NodeRecord, NODE_STATUS_PENDING, NODE_STATUS_APPROVED

_MASTER_KEY_HEX = "00" * 32


class _FakeStore:
    """Just enough NodeService.store surface for refresh_node_labels."""

    def __init__(self, record: Optional[NodeRecord] = None) -> None:
        self.record = record
        self.upserts: list[NodeRecord] = []

    async def get_node_if_exists(self, node_id: str) -> Optional[NodeRecord]:
        if self.record is not None and self.record.id == node_id:
            return self.record
        return None

    async def upsert_node(self, item: NodeRecord) -> NodeRecord:
        self.upserts.append(item)
        self.record = item
        return item


def _record(node_id: str = "n1", *, caps: dict | None = None) -> NodeRecord:
    return NodeRecord(
        id=node_id,
        name=node_id,
        status=NODE_STATUS_APPROVED,
        role="execution",
        startup_method="standalone",
        capabilities=dict(caps or {"os": "darwin", "arch": "arm64"}),
    )


def _service(store: _FakeStore) -> tuple[NodeService, Registry]:
    registry = Registry()
    service = NodeService(
        master_key=crypto.parse_master_key(_MASTER_KEY_HEX),
        server_url="http://127.0.0.1:8001",
        store=store,  # type: ignore[arg-type]
        registry=registry,
    )
    return service, registry


class _AckPump:
    """Drains the connection's downstream queue and delivers a canned ack."""

    def __init__(self, conn) -> None:
        self.conn = conn
        self.frames: list[pb.NodeDownstreamFrame] = []
        self.task: Optional[asyncio.Task] = None

    def start(self, ack_for) -> None:
        async def pump():
            while True:
                frame = await self.conn.downstream_get()
                if frame is None:
                    return
                self.frames.append(frame)
                ack = ack_for(frame)
                if ack is not None:
                    self.conn.deliver_ack(ack)

        self.task = asyncio.get_running_loop().create_task(pump())

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass


def _caps_ack(frame, **labels: str) -> pb.NodeCommandAck:
    caps = pb.NodeCapabilities(os="darwin", arch="arm64", docker=False)
    caps.labels.update({"cpu_cores": "8", "client_version": "0.2.0", **labels})
    return pb.NodeCommandAck(
        server_frame_id=frame.server_frame_id,
        ok=True,
        refreshed_capabilities=caps,
    )


@pytest.mark.asyncio
async def test_refresh_labels_folds_snapshot_and_keeps_server_bookkeeping():
    """A successful refresh merges the fresh snapshot over stored labels."""
    store = _FakeStore(
        _record(caps={
            "os": "linux",
            "role": "execution",
            "hostname": "old-host",
            "server_seen_address": "10.0.0.5:44441",
            "node_version": "18.0.0",  # stale: the fresh probe re-reports
        })
    )
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="10.0.0.5:44441")
    pump = _AckPump(conn)
    pump.start(lambda frame: _caps_ack(frame, node_version="22.17.0", editor_version_claude="2.1.0"))
    try:
        result = await service.refresh_node_labels("n1")
    finally:
        await pump.stop()

    # The frame the node received is the empty refresh request.
    frame = pump.frames[0]
    assert frame.WhichOneof("frame") == "refresh_labels"

    caps = store.record.capabilities
    # Fresh probe wins for re-probed keys.
    assert caps.get("os") == "darwin"
    assert caps.get("node_version") == "22.17.0"
    assert caps.get("editor_version_claude") == "2.1.0"
    # Server bookkeeping survives the merge (the node does not report these).
    assert caps.get("role") == "execution"
    assert caps.get("server_seen_address") == "10.0.0.5:44441"
    assert result["labels"] is caps


@pytest.mark.asyncio
async def test_refresh_labels_node_offline_rejected():
    store = _FakeStore(_record())
    service, _ = _service(store)
    # No registry.register → node has no live connection.
    with pytest.raises(RPCError):
        await service.refresh_node_labels("n1")


@pytest.mark.asyncio
async def test_refresh_labels_unknown_node_rejected():
    store = _FakeStore(None)
    service, registry = _service(store)
    registry.register("other", caps=None)
    with pytest.raises(RPCError):
        await service.refresh_node_labels("n1")


@pytest.mark.asyncio
async def test_refresh_labels_ack_without_capabilities_rejected():
    """An ok ack that forgot the snapshot is a protocol violation, not a no-op."""
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None)
    pump = _AckPump(conn)
    pump.start(lambda frame: pb.NodeCommandAck(server_frame_id=frame.server_frame_id, ok=True))
    try:
        with pytest.raises(RPCError):
            await service.refresh_node_labels("n1")
    finally:
        await pump.stop()


@pytest.mark.asyncio
async def test_refresh_labels_failed_ack_surfaces_node_error():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None)
    pump = _AckPump(conn)
    pump.start(lambda frame: pb.NodeCommandAck(
        server_frame_id=frame.server_frame_id, ok=False, error="probe crashed"))
    try:
        with pytest.raises(RPCError) as exc_info:
            await service.refresh_node_labels("n1")
    finally:
        await pump.stop()
    assert "probe crashed" in str(exc_info.value.message)
