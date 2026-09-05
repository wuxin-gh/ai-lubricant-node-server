"""In-memory registry of currently connected execution nodes.

This is the live counterpart to the durable node ledger in :mod:`store`: the
ledger records which nodes exist and their approval status, while this registry
tracks which nodes are connected *right now* and owns the downstream queue used
to reverse-dispatch session commands over each node's long-lived ``NodeConnect``
stream.

Ported from the Go ``pkg/nodes/registry.go``. The Go implementation uses
channels + mutexes; here we use asyncio primitives (``asyncio.Queue`` for the
downstream + tunnel channels, ``asyncio.Future`` for one-shot ack waiters). The
registry is transport-agnostic: it deals in downstream frames and node
identities, not in the ASGI stream. The ``connect_stream`` handler owns the
stream and pumps frames between it and the registry.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable, Optional

from . import agentcompose_v2_pb2 as pb

# How many bytes of a session's most recent stderr the connection retains so a
# terminal failure can be explained after the fact.
#
# Why this exists: session output used to be fanned out ONLY to a live
# FollowNodeSession subscriber. With no browser attached, the provider's own
# stderr — the single most useful artifact when a session dies (e.g. a Node.js
# ERR_MODULE_NOT_FOUND stack naming the missing package) — was dropped on the
# floor, leaving nothing but "exit_code=1" to debug from. Keeping a small tail
# per session means the reason is available at result time regardless of who is
# watching. Bounded and dropped as soon as the session ends, so a chatty session
# cannot grow memory: worst case is this many bytes per live session. 16 KiB
# comfortably holds a Node.js stack trace, which is the common failure shape.
STDERR_TAIL_BYTES = 16 * 1024

# Bounds how many pending server→node frames a connection can hold before sends
# start failing. Session commands are small and infrequent, so a modest buffer
# absorbs bursts without letting a stuck node grow memory unboundedly.
DOWNSTREAM_BUFFER = 64

# Bounds how many pending response chunks a single reverse-proxy tunnel can hold
# before the node's upstream loop starts dropping them (treated as a failed
# proxy by the handler). Shared by the reverse-proxy tunnel (session-local
# service) and the forward HTTP proxy (node mode): both stream an HTTP response
# back as NodeTunnelResponse frames correlated by tunnel_id.
TUNNEL_RESPONSE_BUFFER = 64

# Bounds pending PTY output frames per browser terminal. The node sends chunks
# up to 32 KiB; 128 frames leaves several MiB of burst headroom without letting
# a stalled websocket grow memory without bound.
TERMINAL_OUTPUT_BUFFER = 128


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# An OutputSink receives session output/result/structured frames a node streams
# up. FollowNodeSession registers a sink so streamed output lands where the
# server forwards it. In Python we model the sink as three callables rather than
# an interface; ``None`` callbacks are tolerated.
class OutputSink:
    def __init__(
        self,
        on_output: Optional[Callable[["pb.NodeSessionOutput"], None]] = None,
        on_result: Optional[Callable[["pb.NodeSessionResult"], None]] = None,
        on_structured: Optional[Callable[["pb.NodeSessionEventStructured"], None]] = None,
    ) -> None:
        self.on_output = on_output
        self.on_result = on_result
        self.on_structured = on_structured


class Connection:
    """One live node connection.

    The handler task that owns the stream reads :meth:`downstream_get` and writes
    frames to the node; other tasks (e.g. dispatch placing a session) call
    :meth:`send` to enqueue a command.
    """

    def __init__(
        self,
        node_id: str,
        caps: Optional["pb.NodeCapabilities"],
        peer_address: str = "",
    ) -> None:
        self.node_id = node_id
        self.capabilities = caps
        # The node's address as seen by the server on THIS live TCP connection
        # (proxy-aware; see connect_stream._peer_address). Held on the live
        # connection so node_info can surface it without depending on the value
        # persisted to labels at register time — a node connected before that
        # persistence existed still shows its address immediately.
        self.peer_address = peer_address
        self._downstream: asyncio.Queue = asyncio.Queue(maxsize=DOWNSTREAM_BUFFER)
        self.connected_at = _utcnow()

        self._closed = False
        self._last_heartbeat_at: Optional[datetime] = None
        self._active_session_ids: list[str] = []
        self._active_terminal_ids: list[str] = []
        self._active_tool_runs: list[dict] = []
        self._last_error_code = ""
        self._last_error_message = ""

        # session_id -> OutputSink
        self._sinks: dict[str, OutputSink] = {}
        # session_id -> most recent stderr bytes (bounded, see STDERR_TAIL_BYTES).
        # Independent of _sinks: retained whether or not anyone is following, so
        # a session that dies with no subscriber still has a debuggable reason.
        self._stderr_tails: dict[str, bytearray] = {}
        # server_frame_id -> Future[NodeCommandAck]
        self._acks: dict[str, asyncio.Future] = {}
        # request_id -> Future[NodeHostExecResult]
        self._host_execs: dict[str, asyncio.Future] = {}
        # upload_id -> Future[NodeFileUploadResult]. One waiter per in-flight
        # chunk: the uploader awaits each chunk's ack before sending the next, so
        # a single upload never has two outstanding futures under the same id.
        self._file_uploads: dict[str, asyncio.Future] = {}
        # tunnel_id -> asyncio.Queue[NodeTunnelResponse]. Shared by the
        # reverse-proxy tunnel (session-local service) and the forward HTTP
        # proxy (node mode); both deliver the node's streamed HTTP response
        # here, correlated by tunnel_id.
        self._tunnels: dict[str, asyncio.Queue] = {}
        # terminal_id -> asyncio.Queue[NodeTerminalOutput|NodeTerminalExit|None].
        # Host-shell terminal output/exit frames the node streams up, correlated
        # by terminal_id; the websocket bridge consumes them. A None sentinel is
        # enqueued on close() to wake a blocked consumer.
        self._terminals: dict[str, asyncio.Queue] = {}
        # request_id -> Future[NodeTerminalListResult]. The management console
        # asks for the node's open host terminals; the node's reply is correlated
        # by request_id and delivered here.
        self._terminal_lists: dict[str, asyncio.Future] = {}
        # run_id -> asyncio.Queue[NodeToolRunEvent|None]. Long-running external
        # tool runs (tunnel manager: frpc/cloudflared/npc) stream stdout/stderr
        # chunks + a final exited event, correlated by run_id. A None sentinel
        # is enqueued on close() to wake a blocked consumer.
        self._tool_runs: dict[str, asyncio.Queue] = {}
        # ─── iOS host management (role ios_host) ───────────────────────────────
        # The host's latest full device inventory. Always a complete snapshot the
        # node sends unsolicited on register / attach-detach / claim / WDA state
        # change, so the data side reads it via a unary getter without polling the
        # host. Lost on reconnect, but a freshly-registered host reports again.
        self._ios_inventory: Optional["pb.NodeIosDevicesReport"] = None
        # job_id -> asyncio.Queue[NodeIosJobEvent|None]. WDA job progress frames
        # the host streams up, correlated by job_id. A None sentinel is enqueued
        # on close() to wake a blocked consumer. Used by Stage 3's job follower.
        self._ios_jobs: dict[str, asyncio.Queue] = {}
        # job_id -> Future[NodeIosJobResult]. The terminal outcome of a WDA job,
        # sent exactly once. A server-side dispatch awaits this so a pending job
        # future never hangs on the ack timeout alone.
        self._ios_job_results: dict[str, asyncio.Future] = {}
        # job_id -> dict[str, Any]. In-memory job snapshots for polling queries.
        # Each entry: {job_id, device_id, udid, action, status, stage, percent,
        # message, retryable, error_code, created_at, updated_at, completed_at,
        # events: [{seq, stage, message, timestamp}]}.
        self._ios_job_snapshots: dict[str, dict] = {}
        # ── generic node builds (project-page「构建」tab) ────────────────────
        # build_id -> asyncio.Queue[NodeBuildEvent|None]. Mirrors _ios_jobs.
        self._build_jobs: dict[str, asyncio.Queue] = {}
        # build_id -> Future[NodeBuildResult]. Mirrors _ios_job_results.
        self._build_results: dict[str, asyncio.Future] = {}
        # build_id -> dict[str, Any]. In-memory build snapshots for polling:
        # {build_id, recipe_kind, node_id, status, stage, percent, message,
        # retryable, error_code, artifact_sha256, artifact_size_bytes,
        # created_at, updated_at, completed_at, events: [...]}.
        self._build_snapshots: dict[str, dict] = {}

    # ── downstream channel ────────────────────────────────────────────────
    async def downstream_get(self) -> Optional["pb.NodeDownstreamFrame"]:
        """Await the next downstream frame. Returns ``None`` when the connection
        is closed (the sentinel enqueued by :meth:`close`)."""
        return await self._downstream.get()

    def send(self, frame: "pb.NodeDownstreamFrame") -> None:
        """Enqueue a downstream frame for delivery to the node.

        Fails fast (raises) if the connection is closed or the buffer is full
        rather than blocking the caller (a dispatch/API handler).
        """
        if self._closed:
            raise ConnectionError(f"node {self.node_id} connection is closed")
        try:
            self._downstream.put_nowait(frame)
        except asyncio.QueueFull:
            raise ConnectionError(f"node {self.node_id} downstream buffer is full")

    # ── liveness ──────────────────────────────────────────────────────────
    def note_heartbeat(self, active_session_ids: Optional[list[str]]) -> None:
        self._last_heartbeat_at = _utcnow()
        self._active_session_ids = list(active_session_ids or [])

    def note_active_terminal_ids(self, terminal_ids: list[str]) -> None:
        """Record the host terminals the node reports as still alive.

        A host PTY outlives the control stream, so after a reconnect (or a server
        restart) this is how the server learns which terminals it can reattach to
        instead of assuming they died with the old connection.
        """
        self._active_terminal_ids = list(terminal_ids or [])

    def active_terminal_ids(self) -> list[str]:
        return list(self._active_terminal_ids)

    def note_active_tool_runs(self, runs) -> None:
        self._active_tool_runs = [
            {
                "run_id": str(run.run_id or ""),
                "revision": int(run.revision or 0),
                "pid": int(run.pid or 0),
            }
            for run in (runs or [])
            if str(run.run_id or "")
        ]

    def active_tool_runs(self) -> list[dict]:
        return [dict(item) for item in self._active_tool_runs]

    def note_error(self, code: str, message: str) -> None:
        self._last_error_code = code
        self._last_error_message = message

    def active_sessions(self) -> list[str]:
        return list(self._active_session_ids)

    def snapshot(self) -> tuple[datetime, Optional[datetime], list[str]]:
        return self.connected_at, self._last_heartbeat_at, list(self._active_session_ids)

    # ── output sinks (FollowNodeSession) ──────────────────────────────────
    def bind_sink(self, session_id: str, sink: OutputSink) -> None:
        self._sinks[session_id] = sink

    def unbind_sink(self, session_id: str) -> None:
        self._sinks.pop(session_id, None)

    def deliver_output(self, out: Optional["pb.NodeSessionOutput"]) -> None:
        if out is None:
            return
        # Retain a bounded stderr tail regardless of subscribers. The fan-out
        # below is best-effort by design (no follower → dropped), but the
        # *reason* a session failed must survive: a runtime that dies on start
        # prints its stack to stderr and exits before any UI attaches, which is
        # precisely the case that used to leave "exit code 1" with no cause.
        if out.stream == pb.StdioStream.STDIO_STREAM_STDERR and out.data:
            self.note_stderr(out.session_id, out.data)
        sink = self._sinks.get(out.session_id)
        if sink is not None and sink.on_output is not None:
            sink.on_output(out)

    def note_stderr(self, session_id: str, data: bytes) -> None:
        """Append to a session's stderr tail, keeping only the last N bytes.

        The tail (not the head) is kept: a crash message is the last thing
        written before exit, and an unbounded buffer would let a chatty session
        grow memory for the lifetime of the connection.
        """
        if not session_id or not data:
            return
        tail = self._stderr_tails.get(session_id)
        if tail is None:
            tail = bytearray()
            self._stderr_tails[session_id] = tail
        tail.extend(data)
        if len(tail) > STDERR_TAIL_BYTES:
            del tail[: len(tail) - STDERR_TAIL_BYTES]

    def stderr_tail(self, session_id: str) -> str:
        """Decoded stderr tail for a session; empty when nothing was captured."""
        tail = self._stderr_tails.get(session_id)
        if not tail:
            return ""
        return bytes(tail).decode("utf-8", "replace")

    def forget_stderr(self, session_id: str) -> None:
        """Drop a finished session's retained stderr (called after finalize)."""
        self._stderr_tails.pop(session_id, None)

    def deliver_result(self, res: Optional["pb.NodeSessionResult"]) -> None:
        if res is None:
            return
        sink = self._sinks.get(res.session_id)
        if sink is not None and sink.on_result is not None:
            sink.on_result(res)

    def deliver_structured(self, evt: Optional["pb.NodeSessionEventStructured"]) -> None:
        if evt is None:
            return
        sink = self._sinks.get(evt.session_id)
        if sink is not None and sink.on_structured is not None:
            sink.on_structured(evt)

    # ── ack waiters (send-with-ack) ───────────────────────────────────────
    def await_ack(self, server_frame_id: str) -> asyncio.Future:
        """Register a one-shot waiter for a downstream command's ack, correlated
        by the ``server_frame_id`` the node echoes back. The caller sends the
        command with the same frame id, then awaits the returned Future."""
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._acks[server_frame_id] = fut
        return fut

    def cancel_ack(self, server_frame_id: str) -> None:
        self._acks.pop(server_frame_id, None)

    def deliver_ack(self, ack: Optional["pb.NodeCommandAck"]) -> None:
        if ack is None:
            return
        fut = self._acks.pop(ack.server_frame_id, None)
        if fut is not None and not fut.done():
            fut.set_result(ack)

    # ── one-shot host command results ─────────────────────────────────────
    def await_host_exec(self, request_id: str) -> asyncio.Future:
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._host_execs[request_id] = fut
        return fut

    def cancel_host_exec(self, request_id: str) -> None:
        self._host_execs.pop(request_id, None)

    def deliver_host_exec(self, result: Optional["pb.NodeHostExecResult"]) -> None:
        if result is None:
            return
        fut = self._host_execs.pop(result.request_id, None)
        if fut is not None and not fut.done():
            fut.set_result(result)

    # ── chunked host file uploads ─────────────────────────────────────────
    def await_file_upload(self, upload_id: str) -> asyncio.Future:
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._file_uploads[upload_id] = fut
        return fut

    def cancel_file_upload(self, upload_id: str) -> None:
        self._file_uploads.pop(upload_id, None)

    def deliver_file_upload(self, result: Optional["pb.NodeFileUploadResult"]) -> None:
        if result is None:
            return
        fut = self._file_uploads.pop(result.upload_id, None)
        if fut is not None and not fut.done():
            fut.set_result(result)

    # ── reverse-proxy tunnels ─────────────────────────────────────────────
    def open_tunnel(self, tunnel_id: str) -> asyncio.Queue:
        ch: asyncio.Queue = asyncio.Queue(maxsize=TUNNEL_RESPONSE_BUFFER)
        self._tunnels[tunnel_id] = ch
        return ch

    def close_tunnel(self, tunnel_id: str) -> None:
        self._tunnels.pop(tunnel_id, None)

    def deliver_tunnel_response(self, resp: Optional["pb.NodeTunnelResponse"]) -> None:
        if resp is None:
            return
        ch = self._tunnels.get(resp.tunnel_id)
        if ch is None:
            return
        try:
            ch.put_nowait(resp)
        except asyncio.QueueFull:
            # Drop the chunk rather than blocking the node's upstream loop; the
            # handler treats a stalled tunnel as a failed proxy.
            pass

    # ── host-shell terminals ──────────────────────────────────────────────
    def open_terminal(self, terminal_id: str) -> asyncio.Queue:
        """Register a queue for one host terminal's upstream frames.

        Mirrors :meth:`open_tunnel`: the websocket bridge opens the queue before
        sending ``terminal_open`` so no output frame can be missed.
        """
        ch: asyncio.Queue = asyncio.Queue(maxsize=TERMINAL_OUTPUT_BUFFER)
        self._terminals[terminal_id] = ch
        return ch

    def close_terminal(self, terminal_id: str) -> None:
        self._terminals.pop(terminal_id, None)

    def deliver_terminal_frame(self, terminal_id: str, frame) -> None:
        """Hand one terminal output/exit frame to its consumer.

        A full queue means the browser is not draining output (a stalled
        websocket). Dropping the chunk is the right trade-off here: blocking
        would stall the node's whole upstream loop, and a terminal that has
        fallen behind is already showing stale output.
        """
        if not terminal_id:
            return
        ch = self._terminals.get(terminal_id)
        if ch is None:
            return
        try:
            ch.put_nowait(frame)
        except asyncio.QueueFull:
            pass

    # ── terminal-list queries (management console) ─────────────────────────
    def await_terminal_list(self, request_id: str) -> asyncio.Future:
        """Register a one-shot waiter for a NodeTerminalListResult."""
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._terminal_lists[request_id] = fut
        return fut

    def cancel_terminal_list(self, request_id: str) -> None:
        self._terminal_lists.pop(request_id, None)

    def deliver_terminal_list(self, result: Optional["pb.NodeTerminalListResult"]) -> None:
        if result is None:
            return
        fut = self._terminal_lists.pop(result.request_id, None)
        if fut is not None and not fut.done():
            fut.set_result(result)

    # ── long-running external tool runs (tunnel manager) ──────────────────
    def open_tool_run(self, run_id: str) -> asyncio.Queue:
        """Register a queue for one tool run's upstream events.

        Mirrors :meth:`open_terminal`: the dispatcher opens the queue before
        sending ``tool_run_request`` so no stdout chunk can be missed.
        """
        ch: asyncio.Queue = asyncio.Queue(maxsize=TERMINAL_OUTPUT_BUFFER)
        self._tool_runs[run_id] = ch
        return ch

    def close_tool_run(self, run_id: str) -> None:
        self._tool_runs.pop(run_id, None)

    def deliver_tool_run_event(self, event: Optional["pb.NodeToolRunEvent"]) -> None:
        """Hand one tool-run event to its consumer. A None sentinel ends it."""
        if event is None:
            return
        ch = self._tool_runs.get(event.run_id)
        if ch is None:
            return
        try:
            ch.put_nowait(event)
        except asyncio.QueueFull:
            # Drop rather than stall the node's upstream loop; a busy daemon's
            # bursty output is acceptable to lose a chunk of.
            pass

    # ── iOS host management (role ios_host) ───────────────────────────────
    def note_ios_inventory(self, report: "pb.NodeIosDevicesReport") -> None:
        """Record the host's latest full device inventory snapshot.

        The host sends this unsolicited on register / attach-detach / claim /
        WDA state change. Always a complete snapshot, so no incremental merge.
        """
        self._ios_inventory = report

    def ios_inventory(self) -> Optional["pb.NodeIosDevicesReport"]:
        """Return the cached iOS device inventory, if any."""
        return self._ios_inventory

    def open_ios_job(self, job_id: str) -> asyncio.Queue:
        """Register a queue for one WDA job's progress events.

        Mirrors :meth:`open_tool_run`: the dispatcher opens the queue before
        sending ``NodeIosWdaJobRequest`` so no progress frame can be missed.
        """
        ch: asyncio.Queue = asyncio.Queue(maxsize=TERMINAL_OUTPUT_BUFFER)
        self._ios_jobs[job_id] = ch
        return ch

    def close_ios_job(self, job_id: str) -> None:
        self._ios_jobs.pop(job_id, None)

    def deliver_ios_job_event(self, event: Optional["pb.NodeIosJobEvent"]) -> None:
        """Hand one WDA job event to its consumer. A None sentinel ends it."""
        if event is None:
            return
        ch = self._ios_jobs.get(event.job_id)
        if ch is None:
            return
        try:
            ch.put_nowait(event)
        except asyncio.QueueFull:
            pass

    def await_ios_job_result(self, job_id: str) -> asyncio.Future:
        """Register a one-shot waiter for a NodeIosJobResult.

        A server-side WDA job dispatch awaits this so a pending job never hangs
        on the ack timeout alone — the terminal result resolves the future.
        """
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._ios_job_results[job_id] = fut
        return fut

    def cancel_ios_job_result(self, job_id: str) -> None:
        self._ios_job_results.pop(job_id, None)

    def deliver_ios_job_result(self, result: Optional["pb.NodeIosJobResult"]) -> None:
        """Resolve the terminal outcome future for a WDA job."""
        if result is None:
            return
        fut = self._ios_job_results.pop(result.job_id, None)
        if fut is not None and not fut.done():
            fut.set_result(result)
        # Update job snapshot with terminal result
        snapshot = self._ios_job_snapshots.get(result.job_id)
        if snapshot:
            from . import crypto
            snapshot["status"] = "completed" if result.ok else "failed"
            snapshot["error_code"] = result.error_code
            snapshot["message"] = result.error_message
            snapshot["stage_reached"] = result.stage_reached
            snapshot["retryable"] = result.retryable
            snapshot["profile_expires_at"] = result.profile_expires_at
            snapshot["artifact_sha256"] = result.artifact_sha256
            snapshot["completed_at"] = crypto.rfc3339nano(crypto.utc_now())
            snapshot["updated_at"] = snapshot["completed_at"]

    def init_ios_job_snapshot(
        self, job_id: str, device_id: str, udid: str, action: str
    ) -> None:
        """Initialize a job snapshot when the job is dispatched."""
        from . import crypto
        now = crypto.rfc3339nano(crypto.utc_now())
        self._ios_job_snapshots[job_id] = {
            "job_id": job_id,
            "device_id": device_id,
            "udid": udid,
            "action": action,
            "status": "running",
            "stage": "queued",
            "percent": 0,
            "message": "",
            "retryable": False,
            "error_code": "",
            "created_at": now,
            "updated_at": now,
            "completed_at": "",
            "events": [],
        }

    def update_ios_job_snapshot_event(self, event: "pb.NodeIosJobEvent") -> None:
        """Update job snapshot with a progress event."""
        snapshot = self._ios_job_snapshots.get(event.job_id)
        if not snapshot:
            return
        from . import crypto
        now = crypto.rfc3339nano(crypto.utc_now())
        snapshot["stage"] = event.stage
        snapshot["message"] = event.message
        snapshot["percent"] = event.percent
        snapshot["retryable"] = event.retryable
        snapshot["updated_at"] = now
        snapshot["events"].append({
            "seq": event.seq,
            "stage": event.stage,
            "message": event.message,
            "timestamp": now,
        })
        # Keep only last 20 events to bound memory
        if len(snapshot["events"]) > 20:
            snapshot["events"] = snapshot["events"][-20:]

    def get_ios_job_snapshot(self, job_id: str) -> dict | None:
        """Retrieve a job snapshot for polling queries."""
        return self._ios_job_snapshots.get(job_id)

    def clear_ios_job_snapshot(self, job_id: str) -> None:
        """Remove a job snapshot (after client acknowledges completion)."""
        self._ios_job_snapshots.pop(job_id, None)

    # ── generic node builds (mirror of the iOS job machinery) ─────────────

    def open_build_job(self, build_id: str) -> asyncio.Queue:
        """Register a queue for one build's progress events. Mirrors
        :meth:`open_ios_job`: the dispatcher opens the queue before sending
        ``NodeBuildRequest`` so no progress frame can be missed."""
        ch: asyncio.Queue = asyncio.Queue(maxsize=TERMINAL_OUTPUT_BUFFER)
        self._build_jobs[build_id] = ch
        return ch

    def close_build_job(self, build_id: str) -> None:
        self._build_jobs.pop(build_id, None)

    def deliver_build_event(self, event: Optional["pb.NodeBuildEvent"]) -> None:
        """Hand one build event to its consumer. A None sentinel ends it."""
        if event is None:
            return
        ch = self._build_jobs.get(event.build_id)
        if ch is None:
            return
        try:
            ch.put_nowait(event)
        except asyncio.QueueFull:
            pass

    def await_build_result(self, build_id: str) -> asyncio.Future:
        """Register a one-shot waiter for a NodeBuildResult. Mirrors
        :meth:`await_ios_job_result`."""
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._build_results[build_id] = fut
        return fut

    def cancel_build_result(self, build_id: str) -> None:
        self._build_results.pop(build_id, None)

    def deliver_build_result(self, result: Optional["pb.NodeBuildResult"]) -> None:
        """Resolve the terminal outcome future for a build and mark the
        snapshot terminal. Mirrors :meth:`deliver_ios_job_result`."""
        if result is None:
            return
        fut = self._build_results.pop(result.build_id, None)
        if fut is not None and not fut.done():
            fut.set_result(result)
        snapshot = self._build_snapshots.get(result.build_id)
        if snapshot:
            from . import crypto
            snapshot["status"] = "completed" if result.ok else "failed"
            snapshot["error_code"] = result.error_code
            snapshot["message"] = result.error_message
            snapshot["stage_reached"] = result.stage_reached
            snapshot["retryable"] = result.retryable
            snapshot["artifact_sha256"] = result.artifact_sha256
            snapshot["artifact_size_bytes"] = result.artifact_size_bytes
            snapshot["completed_at"] = crypto.rfc3339nano(crypto.utc_now())
            snapshot["updated_at"] = snapshot["completed_at"]

    def init_build_snapshot(
        self, build_id: str, recipe_kind: str, node_id: str
    ) -> None:
        """Initialize a build snapshot when the build is dispatched."""
        from . import crypto
        now = crypto.rfc3339nano(crypto.utc_now())
        self._build_snapshots[build_id] = {
            "build_id": build_id,
            "recipe_kind": recipe_kind,
            "node_id": node_id,
            "status": "running",
            "stage": "queued",
            "percent": 0,
            "message": "",
            "retryable": False,
            "error_code": "",
            "artifact_sha256": "",
            "artifact_size_bytes": 0,
            "created_at": now,
            "updated_at": now,
            "completed_at": "",
            "events": [],
        }

    def update_build_snapshot_event(self, event: "pb.NodeBuildEvent") -> None:
        """Update build snapshot with a progress event."""
        snapshot = self._build_snapshots.get(event.build_id)
        if not snapshot:
            return
        from . import crypto
        now = crypto.rfc3339nano(crypto.utc_now())
        snapshot["stage"] = event.stage
        snapshot["message"] = event.message
        snapshot["percent"] = event.percent
        snapshot["updated_at"] = now
        snapshot["events"].append({
            "seq": event.seq,
            "stage": event.stage,
            "message": event.message,
            "timestamp": now,
        })
        if len(snapshot["events"]) > 20:
            snapshot["events"] = snapshot["events"][-20:]

    def get_build_snapshot(self, build_id: str) -> dict | None:
        """Retrieve a build snapshot for polling queries."""
        return self._build_snapshots.get(build_id)

    def clear_build_snapshot(self, build_id: str) -> None:
        """Remove a build snapshot (after client acknowledges completion)."""
        self._build_snapshots.pop(build_id, None)

    # ── teardown ──────────────────────────────────────────────────────────
    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Wake the downstream pump with a sentinel so it exits its await.
        try:
            self._downstream.put_nowait(None)
        except asyncio.QueueFull:
            pass
        # Fail any pending ack waiters so callers stop blocking.
        for fut in self._acks.values():
            if not fut.done():
                fut.set_exception(ConnectionError(f"node {self.node_id} disconnected"))
        self._acks.clear()
        for fut in self._host_execs.values():
            if not fut.done():
                fut.set_exception(ConnectionError(f"node {self.node_id} disconnected"))
        self._host_execs.clear()
        # A console waiting on a terminal list must fail fast rather than block
        # for the dispatch timeout: the node that would have answered is gone.
        for fut in self._terminal_lists.values():
            if not fut.done():
                fut.set_exception(ConnectionError(f"node {self.node_id} disconnected"))
        self._terminal_lists.clear()
        # An upload waiting on a chunk ack must fail immediately rather than
        # blocking for the dispatch timeout; the node drops its temp file when
        # the connection goes away, so the upload cannot be resumed anyway.
        for fut in self._file_uploads.values():
            if not fut.done():
                fut.set_exception(ConnectionError(f"node {self.node_id} disconnected"))
        self._file_uploads.clear()
        # Wake any tunnel consumers (reverse-proxy + node-mode forward proxy)
        # blocked on their queue with a None sentinel — both treat None as
        # "stream ended". Without this a request streaming a response when the
        # node drops hangs until PROXY_RESPONSE_TIMEOUT instead of failing fast.
        for ch in self._tunnels.values():
            try:
                ch.put_nowait(None)
            except asyncio.QueueFull:
                pass
        self._tunnels.clear()
        # Wake any terminal consumers blocked on their queue with a None
        # sentinel (the websocket bridge treats None as "terminal gone").
        for ch in self._terminals.values():
            try:
                ch.put_nowait(None)
            except asyncio.QueueFull:
                pass
        self._terminals.clear()
        # Wake any tool-run consumers (tunnel manager daemons) so a dispatcher
        # blocked on the event stream fails fast instead of hanging.
        for ch in self._tool_runs.values():
            try:
                ch.put_nowait(None)
            except asyncio.QueueFull:
                pass
        self._tool_runs.clear()
        # Fail any pending iOS WDA job result waiters so a dispatch blocked on
        # the job outcome fails fast instead of hanging past the ack timeout.
        for fut in self._ios_job_results.values():
            if not fut.done():
                fut.set_exception(ConnectionError(f"node {self.node_id} disconnected"))
        self._ios_job_results.clear()
        # Wake any iOS WDA job event consumers (Stage 3 job followers) blocked
        # on their queue with a None sentinel so the follower knows the stream
        # ended when the node disconnected mid-job.
        for ch in self._ios_jobs.values():
            try:
                ch.put_nowait(None)
            except asyncio.QueueFull:
                pass
        self._ios_jobs.clear()
        # Fail any pending build result waiters (project-page build dispatch)
        # and wake build event consumers, same as the iOS job machinery above.
        for fut in self._build_results.values():
            if not fut.done():
                fut.set_exception(ConnectionError(f"node {self.node_id} disconnected"))
        self._build_results.clear()
        for ch in self._build_jobs.values():
            try:
                ch.put_nowait(None)
            except asyncio.QueueFull:
                pass
        self._build_jobs.clear()

    @property
    def closed(self) -> bool:
        return self._closed


class Registry:
    """In-memory set of currently connected nodes. A node may only have one live
    connection at a time; a new connection for the same node id evicts the old
    one (the node reconnected)."""

    def __init__(self) -> None:
        self._conns: dict[str, Connection] = {}
        # Optional hook fired when a node's live connection is *definitively*
        # removed (genuine disconnect, force-drop, or reap) — NOT when a fresh
        # reconnect merely supersedes a stale stream. NodeService wires this to
        # ReplayCache.release so a node that restarts inside the same TOTP step
        # can re-authenticate immediately instead of being locked out by its own
        # still-claimed code. See ReplayCache for the reasoning.
        self.on_disconnect: Optional[Callable[[str], None]] = None
        # Optional heartbeat hook: receives (node_id, active_tool_runs) after the
        # inventory is recorded. Kept sync/fire-and-forget so registry liveness
        # never waits on data-service reconciliation.
        self.on_tool_runs: Optional[Callable[[str, list[dict]], None]] = None

    def _fire_disconnect(self, node_id: str) -> None:
        if self.on_disconnect is None:
            return
        try:
            self.on_disconnect(node_id)
        except Exception:  # noqa: BLE001 — a hook error must not break teardown
            pass

    def register(
        self, node_id: str, caps: Optional["pb.NodeCapabilities"], peer_address: str = ""
    ) -> Connection:
        """Register a live connection for ``node_id``, evicting any previous
        connection for the same node (a reconnect supersedes the stale stream)."""
        conn = Connection(node_id, caps, peer_address)
        existing = self._conns.get(node_id)
        if existing is not None:
            # A reconnect replacing a stale stream: do NOT fire on_disconnect. The
            # new connection has already authenticated and holds its own claim;
            # releasing by node id here would drop that fresh claim.
            existing.close()
        self._conns[node_id] = conn
        return conn

    def unregister(self, node_id: str, conn: Connection) -> None:
        """Tear down and forget a connection, but only if the registered
        connection is still the one passed in — avoids a reconnect's fresh
        connection being removed by the teardown of the stale one it replaced."""
        if conn is None:
            return
        current = self._conns.get(node_id)
        if current is conn:
            del self._conns[node_id]
            # Only a genuine teardown of the live connection releases the claim;
            # a superseded stale stream (current is the new conn) must not.
            self._fire_disconnect(node_id)
        conn.close()

    def disconnect(self, node_id: str) -> None:
        """Forcibly drop a node's live connection (e.g. on revoke/delete)."""
        conn = self._conns.pop(node_id, None)
        if conn is not None:
            conn.close()
            self._fire_disconnect(node_id)

    def lookup(self, node_id: str) -> Optional[Connection]:
        return self._conns.get(node_id)

    def connected(self, node_id: str) -> bool:
        return node_id in self._conns

    def list(self) -> list[str]:
        return list(self._conns.keys())

    def reap_stale(self, now: datetime, timeout_seconds: float) -> list[str]:
        """Drop connections whose last heartbeat is older than ``timeout``.

        A connection that has never reported a heartbeat is judged from its
        connect time instead, so a node that registers but never beats is still
        eventually reaped. Returns the node ids that were dropped.
        """
        stale: list[str] = []
        for node_id, conn in list(self._conns.items()):
            _, last_heartbeat_at, _ = conn.snapshot()
            ref = last_heartbeat_at or conn.connected_at
            if (now - ref).total_seconds() > timeout_seconds:
                del self._conns[node_id]
                stale.append(node_id)
                conn.close()
                self._fire_disconnect(node_id)
        return stale
