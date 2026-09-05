"""Host-shell terminal sessions over a node's NodeConnect stream.

Sits on top of the node registry (Connection objects), like
:mod:`node_connect_manager` does for the forward HTTP proxy. Provides a
high-level API to open an interactive PTY shell on a node's *host* machine,
push stdin/resize into it, and iterate its output — all multiplexed over the
single long-lived NodeConnect stream by ``terminal_id``.

The node is the party that actually spawns the shell in a pseudo-terminal (see
``nodes/common/agent/terminal.go``); this module only frames the requests and
demultiplexes the replies.

Used by the admin console websocket route (``routes_nodes_terminal``).

Security note: a terminal here is equivalent to shell access on the node host.
Authorization is the caller's responsibility and is enforced at the route
layer (platform admin only).
"""
from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from collections import deque
from typing import AsyncIterator, Awaitable, Callable, Optional

from loguru import logger

from . import agentcompose_v2_pb2 as pb
from . import crypto
from .registry import Connection, Registry


class NodeTerminalSession:
    """One interactive host-shell terminal on a node.

    Lifecycle: :meth:`open` (sends ``terminal_open``) → :meth:`iter_output`
    consumed by the websocket writer while :meth:`send_input`/:meth:`resize`
    are driven by the websocket reader → :meth:`close`.
    """

    def __init__(self, conn: Connection, terminal_id: Optional[str] = None):
        self.terminal_id = terminal_id or str(uuid.uuid4())
        self._conn = conn
        # Open the receive queue BEFORE the open frame goes out so no early
        # output frame can arrive with nowhere to land.
        self._recv_queue = conn.open_terminal(self.terminal_id)
        self._closed = False
        self._last_sequence: int = 0

    @property
    def last_sequence(self) -> int:
        """The sequence of the last output frame this session decoded.

        Used to resume from the right point on reattach after a NodeConnect
        reconnect so the node only replays what the server has not seen.
        """
        return self._last_sequence

    @property
    def closed(self) -> bool:
        return self._closed

    def _frame(self) -> "pb.NodeDownstreamFrame":
        return pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )

    def open(
        self,
        *,
        shell: str = "",
        cwd: str = "",
        rows: int = 24,
        cols: int = 80,
        session_id: str = "",
        env_id: str = "",
    ) -> None:
        """Ask the node to spawn the shell.

        ``shell``/``cwd`` empty let the node pick its platform default and the
        node user's home directory respectively. There is no ack frame: the
        first output (or a ``terminal_exit`` carrying an error) is the answer,
        which keeps an interactive stream from paying a round-trip up front.

        ``session_id`` opts into workspace-rooted shells: the node resolves that
        session's own working tree and starts there, so the server never has to
        know (or send) a node-local absolute path. An unknown session on the node
        degrades to ``cwd``/home rather than failing.

        ``env_id`` opens a MAINTENANCE shell inside a named shared environment:
        the node resolves the env dir and points the shell's HOME at it. It wins
        over ``session_id`` — a maintenance shell targets the environment, not a
        session workspace.
        """
        frame = self._frame()
        spec = pb.NodeTerminalOpen(
            terminal_id=self.terminal_id,
            shell=shell,
            cwd=cwd,
            session_id=session_id,
            env_id=env_id,
        )
        spec.terminal_size.rows = max(int(rows or 0), 0)
        spec.terminal_size.cols = max(int(cols or 0), 0)
        frame.terminal_open.CopyFrom(spec)
        self._send(frame)

    def send_input(self, data: bytes) -> None:
        """Write stdin bytes into the shell."""
        if not data:
            return
        frame = self._frame()
        frame.terminal_input.CopyFrom(
            pb.NodeTerminalInput(terminal_id=self.terminal_id, data=data)
        )
        self._send(frame)

    def resize(self, rows: int, cols: int) -> None:
        """Resize the shell's PTY window."""
        rows, cols = int(rows or 0), int(cols or 0)
        if rows <= 0 or cols <= 0:
            return
        frame = self._frame()
        spec = pb.NodeTerminalResize(terminal_id=self.terminal_id)
        spec.terminal_size.rows = rows
        spec.terminal_size.cols = cols
        frame.terminal_resize.CopyFrom(spec)
        self._send(frame)

    def attach(self, *, new_conn: Connection, after_sequence: int = 0) -> None:
        """Rebind to a fresh connection after a NodeConnect reconnect.

        The PTY survived the dropped stream on the node; this sends
        ``NodeTerminalAttach`` so the node replays its bounded tail beyond
        ``after_sequence`` and resumes live streaming. The receive queue is
        re-opened on the new connection before the frame goes out so no early
        replay frame can arrive with nowhere to land.
        """
        if self._closed:
            raise ConnectionError("terminal is closed")
        # Release the old queue and rebind to the new connection.
        try:
            self._conn.close_terminal(self.terminal_id)
        except Exception:  # noqa: BLE001
            pass
        self._conn = new_conn
        self._recv_queue = new_conn.open_terminal(self.terminal_id)
        frame = self._frame()
        spec = pb.NodeTerminalAttach(
            terminal_id=self.terminal_id, after_sequence=after_sequence
        )
        frame.terminal_attach.CopyFrom(spec)
        self._send(frame)

    async def iter_output(self) -> AsyncIterator[bytes]:
        """Yield PTY output chunks until the shell exits or the node drops.

        Ends (returns) on ``terminal_exit``, on the connection-closed ``None``
        sentinel, or when the terminal is closed locally. No idle timeout: an
        interactive shell is legitimately silent for long stretches — liveness
        is the node connection's own concern (heartbeat + reaper).

        The ``None`` sentinel (connection drop) does NOT release the session: the
        terminal is kept alive so a reconnect can reattach to the same PTY. Only
        a real ``terminal_exit`` or consumer abandonment releases local state.
        """
        try:
            while True:
                item = await self._recv_queue.get()
                if item is None:  # connection drop — reattachable, do NOT release
                    return
                if isinstance(item, pb.NodeTerminalExit):
                    err = (item.error or "").strip()
                    if err:
                        logger.debug(
                            "[nodeserver] terminal {} exited with error: {}",
                            self.terminal_id,
                            err,
                        )
                    self._release()
                    return
                data = bytes(getattr(item, "data", b"") or b"")
                if data:
                    self._last_sequence = int(getattr(item, "sequence", 0) or 0)
                    yield data
        except (GeneratorExit, asyncio.CancelledError):
            self._release()
            raise

    def close(self) -> None:
        """Tell the node to kill the shell, then release local state."""
        if self._closed:
            return
        try:
            frame = self._frame()
            frame.terminal_close.CopyFrom(
                pb.NodeTerminalClose(terminal_id=self.terminal_id)
            )
            self._send(frame)
        except Exception as exc:  # noqa: BLE001 - node may already be gone
            logger.debug("[nodeserver] terminal close send failed: {}", exc)
        finally:
            self._release()

    def _send(self, frame: "pb.NodeDownstreamFrame") -> None:
        if self._closed:
            raise ConnectionError("terminal is closed")
        self._conn.send(frame)

    def _release(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            # Wake the persistent pump before removing the queue from the
            # connection.  Otherwise a delete can wait forever on queue.get().
            queue = self._recv_queue
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                # Prefer the terminal-exit sentinel over stale output when a
                # disconnected browser left the bounded queue full.
                while True:
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                queue.put_nowait(None)
        except Exception:  # noqa: BLE001
            pass
        try:
            self._conn.close_terminal(self.terminal_id)
        except Exception:  # noqa: BLE001
            pass


class NodeTerminalManager:
    """Open host-shell terminals on connected nodes."""

    def __init__(self, registry: Registry):
        self._registry = registry

    def open(
        self,
        node_id: str,
        *,
        terminal_id: str | None = None,
        shell: str = "",
        cwd: str = "",
        rows: int = 24,
        cols: int = 80,
        session_id: str = "",
        env_id: str = "",
    ) -> NodeTerminalSession:
        """Open a terminal on ``node_id``. Raises ConnectionError if offline.

        ``session_id`` roots the shell in that node session's workspace (the node
        resolves the path itself); empty keeps the host-home behavior.
        ``env_id`` overrides ``session_id`` for a maintenance shell inside a
        shared environment: the node resolves the env dir and points HOME at it.
        """
        conn = self._registry.lookup(node_id)
        if conn is None or conn.closed:
            raise ConnectionError(f"node {node_id} is not connected")
        session = NodeTerminalSession(conn, terminal_id=terminal_id)
        try:
            session.open(
                shell=shell, cwd=cwd, rows=rows, cols=cols, session_id=session_id, env_id=env_id
            )
        except Exception:
            session._release()
            raise
        return session

    def close(self, node_id: str, terminal_id: str) -> None:
        """Kill a terminal on ``node_id`` without holding a session for it.

        A PTY outlives the server's bridge (it survives a server restart), so the
        management console must be able to close one the server has no
        :class:`NodeTerminalSession` for. Raises ConnectionError if the node is
        offline — the PTY is the node's, so there is nothing to do until it is
        back.
        """
        conn = self._registry.lookup(node_id)
        if conn is None or conn.closed:
            raise ConnectionError(f"node {node_id} is not connected")
        frame = pb.NodeDownstreamFrame(server_frame_id=str(uuid.uuid4()))
        frame.terminal_close.CopyFrom(pb.NodeTerminalClose(terminal_id=terminal_id))
        conn.send(frame)


class PersistentTerminal:
    """A node PTY that outlives an individual browser websocket."""

    _REPLAY_LIMIT = 256 * 1024

    def __init__(
        self,
        workspace_id: str,
        node_id: str,
        session: NodeTerminalSession,
        on_finished: Callable[["PersistentTerminal"], Awaitable[None]],
        owner: str = "",
    ) -> None:
        self.workspace_id = workspace_id
        self.node_id = node_id
        self.session = session
        self.terminal_id = session.terminal_id
        # Who opened it (admin/user id), for audit and the management Tab. Not
        # used for authorization here — the route layer already gated the caller.
        self.owner = owner
        self.created_at = time.time()
        self.last_activity = time.monotonic()
        # When the last browser detached (monotonic). None while a browser is
        # attached. A host terminal reaper uses this to age out a terminal that
        # nobody has watched for a while, independent of PTY output activity.
        self.detached_since: float | None = time.monotonic()
        self._on_finished = on_finished
        self._replay: deque[bytes] = deque()
        self._replay_size = 0
        self._subscriber: asyncio.Queue[bytes | None] | None = None
        self._closed = False
        self._pump_task = asyncio.create_task(self._pump())

    @property
    def closed(self) -> bool:
        # A terminal is closed only when explicitly closed or the node reported
        # exit. The pump task ending alone does not mean closed: it can end when
        # the node connection drops (reattachable) or when the browser detached.
        return self._closed or self.session.closed

    @property
    def _reattachable(self) -> bool:
        """The pump ended but the terminal is not closed — a reconnect can
        reattach to the same PTY."""
        return self._pump_task.done() and not self.closed

    def describe(self) -> dict:
        return {
            "id": self.terminal_id,
            "node_id": self.node_id,
            "owner": self.owner,
            "created_at": self.created_at,
            "connected_count": 1 if self._subscriber is not None else 0,
            "attached": self._subscriber is not None,
        }

    @property
    def attached(self) -> bool:
        return self._subscriber is not None

    async def rebind(self, new_conn: Connection) -> bool:
        """Rebind this terminal's session to a new node connection.

        The PTY survived the dropped stream, so the server asks the node to
        resume streaming rather than opening a fresh shell.
        """
        if self._closed:
            return False
        try:
            # The session owns the sequence cursor (it decodes the frames), so
            # resume from ITS last seen sequence — not a copy on this object.
            self.session.attach(
                new_conn=new_conn, after_sequence=self.session.last_sequence
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[terminal] reattach failed for terminal {} node {}: {}",
                self.terminal_id,
                self.node_id,
                exc,
            )
            return False
        # The old pump task ended when the old connection's iter_output did.
        # Start a fresh pump that consumes the new session's output.
        self._pump_task = asyncio.create_task(self._pump())
        return True

    def subscribe(self) -> asyncio.Queue[bytes | None]:
        """Attach one browser, replacing an older browser if necessary."""
        if self.closed:
            raise ConnectionError("terminal is closed")
        if self._subscriber is not None:
            with contextlib.suppress(asyncio.QueueFull):
                self._subscriber.put_nowait(None)
        queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=256)
        for chunk in self._replay:
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(chunk)
        self._subscriber = queue
        # A browser is watching again: cancel the detached grace clock.
        self.detached_since = None
        return queue

    def unsubscribe(self, queue: asyncio.Queue[bytes | None]) -> None:
        if self._subscriber is queue:
            self._subscriber = None
            # Start the detached grace clock: the reaper closes the PTY once this
            # exceeds the host-terminal detached TTL (nobody is watching anymore).
            self.detached_since = time.monotonic()

    def send_input(self, data: bytes) -> None:
        if data:
            self.last_activity = time.monotonic()
            self.session.send_input(data)

    def resize(self, rows: int, cols: int) -> None:
        self.session.resize(rows, cols)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._subscriber is not None:
            with contextlib.suppress(asyncio.QueueFull):
                self._subscriber.put_nowait(None)
            self._subscriber = None
        self.session.close()

    async def wait_closed(self) -> None:
        with contextlib.suppress(asyncio.CancelledError):
            await self._pump_task

    async def _pump(self) -> None:
        try:
            async for chunk in self.session.iter_output():
                self.last_activity = time.monotonic()
                self._append_replay(chunk)
                subscriber = self._subscriber
                if subscriber is not None:
                    try:
                        subscriber.put_nowait(chunk)
                    except asyncio.QueueFull:
                        # A browser that cannot consume output must reconnect and
                        # replay the bounded tail instead of blocking the node pump.
                        while not subscriber.empty():
                            with contextlib.suppress(asyncio.QueueEmpty):
                                subscriber.get_nowait()
                        subscriber.put_nowait(None)
                        # Dropping a stalled browser is a detach: start the grace
                        # clock, otherwise the terminal would sit with no
                        # subscriber and never age out of the host reaper.
                        self.unsubscribe(subscriber)
        except asyncio.CancelledError:
            pass
        finally:
            # Only mark closed if the session itself closed (the shell exited or
            # was explicitly closed). A connection drop leaves the session open
            # so the terminal stays in the registry for a potential rebind.
            if self.session.closed:
                self._closed = True
                subscriber = self._subscriber
                self._subscriber = None
                if subscriber is not None:
                    with contextlib.suppress(asyncio.QueueFull):
                        subscriber.put_nowait(None)
                await self._on_finished(self)
            else:
                # Connection drop: the terminal is reattachable. Tell the
                # registry to keep it; do not clear the subscriber here — the
                # browser websocket is already gone and will clean up itself.
                pass

    def _append_replay(self, chunk: bytes) -> None:
        self._replay.append(chunk)
        self._replay_size += len(chunk)
        while self._replay_size > self._REPLAY_LIMIT and self._replay:
            self._replay_size -= len(self._replay.popleft())


class PersistentTerminalRegistry:
    """Editor-workspace terminals keyed by ``(session_id, terminal_id)``."""

    def __init__(self, manager: NodeTerminalManager, inactivity_timeout: float = 900.0):
        self._manager = manager
        self._inactivity_timeout = inactivity_timeout
        self._terminals: dict[tuple[str, str], PersistentTerminal] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: asyncio.Task | None = None

    async def get_or_create(
        self,
        workspace_id: str,
        node_id: str,
        terminal_id: str,
        *,
        rows: int = 24,
        cols: int = 80,
    ) -> PersistentTerminal:
        key = (workspace_id, terminal_id)
        async with self._lock:
            current = self._terminals.get(key)
            if current is not None and not current.closed:
                if current.node_id != node_id:
                    raise ConnectionError("terminal node binding changed")
                return current
            session = self._manager.open(
                node_id,
                terminal_id=terminal_id,
                session_id=workspace_id,
                rows=rows,
                cols=cols,
            )
            terminal = PersistentTerminal(workspace_id, node_id, session, self._remove_finished)
            self._terminals[key] = terminal
            self._ensure_reaper()
            return terminal

    async def list(self, workspace_id: str) -> list[dict]:
        async with self._lock:
            items = [
                terminal.describe()
                for (owner, _), terminal in self._terminals.items()
                if owner == workspace_id and not terminal.closed
            ]
        return sorted(items, key=lambda item: item["created_at"], reverse=True)

    async def delete(self, workspace_id: str, terminal_id: str) -> bool:
        async with self._lock:
            terminal = self._terminals.pop((workspace_id, terminal_id), None)
        if terminal is None:
            return False
        terminal.close()
        await terminal.wait_closed()
        return True

    async def _remove_finished(self, terminal: PersistentTerminal) -> None:
        key = (terminal.workspace_id, terminal.terminal_id)
        async with self._lock:
            if self._terminals.get(key) is terminal:
                self._terminals.pop(key, None)

    def _ensure_reaper(self) -> None:
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._reap_loop())

    async def _reap_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(min(60.0, max(1.0, self._inactivity_timeout / 2)))
                cutoff = time.monotonic() - self._inactivity_timeout
                async with self._lock:
                    expired = [
                        (key, terminal)
                        for key, terminal in self._terminals.items()
                        if terminal.last_activity <= cutoff or terminal.closed
                    ]
                    for key, _ in expired:
                        self._terminals.pop(key, None)
                    empty = not self._terminals
                for _, terminal in expired:
                    terminal.close()
                if expired:
                    await asyncio.gather(
                        *(terminal.wait_closed() for _, terminal in expired),
                        return_exceptions=True,
                    )
                if empty:
                    return
        except asyncio.CancelledError:
            return


class NodeHostTerminalRegistry:
    """Persistent host terminals keyed by ``(node_id, terminal_id)``.

    The node owns the actual PTY. This registry deliberately owns only the
    control-plane bridge: it lets a browser detach and later reattach without
    translating a transient websocket failure into ``terminal_close``. A
    per-node cap bounds the retained PTYs across admin and user entry points.
    """

    def __init__(
        self,
        manager: NodeTerminalManager,
        *,
        max_active_per_node: int = 10,
        detached_ttl: float = 1800.0,
    ) -> None:
        self._manager = manager
        self._max_active_per_node = max(1, int(max_active_per_node))
        self._detached_ttl = max(1.0, float(detached_ttl))
        self._terminals: dict[tuple[str, str], PersistentTerminal] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: asyncio.Task | None = None
        # Fired when a terminal is definitively gone (PTY exited, explicit close,
        # or reaped). The gateway wires this to ActiveTerminalRegistry.retire so a
        # still-registered agent command is failed instead of waiting for a marker
        # that can no longer arrive. A browser merely detaching does NOT fire it.
        self.on_retired: Optional[Callable[[str, str], None]] = None
        # Queried by the reaper to keep a detached-but-busy terminal alive: it
        # returns True while an agent command is running in this terminal, so
        # "nobody is watching" does not mean "nobody is using it". The gateway
        # wires this to ActiveTerminalRegistry.get(...).input_locked.
        self.has_running_work: Optional[Callable[[str, str], bool]] = None

    def _fire_retired(self, node_id: str, terminal_id: str) -> None:
        if self.on_retired is None:
            return
        try:
            self.on_retired(node_id, terminal_id)
        except Exception as exc:  # noqa: BLE001 — a hook error must not break teardown
            logger.debug("[terminal] on_retired hook failed for {}: {}", terminal_id, exc)

    async def get_or_create(
        self,
        node_id: str,
        terminal_id: str,
        owner: str,
        *,
        rows: int = 24,
        cols: int = 80,
        env_id: str = "",
    ) -> PersistentTerminal:
        key = (node_id, terminal_id)
        async with self._lock:
            current = self._terminals.get(key)
            if current is not None and not current.closed:
                return current

            active_count = sum(
                1
                for terminal in self._terminals.values()
                if terminal.node_id == node_id and not terminal.closed
            )
            if active_count >= self._max_active_per_node:
                raise ConnectionError(
                    f"terminal_limit_reached: node terminal limit is {self._max_active_per_node}"
                )

            session = self._manager.open(
                node_id,
                terminal_id=terminal_id,
                rows=rows,
                cols=cols,
                env_id=env_id,
            )
            terminal = PersistentTerminal(
                node_id,
                node_id,
                session,
                self._remove_finished,
                owner=owner,
            )
            self._terminals[key] = terminal
            self._ensure_reaper()
            return terminal

    async def delete(self, node_id: str, terminal_id: str) -> bool:
        async with self._lock:
            terminal = self._terminals.pop((node_id, terminal_id), None)
        if terminal is None:
            return False
        terminal.close()
        await terminal.wait_closed()
        # The PTY is gone for good, so any agent command still waiting on it must
        # be failed rather than left waiting for a marker that cannot arrive.
        self._fire_retired(node_id, terminal_id)
        return True

    async def list_for_node(self, node_id: str) -> list[dict]:
        async with self._lock:
            items = [
                terminal.describe()
                for (nid, _), terminal in self._terminals.items()
                if nid == node_id and not terminal.closed
            ]
        return sorted(items, key=lambda item: item["created_at"], reverse=True)

    async def get_if_live(self, node_id: str, terminal_id: str) -> Optional[PersistentTerminal]:
        """Return this terminal if its PTY is still alive, else ``None``.

        Unlike :meth:`get_or_create` this never opens a shell: callers use it to
        ask "does this terminal exist right now?" without the side effect of
        creating one. Notably it is true for a terminal whose browser detached —
        the PTY is alive and still usable.
        """
        async with self._lock:
            terminal = self._terminals.get((node_id, terminal_id))
        if terminal is None or terminal.closed:
            return None
        return terminal

    async def rebind(self, node_id: str, terminal_id: str, new_conn: Connection) -> bool:
        """Rebind a terminal's session to a new node connection (on reconnect).

        The terminal's PTY survived the dropped stream, so the server asks the
        node to resume streaming rather than opening a fresh shell.
        """
        async with self._lock:
            terminal = self._terminals.get((node_id, terminal_id))
        if terminal is None or terminal.closed:
            return False
        return await terminal.rebind(new_conn)

    async def rebind_all(self, node_id: str, new_conn: Connection) -> None:
        """Rebind every live host terminal for ``node_id`` to ``new_conn``.

        Called on a NodeConnect reconnect: the PTYs survived the dropped stream,
        so the server reattaches to them instead of opening fresh shells (which
        would lose cwd and any running foreground process).
        """
        async with self._lock:
            terminals = [
                (tid, terminal)
                for (nid, tid), terminal in self._terminals.items()
                if nid == node_id
            ]
        for terminal_id, terminal in terminals:
            if terminal.closed or not terminal._reattachable:
                continue
            try:
                await terminal.rebind(new_conn)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "[terminal] rebind {} on node {} failed: {}",
                    terminal_id,
                    node_id,
                    exc,
                )

    async def _remove_finished(self, terminal: PersistentTerminal) -> None:
        key = (terminal.node_id, terminal.terminal_id)
        removed = False
        async with self._lock:
            if self._terminals.get(key) is terminal:
                self._terminals.pop(key, None)
                removed = True
        if removed:
            self._fire_retired(*key)

    def _ensure_reaper(self) -> None:
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._reap_loop())

    async def _reap_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(min(60.0, max(1.0, self._detached_ttl / 2)))
                now = time.monotonic()
                cutoff = now - self._detached_ttl
                async with self._lock:
                    expired = []
                    for key, terminal in self._terminals.items():
                        if terminal.closed:
                            expired.append((key, terminal))
                            continue
                        if terminal.detached_since is None or terminal.detached_since > cutoff:
                            continue
                        # Detached past the TTL, but still running work: NOT
                        # abandoned. Reaping would kill the task, which is exactly
                        # what "browser disconnect is not task cancellation" rules
                        # out. Restart the idle clock so that once the work does
                        # finish the operator still gets a full TTL to reattach and
                        # read the result — without this the terminal would be
                        # reaped on the very next tick after the task ended.
                        if self._has_running_work(*key):
                            terminal.detached_since = now
                            continue
                        expired.append((key, terminal))
                    for key, _ in expired:
                        self._terminals.pop(key, None)
                    empty = not self._terminals
                for _, terminal in expired:
                    terminal.close()
                if expired:
                    await asyncio.gather(
                        *(terminal.wait_closed() for _, terminal in expired),
                        return_exceptions=True,
                    )
                for key, _ in expired:
                    self._fire_retired(*key)
                if empty:
                    return
        except asyncio.CancelledError:
            return

    def _has_running_work(self, node_id: str, terminal_id: str) -> bool:
        """Whether a task is running in this terminal (keeps the reaper off it).

        Answered by the hook the gateway installs, because this registry owns the
        control-plane bridge and knows nothing about agent commands.
        """
        if self.has_running_work is None:
            return False
        try:
            return bool(self.has_running_work(node_id, terminal_id))
        except Exception as exc:  # noqa: BLE001 — never let a hook stall the reaper
            logger.debug("[terminal] has_running_work hook failed for {}: {}", terminal_id, exc)
            return False
