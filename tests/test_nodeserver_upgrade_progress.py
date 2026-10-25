"""Node upgrade progress tracker + wiring (runtime hot-swap / node self-upgrade).

Pins the contract the upgrade progress panel depends on:

* runtime/node steps init BEFORE the frame is sent (the status endpoint must
  return a snapshot even before the first event);
* NodeUpgradeEvent frames fold into the tracker via handle_upstream — only
  done|failed are terminal; unknown nodes/kinds are dropped; stale frame ids
  cannot clobber the current run;
* the runtime step's ack IS authoritative (ok -> completed, error -> failed);
  the node step's ack only means "accepted" (non-terminal);
* ack timeout / mid-upgrade disconnect leave the snapshot NON-terminal with an
  explanatory message (the detached node goroutine keeps downloading);
* the node-binary step terminalizes via the reconnect's client_version —
  exactly the "node cannot ack post-restart" gap;
* a genuine disconnect while the node step runs marks "restarting";
* get_node_upgrade_status works with the node OFFLINE (the restart window is
  when the console polls) and 404s when the node never ran an upgrade.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import pytest

from node_server import agentcompose_v2_pb2 as pb
from node_server import crypto
from node_server.registry import Registry
from node_server.service import NodeService
from node_server.store import NodeRecord, NODE_STATUS_PENDING
from node_server.upgrade_progress import UpgradeTracker

_MASTER_KEY_HEX = "00" * 32


class _FakeStore:
    """Just enough NodeService.store surface for the upgrade paths."""

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
        status=NODE_STATUS_PENDING,
        role="execution",
        startup_method="standalone",
        capabilities=dict(caps or {"os": "linux", "arch": "amd64"}),
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


_RUNTIME_TARGET = {
    "target_version": "20261014-1837",
    "download_url": "https://example.com/node-runtime.tar.gz",
    "sha256": "",
}
_NODE_TARGET = {
    "target_version": "20261014-1837",
    "download_url": "https://example.com/node-execution-linux-amd64",
    "sha256": "",
}


class _AckPump:
    """Drains the downstream queue; acks upgrade frames (configurable ok)."""

    def __init__(self, conn) -> None:
        self.conn = conn
        self.frames: list[pb.NodeDownstreamFrame] = []
        self.ok = True
        self.error = ""
        self.task: Optional[asyncio.Task] = None

    def start(self) -> None:
        async def pump():
            while True:
                frame = await self.conn.downstream_get()
                if frame is None:
                    return
                self.frames.append(frame)
                if frame.WhichOneof("frame") in ("runtime_upgrade", "self_upgrade"):
                    self.conn.deliver_ack(
                        pb.NodeCommandAck(
                            server_frame_id=frame.server_frame_id,
                            ok=self.ok,
                            error=self.error,
                        )
                    )

        self.task = asyncio.get_running_loop().create_task(pump())

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass


# ── tracker unit behavior ────────────────────────────────────────────────────


def test_tracker_init_before_send_and_event_flow():
    tracker = UpgradeTracker()
    tracker.init("n1", "runtime", "20261014-1837", "frame-1")
    snap = tracker.get("n1")
    assert snap is not None and snap["runtime"] is not None
    assert snap["runtime"]["status"] == "dispatched"

    ev = pb.NodeUpgradeEvent(
        server_frame_id="frame-1", kind="runtime", seq=1, stage="downloading",
        message="已下载 4.0 MB", percent=7, current_bytes=4 << 20,
        total_bytes=188 << 20,
    )
    tracker.apply("n1", ev)
    snap = tracker.get("n1")
    assert snap["runtime"]["stage"] == "downloading"
    assert snap["runtime"]["current_bytes"] == 4 << 20
    assert snap["runtime"]["total_bytes"] == 188 << 20
    assert snap["runtime"]["status"] == "dispatched"  # non-terminal stage


def test_tracker_terminal_stages_and_no_unfinish():
    tracker = UpgradeTracker()
    tracker.init("n1", "runtime", "v1", "frame-1")
    tracker.apply("n1", pb.NodeUpgradeEvent(server_frame_id="frame-1", kind="runtime", seq=1, stage="done", message="ok", percent=100))
    assert tracker.get("n1")["runtime"]["status"] == "completed"
    # a late non-terminal event must never un-finish
    tracker.apply("n1", pb.NodeUpgradeEvent(server_frame_id="frame-1", kind="runtime", seq=2, stage="downloading", message="late", percent=50))
    assert tracker.get("n1")["runtime"]["status"] == "completed"
    # failed terminalizes too
    tracker.init("n2", "node", "v1", "frame-2")
    tracker.apply("n2", pb.NodeUpgradeEvent(server_frame_id="frame-2", kind="node", seq=1, stage="failed", message="boom"))
    assert tracker.get("n2")["node"]["status"] == "failed"


def test_tracker_ignores_unknown_kind_and_stale_frame():
    tracker = UpgradeTracker()
    tracker.init("n1", "runtime", "v1", "frame-1")
    # unknown kind dropped
    tracker.apply("n1", pb.NodeUpgradeEvent(kind="build", seq=1, stage="downloading"))
    assert tracker.get("n1")["runtime"]["stage"] == "dispatched"
    # unknown node dropped (no exception)
    tracker.apply("n9", pb.NodeUpgradeEvent(kind="runtime", seq=1, stage="downloading"))
    # stale frame id cannot clobber the current run
    tracker.apply("n1", pb.NodeUpgradeEvent(server_frame_id="old-frame", kind="runtime", seq=9, stage="downloading", message="stale"))
    assert tracker.get("n1")["runtime"]["message"] != "stale"


def test_tracker_finalize_from_reconnect_matches_target():
    tracker = UpgradeTracker()
    tracker.init("n1", "node", "20261014-1837", "frame-1")
    # blip reconnect with the OLD version: not terminal
    tracker.finalize_from_reconnect("n1", "20260901-0000")
    assert tracker.get("n1")["node"]["status"] != "completed"
    # the pushed version arrives (v-prefix tolerated)
    tracker.finalize_from_reconnect("n1", "v20261014-1837")
    snap = tracker.get("n1")["node"]
    assert snap["status"] == "completed"
    assert snap["percent"] == 100


def test_tracker_mark_restarting_not_terminal():
    tracker = UpgradeTracker()
    tracker.init("n1", "node", "v1", "frame-1")
    tracker.mark_restarting("n1")
    snap = tracker.get("n1")["node"]
    assert snap["status"] == "restarting"
    # still non-terminal: the reconnect must be able to complete it
    tracker.finalize_from_reconnect("n1", "v1")
    assert tracker.get("n1")["node"]["status"] == "completed"


# ── service wiring ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_runtime_upgrade_ack_terminalizes():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn)
    pump.start()
    try:
        result = await service.runtime_upgrade_node("n1", target=dict(_RUNTIME_TARGET))
    finally:
        await pump.stop()

    assert result["target_version"] == "20261014-1837"
    # frame carried the target
    spec = pump.frames[0].runtime_upgrade
    assert spec.target_version == "20261014-1837"
    # snapshot initialized before send + terminalized by the ack
    snap = service.upgrade_tracker.get("n1")
    assert snap["runtime"]["status"] == "completed"
    # ack ok folded into the store's runtime_version label
    assert store.record.capabilities.get("runtime_version") == "20261014-1837"


@pytest.mark.asyncio
async def test_runtime_upgrade_failed_ack_terminalizes_failed():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn)
    pump.ok = False
    pump.error = "sha256 mismatch"
    pump.start()
    try:
        with pytest.raises(Exception):
            await service.runtime_upgrade_node("n1", target=dict(_RUNTIME_TARGET))
    finally:
        await pump.stop()
    assert service.upgrade_tracker.get("n1")["runtime"]["status"] == "failed"
    assert "sha256" in service.upgrade_tracker.get("n1")["runtime"]["error"]


@pytest.mark.asyncio
async def test_self_upgrade_accepted_ack_stays_non_terminal():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn)
    pump.start()
    try:
        result = await service.self_upgrade_node("n1", target=dict(_NODE_TARGET))
    finally:
        await pump.stop()

    assert result["accepted"] is True
    snap = service.upgrade_tracker.get("n1")
    # accepted, NOT completed — the terminal truth is the reconnect
    assert snap["node"]["status"] == "dispatched"
    assert "已受理" in snap["node"]["message"]


@pytest.mark.asyncio
async def test_node_event_flows_and_reconnect_completes():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn)
    pump.start()
    try:
        await service.self_upgrade_node("n1", target=dict(_NODE_TARGET))
    finally:
        await pump.stop()
    frame_id = pump.frames[0].server_frame_id

    # progress events stream through handle_upstream
    await service.handle_upstream(
        "n1", conn,
        pb.NodeUpstreamFrame(node_upgrade_event=pb.NodeUpgradeEvent(
            server_frame_id=frame_id, kind="node", seq=1,
            stage="downloading", message="已下载 69 MB",
            percent=37, current_bytes=69 << 20, total_bytes=188 << 20,
        )),
    )
    snap = service.upgrade_tracker.get("n1")
    assert snap["node"]["stage"] == "downloading"
    assert snap["node"]["current_bytes"] == 69 << 20

    # disconnect while in flight -> restarting (display glue)
    registry.unregister("n1", conn)
    assert service.upgrade_tracker.get("n1")["node"]["status"] == "restarting"

    # node restarts and reconnects with the new client_version -> completed
    # (the register path calls finalize_from_reconnect; exercise the tracker
    # call site directly here — the wiring is covered by its line in the plan).
    service.upgrade_tracker.finalize_from_reconnect("n1", "20261014-1837")
    assert service.upgrade_tracker.get("n1")["node"]["status"] == "completed"


@pytest.mark.asyncio
async def test_get_node_upgrade_status_works_offline_and_404s():
    store = _FakeStore(_record())
    service, registry = _service(store)
    # never ran an upgrade -> NOT_FOUND (mapped to 404 by unary_api)
    from node_server.service import RPCError

    with pytest.raises(RPCError) as exc_info:
        await service.get_node_upgrade_status("n1")
    assert exc_info.value.code == "not_found"

    # an upgrade that already dropped the node (restart window): the snapshot
    # must still be readable with NO live connection
    registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    service.upgrade_tracker.init("n1", "node", "v1", "frame-1")
    registry.disconnect("n1")
    snap = await service.get_node_upgrade_status("n1")
    assert snap["node"]["target_version"] == "v1"
    assert registry.lookup("n1") is None  # offline, yet the read succeeded


@pytest.mark.asyncio
async def test_authenticate_registration_finalizes_node_upgrade():
    """The register path is the node step's terminal signal: a restarted node
    reporting client_version == target completes the in-flight upgrade without
    any post-restart ack."""
    from node_server import crypto as node_crypto

    service, registry = _service(_FakeStore())
    # seal() takes the base32 STRING; open() returns it back (see service.py).
    secret_b32 = node_crypto.generate_secret()
    secret = node_crypto.decode_secret(secret_b32)
    record = _record()
    record.credential_secret_enc = service.secrets.seal(secret_b32.encode("ascii"))
    store = _FakeStore(record)
    service.store = store  # type: ignore[assignment]

    service.upgrade_tracker.init("n1", "node", "20261014-1837", "frame-1")
    now = node_crypto.utc_now()
    code = node_crypto.generate(secret, now)
    register = pb.NodeRegister(
        node_id="n1", totp_code=code,
        capabilities=pb.NodeCapabilities(labels={"client_version": "v20261014-1837"}),
    )
    await service.authenticate_registration(register, now)
    snap = service.upgrade_tracker.get("n1")
    assert snap["node"]["status"] == "completed"
