"""HostToolJob control-plane trio (start / status / cancel) for async Xcode.

Pins the contract the environment-panel「自动安装 Xcode」button depends on:

* start validates the same guard family as install_host_tool (exists / not
  passive / online) plus the darwin gate, sends the caller-resolved target in
  the NodeHostToolJob frame, and returns right after the node's 30s "accepted"
  ack — the install itself runs for hours and streams its own frames;
* a successful NodeHostToolJobResult folds the freshly probed
  xcodebuild_version into capability labels (no re-register needed), the same
  fold the sync InstallHostTool ack performs;
* events update the in-memory snapshot the status endpoint polls;
* cancel sends the NodeHostToolJobCancel frame downstream;
* non-darwin hosts / unknown tools / offline nodes fail closed.
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

_MASTER_KEY_HEX = "00" * 32


class _FakeStore:
    """Just enough NodeService.store surface for start_host_tool_job."""

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


def _record(node_id: str = "n1", *, status: str = NODE_STATUS_PENDING, caps: dict | None = None) -> NodeRecord:
    return NodeRecord(
        id=node_id,
        name=node_id,
        status=status,
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


_JOB = {
    "tool": "xcode",
    "target_version": "16.0",
    "download_url": "https://xcodereleases.com/Xcode_16.0.xip",
    "download_size_bytes": 12_000_000_000,
    "sha256": "",
}


class _AckPump:
    """Drains the connection's downstream queue and delivers a canned ack.

    start_host_tool_job awaits conn.await_ack(frame_id), so the frame the
    service enqueues must be consumed and matched back by server_frame_id.
    """

    def __init__(self, conn) -> None:
        self.conn = conn
        self.frames: list[pb.NodeDownstreamFrame] = []
        self.task: Optional[asyncio.Task] = None

    def start(self) -> None:
        async def pump():
            while True:
                frame = await self.conn.downstream_get()
                if frame is None:
                    return
                self.frames.append(frame)
                if frame.WhichOneof("frame") == "host_tool_job":
                    self.conn.deliver_ack(
                        pb.NodeCommandAck(server_frame_id=frame.server_frame_id, ok=True)
                    )

        self.task = asyncio.get_running_loop().create_task(pump())

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass


@pytest.mark.asyncio
async def test_start_host_tool_job_accepts_and_carries_target():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn)
    pump.start()
    try:
        result = await service.start_host_tool_job("n1", "htj-1", **_JOB)
    finally:
        await pump.stop()

    assert result == {"node_id": "n1", "job_id": "htj-1", "tool": "xcode", "status": "accepted"}

    frame = pump.frames[0]
    spec = frame.host_tool_job
    assert spec.job_id == "htj-1"
    assert spec.tool == "xcode"
    assert spec.target_version == "16.0"
    assert spec.download_url == _JOB["download_url"]
    assert spec.download_size_bytes == _JOB["download_size_bytes"]
    # The snapshot exists before any event arrives (status endpoint returns it).
    snap = conn.get_host_tool_snapshot("htj-1")
    assert snap is not None
    assert snap["status"] == "running"
    assert snap["target_version"] == "16.0"


@pytest.mark.asyncio
async def test_host_tool_job_event_updates_snapshot():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn)
    pump.start()
    try:
        await service.start_host_tool_job("n1", "htj-ev", **_JOB)
    finally:
        await pump.stop()

    # A progress frame from the node routes through handle_upstream and
    # updates the polled snapshot.
    event = pb.NodeHostToolJobEvent(
        job_id="htj-ev", seq=1, stage="downloading", message="fetching",
        percent=10, current_bytes=100, total_bytes=1000,
    )
    await service.handle_upstream("n1", conn, pb.NodeUpstreamFrame(host_tool_job_event=event))

    snap = conn.get_host_tool_snapshot("htj-ev")
    assert snap["stage"] == "downloading"
    assert snap["current_bytes"] == 100
    assert snap["total_bytes"] == 1000
    assert snap["events"][-1]["seq"] == 1


@pytest.mark.asyncio
async def test_host_tool_job_result_folds_xcodebuild_version():
    """A successful result folds the probed version into caps (no re-register)."""
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn)
    pump.start()
    try:
        await service.start_host_tool_job("n1", "htj-ok", **_JOB)
    finally:
        await pump.stop()

    await service.handle_upstream(
        "n1",
        conn,
        pb.NodeUpstreamFrame(
            host_tool_job_result=pb.NodeHostToolJobResult(
                job_id="htj-ok",
                ok=True,
                stage_reached="completed",
                xcodebuild_version="Xcode 16.0\nBuild version 16A242d",
                app_path="/Applications/Xcode-16.0.app",
            )
        ),
    )
    snap = conn.get_host_tool_snapshot("htj-ok")
    assert snap["status"] == "completed"
    assert snap["xcodebuild_version"].startswith("Xcode 16.0")
    assert snap["app_path"] == "/Applications/Xcode-16.0.app"
    # The fold happened on the stored record immediately.
    assert store.record.capabilities.get("xcodebuild_version").startswith("Xcode 16.0")

    # A failed result stores the error but never folds a version.
    await service.handle_upstream(
        "n1",
        conn,
        pb.NodeUpstreamFrame(
            host_tool_job_result=pb.NodeHostToolJobResult(
                job_id="htj-ok", ok=False, error_code="extract_failed",
                error_message="xip signature check failed", stage_reached="extracting",
            )
        ),
    )
    snap = conn.get_host_tool_snapshot("htj-ok")
    assert snap["status"] == "failed"
    assert snap["error_code"] == "extract_failed"


@pytest.mark.asyncio
async def test_cancel_host_tool_job_sends_frame():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn)
    pump.start()
    try:
        result = await service.cancel_host_tool_job("n1", "htj-1")
        # send() only enqueues; give the pump task a turn to consume it.
        await asyncio.sleep(0.05)
    finally:
        await pump.stop()
    assert result["cancelled"] is True
    # No ack is awaited for cancel — it may arrive after the node finished.
    assert pump.frames[-1].host_tool_job_cancel.job_id == "htj-1"


@pytest.mark.asyncio
async def test_start_host_tool_job_offline_rejected():
    store = _FakeStore(_record())
    service, _registry = _service(store)
    from node_server.service import RPCError

    with pytest.raises(RPCError):
        await service.start_host_tool_job("n1", "htj-x", **_JOB)


@pytest.mark.asyncio
async def test_start_host_tool_job_non_darwin_rejected():
    store = _FakeStore(_record(caps={"os": "linux", "arch": "amd64"}))
    service, registry = _service(store)
    registry.register("n1", caps=None)
    from node_server.service import RPCError

    with pytest.raises(RPCError) as exc_info:
        await service.start_host_tool_job("n1", "htj-x", **_JOB)
    assert "macos" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_start_host_tool_job_unknown_tool_rejected():
    store = _FakeStore(_record())
    service, registry = _service(store)
    registry.register("n1", caps=None)
    from node_server.service import RPCError

    job = {k: v for k, v in _JOB.items() if k != "tool"}
    with pytest.raises(RPCError) as exc_info:
        await service.start_host_tool_job("n1", "htj-x", tool="nodejs", **job)
    assert "unsupported" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_get_host_tool_job_status_unknown_job_404():
    store = _FakeStore(_record())
    service, registry = _service(store)
    registry.register("n1", caps=None)
    from node_server.service import RPCError

    with pytest.raises(RPCError):
        await service.get_host_tool_job_status("n1", "htj-missing")
