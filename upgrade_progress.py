"""Node upgrade progress tracker.

Tracks the per-step progress of node upgrades (the JS-runtime hot swap and the
node-binary self-upgrade) so the console can poll live status instead of
staring at a blocking POST with a bare error at the end.

Why a dedicated tracker and not the Connection-bound snapshot pattern (build /
ios / host-tool jobs): the node-binary step ends with the node REPLACING its
own process, which drops the stream — every existing snapshot family lives on
the Connection object and dies with it, exactly when this feature most needs
the data. The tracker therefore hangs off NodeService and is keyed by node_id,
surviving reconnects for the lifetime of the server process (in-memory only,
like every other job snapshot; the durable truth stays in the store —
runtime_version label / reconnecting client_version).

Terminal semantics per step:
- runtime: the node acks only AFTER download+sha256+extract+activate, so the
  ack is authoritative (ok -> completed, error -> failed). A late "done" event
  from a detached goroutine also terminalizes.
- node: the ack means only "accepted" (the node downloads, swaps, then restarts
  and cannot ack post-restart). Terminal = reconnect reporting the new
  client_version (finalize_from_reconnect) or a "failed" event from the node.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from . import crypto

# The node step is "accepted" but not done until the node reconnects with the
# new version; if that never happens the frontend needs a bounded wait. No hard
# server-side timeout on the snapshot itself (the POST's own deadline governs
# the operator-facing flow); this only bounds the events tail.
_EVENTS_TAIL = 20


def _normalize_version(value: Any) -> str:
    """Strip a leading v/whitespace so 'v1.2.3' == '1.2.3' (same normalization
    as node_release_catalog._clean_version)."""
    return str(value or "").strip().lstrip("v")


class UpgradeTracker:
    """In-memory, node_id-keyed upgrade progress snapshots (thread-safe)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # node_id -> {"runtime": snap|None, "node": snap|None}
        self._jobs: dict[str, dict[str, Optional[dict]]] = {}

    def _node_entry(self, node_id: str) -> dict:
        entry = self._jobs.get(node_id)
        if entry is None:
            entry = {"runtime": None, "node": None}
            self._jobs[node_id] = entry
        return entry

    def _step_snapshot(self, node_id: str, kind: str) -> Optional[dict]:
        entry = self._jobs.get(node_id)
        if entry is None:
            return None
        return entry.get(kind)

    @staticmethod
    def _new_snapshot(
        kind: str, target_version: str, server_frame_id: str
    ) -> dict:
        now = crypto.rfc3339nano(crypto.utc_now())
        return {
            "kind": kind,
            "target_version": target_version,
            "server_frame_id": server_frame_id,
            # dispatched: frame sent, node not heard from yet (an old node that
            # never emits events stays here — the ack/reconnect still terminalizes)
            "status": "dispatched",
            "stage": "dispatched",
            "message": "已下发，等待节点领取",
            "percent": 0,
            "current_bytes": 0,
            "total_bytes": 0,
            "error": "",
            "created_at": now,
            "updated_at": now,
            "completed_at": "",
            "events": [],
        }

    # ── lifecycle ────────────────────────────────────────────────────────────
    def init(
        self, node_id: str, kind: str, target_version: str, server_frame_id: str
    ) -> None:
        """Register a step right before the downstream frame is sent, so a fast
        progress event can never race the init (same ordering rule as the
        host-tool/build dispatches)."""
        if kind not in ("runtime", "node"):
            return
        with self._lock:
            entry = self._node_entry(node_id)
            entry[kind] = self._new_snapshot(kind, target_version, server_frame_id)

    def apply(self, node_id: str, event: Any) -> None:
        """Fold one NodeUpgradeEvent into the matching step snapshot. Events for
        unknown nodes/kinds are dropped; a stale server_frame_id (an event left
        over from a previous upgrade to this node) is ignored so an old
        goroutine's tail cannot clobber the current run."""
        kind = str(getattr(event, "kind", "") or "")
        if kind not in ("runtime", "node"):
            return
        stage = str(getattr(event, "stage", "") or "")
        seq = int(getattr(event, "seq", 0) or 0)
        frame_id = str(getattr(event, "server_frame_id", "") or "")
        now = crypto.rfc3339nano(crypto.utc_now())
        with self._lock:
            snap = self._step_snapshot(node_id, kind)
            if snap is None:
                return
            if snap.get("server_frame_id") and frame_id and snap["server_frame_id"] != frame_id:
                return  # stale event from a previous upgrade
            terminal = stage in ("done", "failed")
            if snap.get("status") in ("completed", "failed") and not terminal:
                return  # never un-finish a step
            snap["stage"] = stage
            snap["message"] = str(getattr(event, "message", "") or "")
            snap["percent"] = int(getattr(event, "percent", 0) or 0)
            snap["current_bytes"] = int(getattr(event, "current_bytes", 0) or 0)
            snap["total_bytes"] = int(getattr(event, "total_bytes", 0) or 0)
            snap["updated_at"] = now
            if terminal:
                snap["status"] = "completed" if stage == "done" else "failed"
                snap["completed_at"] = now
            snap["events"].append({"seq": seq, "stage": stage, "message": snap["message"], "timestamp": now})
            del snap["events"][:-_EVENTS_TAIL]

    def finalize_from_ack(self, node_id: str, kind: str, ok: bool, error: str = "") -> None:
        """The runtime step's ack is authoritative (sent after activation);
        the node step's ack only means "accepted" — record it as a progress
        message, never as a terminal state."""
        with self._lock:
            snap = self._step_snapshot(node_id, kind)
            if snap is None or snap.get("status") in ("completed", "failed"):
                return
            now = crypto.rfc3339nano(crypto.utc_now())
            snap["updated_at"] = now
            if ok:
                if kind == "runtime":
                    snap["status"] = "completed"
                    snap["stage"] = "done"
                    snap["percent"] = 100
                    snap["message"] = "Runtime 已切换"
                    snap["completed_at"] = now
                else:
                    snap["stage"] = "downloading"
                    snap["message"] = "已受理，等待节点下载并重启"
            else:
                snap["status"] = "failed"
                snap["error"] = error or "node rejected the upgrade"
                snap["message"] = snap["error"]
                snap["completed_at"] = now

    def note_ack_timeout(self, node_id: str, kind: str, message: str) -> None:
        """The ack window elapsed. NOT terminal: the node-side goroutine runs
        detached from the stream, so events may still arrive and terminalize the
        snapshot later (a reconnect must not abort a mid-download upgrade)."""
        with self._lock:
            snap = self._step_snapshot(node_id, kind)
            if snap is None or snap.get("status") in ("completed", "failed"):
                return
            snap["message"] = message
            snap["updated_at"] = crypto.rfc3339nano(crypto.utc_now())

    def mark_restarting(self, node_id: str) -> None:
        """The node's connection dropped while the node step is in flight —
        that is the expected shape of a binary swap restarting. Display glue
        only (the terminal transition is the reconnect), so never overwrite a
        terminal state."""
        with self._lock:
            snap = self._step_snapshot(node_id, "node")
            if snap is None or snap.get("status") in ("completed", "failed"):
                return
            snap["status"] = "restarting"
            snap["stage"] = "restarting"
            snap["message"] = "节点程序替换中，连接已断开，等待重连上报新版本"
            snap["updated_at"] = crypto.rfc3339nano(crypto.utc_now())

    def finalize_from_reconnect(self, node_id: str, client_version: str) -> None:
        """Called from the register path with the freshly reported
        client_version. Completes the node step when it matches the target —
        this is the ONLY terminal path for a successful node-binary upgrade,
        because the node cannot ack after replacing its own process."""
        version = _normalize_version(client_version)
        if not version:
            return
        with self._lock:
            snap = self._step_snapshot(node_id, "node")
            if snap is None or snap.get("status") in ("completed", "failed"):
                return
            if version != _normalize_version(snap.get("target_version")):
                return  # not the version this upgrade pushed (e.g. a blip reconnect)
            now = crypto.rfc3339nano(crypto.utc_now())
            snap["status"] = "completed"
            snap["stage"] = "done"
            snap["percent"] = 100
            snap["message"] = f"节点程序已更新到 v{version}"
            snap["updated_at"] = now
            snap["completed_at"] = now
            snap["events"].append({"seq": -1, "stage": "done", "message": snap["message"], "timestamp": now})
            del snap["events"][:-_EVENTS_TAIL]

    def get(self, node_id: str) -> Optional[dict]:
        """Polling read. None = this node has never run an upgrade (the caller
        maps that to NOT_FOUND; deliberately NO online check — the restart
        window is exactly when the node is offline)."""
        with self._lock:
            entry = self._jobs.get(node_id)
            if entry is None:
                return None
            return {
                "runtime": dict(entry["runtime"]) if entry.get("runtime") else None,
                "node": dict(entry["node"]) if entry.get("node") else None,
            }
