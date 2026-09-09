"""InstallHostTool control-plane guard policy + ack/version fold.

Pins the contract the environment-panel「安装 Node.js」and「检测 Xcode」buttons
depend on:

* the guard mirrors manage_editor (exists / not passive / online) and does NOT
  require approval — the approve gate itself blocks on missing Node.js, so the
  install must be reachable from a pending node or the gate deadlocks;
* the frame carries the caller-resolved target (download URL + proxy fields);
* a successful ack folds node_version/npm_version (and xcodebuild_version for
  xcode detection) into capability labels so ListNodes refreshes without a
  re-register — one detect click, label updated, no node restart;
* a failed ack surfaces the node-reported error.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import pytest

from node_server import agentcompose_v2_pb2 as pb
from node_server import crypto
from node_server.registry import Registry
from node_server.service import NodeService
from node_server.store import NodeRecord, NODE_STATUS_PENDING

_MASTER_KEY_HEX = "00" * 32


class _FakeStore:
    """Just enough NodeService.store surface for install_host_tool."""

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


_TARGET = {
    "target_version": "22.17.0",
    "download_url": "https://nodejs.org/dist/v22.17.0/node-v22.17.0-darwin-arm64.tar.gz",
    "sha256": "",
    "proxy_mode": "",
    "proxy_url": "",
    "proxy_url_prefix": "",
}


class _AckPump:
    """Drains the connection's downstream queue and delivers a canned ack.

    install_host_tool awaits conn.await_ack(frame_id), so the frame the service
    enqueues must be consumed and matched back by server_frame_id.
    """

    def __init__(self, conn, registry: Registry) -> None:
        self.conn = conn
        self.registry = registry
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


def _ok_ack(frame, node_version: str = "22.17.0", npm_version: str = "10.9.2", xcodebuild_version: str = ""):
    return pb.NodeCommandAck(
        server_frame_id=frame.server_frame_id,
        ok=True,
        node_version=node_version,
        npm_version=npm_version,
        xcodebuild_version=xcodebuild_version,
    )


@pytest.mark.asyncio
async def test_install_host_tool_pending_node_allowed_and_folds_versions():
    """Pending (unapproved) node installs fine and versions fold into caps."""
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn, registry)
    pump.start(_ok_ack)
    try:
        result = await service.install_host_tool("n1", "nodejs", target=_TARGET)
    finally:
        await pump.stop()

    assert result["tool"] == "nodejs"
    assert result["node_version"] == "22.17.0"
    assert result["npm_version"] == "10.9.2"
    # The frame the node received carries the resolved target.
    frame = pump.frames[0]
    spec = frame.install_host_tool
    assert spec.tool == "nodejs"
    assert spec.download_url == _TARGET["download_url"]
    assert spec.target_version == "22.17.0"
    # Versions folded into the capability labels without a re-register.
    caps = store.record.capabilities
    assert caps.get("node_version") == "22.17.0"
    assert caps.get("npm_version") == "10.9.2"


@pytest.mark.asyncio
async def test_install_host_tool_xcode_detect_needs_no_target():
    """xcode is detection-only: no archive target, empty download_url on the wire."""
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None, peer_address="127.0.0.1:1")
    pump = _AckPump(conn, registry)
    pump.start(lambda frame: _ok_ack(frame, node_version="", npm_version="", xcodebuild_version="16.0"))
    try:
        result = await service.install_host_tool("n1", "xcode", target=None)
    finally:
        await pump.stop()

    assert result["tool"] == "xcode"
    assert result["xcodebuild_version"] == "16.0"
    frame = pump.frames[0]
    spec = frame.install_host_tool
    assert spec.tool == "xcode"
    assert spec.download_url == ""
    assert spec.target_version == ""
    # The probed version folded into the capability label immediately — no
    # node restart needed for the build tab's node filter to see it.
    caps = store.record.capabilities
    assert caps.get("xcodebuild_version") == "16.0"


@pytest.mark.asyncio
async def test_install_host_tool_nodejs_still_requires_target():
    """Regression: the target-less allowance is xcode-only; nodejs still rejects."""
    store = _FakeStore(_record())
    service, registry = _service(store)
    registry.register("n1", caps=None)
    from node_server.service import RPCError

    with pytest.raises(RPCError) as exc_info:
        await service.install_host_tool("n1", "nodejs", target=None)
    assert "download_url" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_install_host_tool_unknown_tool_rejected():
    store = _FakeStore(_record())
    service, registry = _service(store)
    registry.register("n1", caps=None)
    from node_server.service import RPCError

    with pytest.raises(RPCError) as exc_info:
        await service.install_host_tool("n1", "gcc", target=_TARGET)
    assert "unsupported host tool" in str(exc_info.value.message).lower()


@pytest.mark.asyncio
async def test_install_host_tool_offline_node_rejected():
    """The install dispatches over the live stream — offline fails closed."""
    store = _FakeStore(_record())
    service, registry = _service(store)
    # No connection registered.
    from node_server.service import RPCError

    with pytest.raises(RPCError):
        await service.install_host_tool("n1", "nodejs", target=_TARGET)


@pytest.mark.asyncio
async def test_install_host_tool_failed_ack_surfaces_error():
    store = _FakeStore(_record())
    service, registry = _service(store)
    conn = registry.register("n1", caps=None)

    def bad_ack(frame):
        ack = pb.NodeCommandAck(server_frame_id=frame.server_frame_id, ok=False)
        ack.error = "host-tool: download 404"
        return ack

    pump = _AckPump(conn, registry)
    pump.start(bad_ack)
    try:
        from node_server.service import RPCError

        with pytest.raises(RPCError) as exc_info:
            await service.install_host_tool("n1", "nodejs", target=_TARGET)
    finally:
        await pump.stop()
    assert "404" in str(exc_info.value.message)
    # No version fold happened on failure.
    assert "node_version" not in (store.record.capabilities or {})
