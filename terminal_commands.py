"""Run one Agent command inside a browser-attached node PTY.

The node terminal page shows a live PTY. When the agent wants to run a command
it must appear in *that* terminal — typed, echoed and streamed like the operator
typed it — while the agent still gets a structured result (exit code + bounded
output). Doing that with a second `host_exec` shell would execute somewhere the
operator cannot see, so instead the command is written into the PTY's stdin and
the gateway tees the PTY output it is already forwarding to the browser.

Boundary detection: a shell gives no "command finished" signal on a PTY, so the
command is wrapped to print an unguessable marker plus the exit status. The
gateway strips the marker from what the browser sees and from what the agent
receives — neither side should see the wrapper, only the command and its output.

Ownership: one registry entry per browser-attached terminal, keyed by
``(node_id, terminal_id)``. Registration/unregistration is the websocket
bridge's job, so the entry's presence *is* the proof that a browser is attached.
A command against a terminal nobody is watching fails rather than silently
running unobserved.
"""
from __future__ import annotations

import asyncio
import contextlib
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

# A command may not run forever: it holds the terminal's input lock and blocks
# the agent turn. The caller may lower this, never raise it.
DEFAULT_COMMAND_TIMEOUT_MS = 120_000
MAX_COMMAND_TIMEOUT_MS = 600_000
# What the agent receives. The browser still sees the full stream; only the copy
# handed back to the model is bounded.
DEFAULT_MAX_OUTPUT_BYTES = 256 * 1024
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
# After Ctrl-C, how long to let the shell wind down before giving up on it.
CANCEL_GRACE_SECONDS = 3.0

_ETX = b"\x03"  # Ctrl-C

# Interactive programs take over the terminal; this bridge only supports
# commands that run to completion and hand the prompt back.
_INTERACTIVE_COMMANDS = {
    "vi", "vim", "nvim", "nano", "emacs", "pico", "less", "more", "man",
    "top", "htop", "btop", "watch", "tail-f", "ssh", "telnet", "ftp", "sftp",
    "mysql", "psql", "redis-cli", "mongo", "sqlite3", "python", "python3",
    "node", "irb", "ipython", "gdb", "lldb", "screen", "tmux", "su", "sudo",
    "passwd", "login", "docker-attach",
}


class TerminalCommandError(Exception):
    """A command could not be started or completed. ``code`` is machine-readable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_command(command: str) -> str:
    """Return the trimmed command, or raise for shapes this bridge cannot run.

    Rejects newlines (a PTY write is one line; embedded newlines would submit
    lines the approval card never showed) and known interactive programs (they
    never return the prompt, so the marker never arrives and the command would
    just time out holding the terminal).
    """
    text = (command or "").strip()
    if not text:
        raise TerminalCommandError("invalid_command", "命令不能为空")
    if "\n" in text or "\r" in text:
        raise TerminalCommandError("invalid_command", "只支持单行命令")
    if "\x00" in text:
        raise TerminalCommandError("invalid_command", "命令包含非法字符")
    head = re.split(r"[\s;&|]+", text, maxsplit=1)[0].lower()
    head = head.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if head.endswith(".exe"):
        head = head[:-4]
    if head in _INTERACTIVE_COMMANDS:
        raise TerminalCommandError(
            "interactive_unsupported",
            f"{head} 是交互式程序，请在终端里手动执行",
        )
    return text


def _posix_wrapper(command: str, cwd: str, marker: str) -> str:
    """POSIX wrapper for a visible-elsewhere command.

    The gateway sends the *original* command line to the browser for the typed
    effect. The actual wrapper is implementation detail, so it disables terminal
    echo before submitting the wrapper, restores it after the command, then emits
    the private marker + exit code.
    """
    prefix = f"cd {_posix_quote(cwd)} && " if cwd else ""
    return (
        "stty -echo 2>/dev/null; "
        f"({prefix}{command}); __agent_status=$?; "
        "stty echo 2>/dev/null; "
        f"printf '\\r\\n{marker}%d\\r\\n' $__agent_status"
    )


def _posix_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _powershell_wrapper(command: str, cwd: str, marker: str) -> str:
    """PowerShell wrapper for a command whose display is provided by gateway.

    Bracketed paste prevents the raw wrapper text from being echoed in modern
    terminals. The gateway has already rendered the original command for the
    user, and strips the marker result line below.
    """
    prefix = f"Set-Location -LiteralPath {_powershell_quote(cwd)}; " if cwd else ""
    return (
        f"& {{ {prefix}{command} }}; "
        f"$__c = if ($LASTEXITCODE -ne $null) {{ $LASTEXITCODE }} elseif ($?) {{ 0 }} else {{ 1 }}; "
        f"Write-Host \"`r`n{marker}$__c\""
    )


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_wrapped_command(command: str, cwd: str, marker: str, shell_flavor: str) -> str:
    cwd = normalize_cwd_for_shell(cwd, shell_flavor)
    if shell_flavor == "powershell":
        return _powershell_wrapper(command, cwd, marker)
    return _posix_wrapper(command, cwd, marker)


def normalize_cwd_for_shell(cwd: str, shell_flavor: str) -> str:
    r"""Translate UI cwd into the shell's native syntax.

    The file browser presents Windows paths as `/C:/dir` (portable URL-like
    virtual path). PowerShell needs `C:\dir`; POSIX can use the path as-is.
    """
    value = (cwd or "").strip()
    if shell_flavor != "powershell" or not value:
        return value
    match = re.fullmatch(r"/([A-Za-z]):(?:/(.*))?", value)
    if not match:
        return value
    tail = (match.group(2) or "").replace("/", "\\")
    return f"{match.group(1).upper()}:\\{tail}" if tail else f"{match.group(1).upper()}:\\"


@dataclass
class _Collector:
    """Accumulates one command's PTY output until the end marker shows up."""

    marker: str
    max_output_bytes: int
    done: asyncio.Future
    chunks: list[bytes] = field(default_factory=list)
    size: int = 0
    truncated: bool = False
    exit_code: int | None = None
    echo_to_strip: bytes = b""
    echo_stripped: bool = False
    # Bytes held back because a marker could still straddle this boundary.
    _pending: bytes = b""

    def feed(self, chunk: bytes) -> bytes:
        """Absorb ``chunk``; return what the browser should see (marker removed).

        The marker can be split across two PTY reads, so the tail that could
        still be a marker prefix is withheld until the next chunk arrives.
        """
        if self.done.done():
            return chunk
        data = self._pending + chunk
        self._pending = b""
        if self.echo_to_strip and not self.echo_stripped:
            stripped = self._strip_echo(data)
            if stripped is None:
                # Need more bytes to decide whether this is the wrapper echo.
                self._pending = data
                return b""
            data = stripped
            self.echo_stripped = True
        marker = self.marker.encode("utf-8")
        index = self._find_result_marker(data, marker)
        if index >= 0:
            visible = data[:index]
            self._absorb(visible)
            tail_visible = self._finish(data[index + len(marker):])
            return visible + tail_visible
        # A result marker can arrive at the very end of a chunk, with the numeric
        # exit code in the next chunk. Hold that full marker (and whitespace) back
        # instead of leaking it to the browser/agent. Echoed wrapper input is not
        # held because it is followed by shell syntax such as `%d` or `$__c`.
        possible = data.rfind(marker)
        if possible >= 0 and re.fullmatch(rb"\s*", data[possible + len(marker):]):
            self._pending = data[possible:]
            data = data[:possible]
        keep = self._marker_prefix_len(data, marker)
        if keep:
            self._pending = data[len(data) - keep:]
            data = data[: len(data) - keep]
        self._absorb(data)
        return data

    def _strip_echo(self, data: bytes) -> bytes | None:
        """Strip the hidden wrapper if the PTY echoes it.

        Most Unix shells echo typed input; because we submit a wrapper, not the
        user-facing command, that echo must be hidden. When echo is already off
        (or bracketed paste suppresses it), the first output simply does not
        start with ``echo_to_strip`` and is passed through unchanged.
        """
        target = self.echo_to_strip
        if not target:
            return data
        if data.startswith(target):
            return data[len(target):]
        if target.startswith(data):
            return None
        return data

    @staticmethod
    def _find_result_marker(data: bytes, marker: bytes) -> int:
        """Find the marker that carries an exit code, not the shell's echo.

        Interactive shells often echo the *wrapper input* before running it, and
        that line contains the marker literal. Only the marker printed by the
        wrapper is immediately followed by optional whitespace and an integer;
        ignore earlier echoes so the command does not appear to finish before it
        actually runs.
        """
        start = 0
        while True:
            index = data.find(marker, start)
            if index < 0:
                return -1
            tail = data[index + len(marker):]
            if re.match(rb"\s*-?\d+", tail):
                return index
            start = index + len(marker)

    @staticmethod
    def _marker_prefix_len(data: bytes, marker: bytes) -> int:
        """Longest suffix of ``data`` that is a prefix of ``marker``."""
        limit = min(len(data), len(marker) - 1)
        for size in range(limit, 0, -1):
            if marker.startswith(data[len(data) - size:]):
                return size
        return 0

    def _absorb(self, data: bytes) -> None:
        if not data:
            return
        room = self.max_output_bytes - self.size
        if room <= 0:
            self.truncated = True
            return
        if len(data) > room:
            self.chunks.append(data[:room])
            self.size += room
            self.truncated = True
            return
        self.chunks.append(data)
        self.size += len(data)

    def _finish(self, tail: bytes) -> bytes:
        """Parse exit status and return bytes after the private marker line."""
        match = re.match(rb"\s*(-?\d+)", tail)
        rest = b""
        if match:
            with contextlib.suppress(ValueError):
                self.exit_code = int(match.group(1))
            rest = tail[match.end():]
            # Drop the marker line terminator, but keep a following prompt/output.
            rest = re.sub(rb"^(?:\r\n|\n|\r)", b"", rest, count=1)
        if not self.done.done():
            self.done.set_result(True)
        return rest

    def flush(self) -> bytes:
        """Release any withheld bytes (called when the command ends early)."""
        pending, self._pending = self._pending, b""
        return pending

    def text(self) -> str:
        return b"".join(self.chunks).decode("utf-8", errors="replace")

    def fail(self, exc: BaseException) -> None:
        if not self.done.done():
            self.done.set_exception(exc)


class ActiveTerminal:
    """One browser-attached PTY that can also run agent commands.

    ``input_locked`` is what stops the operator's keystrokes from interleaving
    with a running agent command; the websocket bridge consults it before
    forwarding a `data` frame.
    """

    def __init__(
        self,
        node_id: str,
        terminal_id: str,
        session,
        notify: Optional[Callable[[str, dict], Awaitable[None]]] = None,
        shell_flavor: str = "posix",
    ) -> None:
        self.node_id = node_id
        self.terminal_id = terminal_id
        self.session = session
        self.shell_flavor = shell_flavor
        # Where the typed-command echo and start/end markers go. A browser
        # websocket sets this while it is attached and clears it on detach, so a
        # command started before the operator closed the tab keeps running with
        # nothing to notify. The PTY output itself still lands in the terminal's
        # replay buffer, so a reconnecting browser sees what happened.
        self._notify_sink: Optional[Callable[[str, dict], Awaitable[None]]] = notify
        self._lock = asyncio.Lock()
        self._collector: _Collector | None = None
        self._closed = False
        # Markers from a timed-out/canceled command can arrive after the command
        # was already returned to the agent. Strip those late marker lines too.
        self._stale_markers: list[bytes] = []
        # What the agent is running here right now, for the management console.
        # The node reports the command line it saw submitted, but it cannot know
        # the command came from an agent rather than an operator's keystrokes —
        # and the wrapper it actually sees is bookkeeping noise. The server knows
        # both, so it overlays this onto the node's report.
        self._agent_command = ""
        self._agent_started_at: float | None = None

    async def _notify(self, kind: str, payload: dict) -> None:
        """Emit one UI event to the attached browser, if any.

        A detached terminal has no sink: the command keeps running and its PTY
        output still accumulates in the terminal's replay buffer, so dropping the
        event here loses only the live echo, not the work.
        """
        sink = self._notify_sink
        if sink is None:
            return
        with contextlib.suppress(Exception):
            await sink(kind, payload)

    def bind_notify(self, notify: Callable[[str, dict], Awaitable[None]]) -> None:
        """Point UI events at a newly attached browser websocket."""
        self._notify_sink = notify

    def unbind_notify(self, notify: Callable[[str, dict], Awaitable[None]]) -> None:
        """Detach a browser without disturbing a running command.

        Only clears the sink if it is still the one being detached, so a browser
        that reconnected before the old socket finished tearing down does not get
        its fresh sink removed by the stale one.
        """
        if self._notify_sink is notify:
            self._notify_sink = None

    @property
    def input_locked(self) -> bool:
        return self._collector is not None

    def agent_state(self) -> dict:
        """Snapshot the agent command in flight here (empty when idle).

        ``started_at`` is wall-clock epoch seconds so the console can render a
        duration without depending on this process's monotonic origin.
        """
        return {
            "running": self._collector is not None,
            "command": self._agent_command,
            "started_at": self._agent_started_at,
        }

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    def observe_output(self, chunk: bytes) -> bytes:
        """Tee PTY output into the running command; return what the browser sees."""
        collector = self._collector
        if collector is None:
            return self._strip_stale_markers(chunk)
        return self._strip_stale_markers(collector.feed(chunk))

    def _strip_stale_markers(self, chunk: bytes) -> bytes:
        data = chunk
        remaining: list[bytes] = []
        for marker in self._stale_markers:
            index = data.find(marker)
            if index < 0:
                remaining.append(marker)
                continue
            # Drop the marker + exit status line; preserve prompt bytes after it.
            tail = data[index + len(marker):]
            match = re.match(rb"\s*-?\d+", tail)
            if match:
                rest = tail[match.end():]
                rest = re.sub(rb"^(?:\r\n|\n|\r)", b"", rest, count=1)
                data = data[:index] + rest
            else:
                remaining.append(marker)
        self._stale_markers = remaining[-8:]
        return data

    def close(self) -> None:
        """The PTY itself is gone — fail any in-flight command instead of hanging.

        This is for the terminal actually dying (shell exited, explicit close,
        node dropped the PTY): the result marker can never arrive, so a waiting
        agent must be told now.

        A browser merely detaching is NOT this. Closing the tab used to land here
        and killed the command, which is exactly the behaviour we removed: the
        command keeps running on the node and the operator can reattach to watch
        it. Detach goes through :meth:`unbind_notify` instead.
        """
        self._closed = True
        collector = self._collector
        if collector is not None:
            collector.fail(
                TerminalCommandError("terminal_closed", "终端已关闭，命令中断")
            )

    def cancel_command(self, reason: str) -> bool:
        """Fail the in-flight agent command without closing the terminal.

        Used by the management console's interrupt/close actions: the Ctrl-C (or
        the PTY going away) means the result marker will never arrive, so the
        waiting agent must be told now rather than waiting out its timeout. The
        terminal itself stays usable — that is what separates this from
        :meth:`close`.
        """
        collector = self._collector
        if collector is None:
            return False
        collector.fail(TerminalCommandError("interrupted", reason))
        return True

    async def run_command(
        self,
        command: str,
        *,
        cwd: str = "",
        timeout_ms: int = DEFAULT_COMMAND_TIMEOUT_MS,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    ) -> dict:
        text = validate_command(command)
        # ``_closed`` means the PTY is gone, not that the browser detached: a
        # command can be started in a terminal nobody is currently watching.
        if self._closed:
            raise TerminalCommandError("terminal_closed", "终端已关闭")
        if self._lock.locked():
            raise TerminalCommandError("busy", "该终端正在执行另一条命令")

        timeout = min(max(int(timeout_ms or 0) or DEFAULT_COMMAND_TIMEOUT_MS, 1000), MAX_COMMAND_TIMEOUT_MS)
        cap = min(max(int(max_output_bytes or 0) or DEFAULT_MAX_OUTPUT_BYTES, 1024), MAX_OUTPUT_BYTES)

        async with self._lock:
            if self._closed:
                raise TerminalCommandError("terminal_closed", "终端已关闭")
            marker = f"__AGENT_CMD_{uuid.uuid4().hex}__"
            loop = asyncio.get_running_loop()
            collector = _Collector(marker=marker, max_output_bytes=cap, done=loop.create_future())
            self._collector = collector
            self._agent_command = text
            self._agent_started_at = time.time()
            started = time.monotonic()
            status = "ok"
            error = ""
            try:
                await self._notify("agent_command_start", {"command": text, "cwd": cwd})
                # Show the operator the exact command being executed, as if it
                # was typed. The following hidden wrapper is only for cwd/exit
                # code/marker bookkeeping and is stripped from PTY output.
                await self._notify("agent_command_output", {"data": text + "\r\n"})
                wrapped = build_wrapped_command(text, cwd, marker, self.shell_flavor)
                submit = (wrapped + "\r").encode("utf-8")
                collector.echo_to_strip = submit
                try:
                    self.session.send_input(submit)
                except Exception as exc:  # noqa: BLE001 — node may have dropped
                    raise TerminalCommandError(
                        "terminal_disconnected", f"命令下发失败：{exc}"
                    ) from exc
                try:
                    await asyncio.wait_for(collector.done, timeout=timeout / 1000)
                except asyncio.TimeoutError:
                    status = "timeout"
                    error = f"命令超过 {timeout // 1000} 秒未结束，已发送中断"
                    await self._interrupt(collector)
                except asyncio.CancelledError:
                    status = "canceled"
                    error = "命令已被取消"
                    await self._interrupt(collector)
                    raise
                except TerminalCommandError as exc:
                    status = "error"
                    error = exc.message
            finally:
                self._collector = None
                self._agent_command = ""
                self._agent_started_at = None
                if status in {"timeout", "canceled"}:
                    self._stale_markers.append(marker.encode("utf-8"))
                # Anything withheld for marker detection is real output the
                # browser must still see.
                pending = collector.flush()
                if pending:
                    with contextlib.suppress(Exception):
                        await self._notify(
                            "agent_command_output", {"data": pending.decode("utf-8", errors="replace")}
                        )
                with contextlib.suppress(Exception):
                    await self._notify("agent_command_end", {"status": status})

            return {
                "status": status,
                "exit_code": collector.exit_code if status == "ok" else None,
                "output": collector.text(),
                "output_truncated": collector.truncated,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "terminal_id": self.terminal_id,
                "cwd": cwd,
                "command": text,
                "error": error,
            }

    async def _interrupt(self, collector: _Collector) -> None:
        """Ctrl-C the foreground process and give it a moment to unwind.

        ``asyncio.wait`` (not ``wait_for``) so the grace period expiring does not
        cancel the collector future — the marker may still arrive and belongs to
        this command. Any failure here is best-effort: the caller already decided
        the command is over.
        """
        with contextlib.suppress(Exception):
            self.session.send_input(_ETX)
        with contextlib.suppress(BaseException):
            await asyncio.wait({collector.done}, timeout=CANCEL_GRACE_SECONDS)


class ActiveTerminalRegistry:
    """Agent-addressable terminals, keyed by ``(node_id, terminal_id)``.

    An entry's lifetime follows the PTY, not a browser websocket. A browser
    attaching binds its notify sink onto the existing entry (creating one if this
    is the first attach) and unbinds on detach; the entry itself survives so a
    command started before the tab closed keeps running and is still reported by
    the management console. Entries are dropped only when the terminal is really
    gone — :meth:`retire`, called when the PTY closes.
    """

    def __init__(self) -> None:
        self._terminals: dict[tuple[str, str], ActiveTerminal] = {}

    def register(self, terminal: ActiveTerminal) -> None:
        self._terminals[(terminal.node_id, terminal.terminal_id)] = terminal

    def get_or_create(
        self,
        node_id: str,
        terminal_id: str,
        session,
        *,
        shell_flavor: str = "posix",
    ) -> ActiveTerminal:
        """Return the entry for this terminal, creating it on first attach.

        A reattach must reuse the existing entry — that is what keeps a running
        agent command addressable across a browser reconnect. The session object
        is refreshed because a node reconnect rebinds the terminal to a new
        stream, and input must go to the live one.
        """
        key = (node_id, terminal_id)
        current = self._terminals.get(key)
        if current is not None:
            current.session = session
            return current
        created = ActiveTerminal(node_id, terminal_id, session, shell_flavor=shell_flavor)
        self._terminals[key] = created
        return created

    def retire(self, node_id: str, terminal_id: str) -> None:
        """Drop the entry because the PTY is gone, failing any running command."""
        terminal = self._terminals.pop((node_id, terminal_id), None)
        if terminal is not None:
            terminal.close()

    def get(self, node_id: str, terminal_id: str) -> Optional[ActiveTerminal]:
        return self._terminals.get((node_id, terminal_id))

    def list_for_node(self, node_id: str) -> list[str]:
        return [tid for (nid, tid) in self._terminals if nid == node_id]
