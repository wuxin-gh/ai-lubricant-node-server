import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from node_server import terminal_commands as tc


class FakeSession:
    def __init__(self):
        self.inputs = []

    def send_input(self, data: bytes) -> None:
        self.inputs.append(data)


@pytest.mark.asyncio
async def test_terminal_command_visible_line_hidden_wrapper_and_result_marker_filtered():
    events = []

    async def notify(kind, payload):
        events.append((kind, payload))

    session = FakeSession()
    terminal = tc.ActiveTerminal("node-1", "term-1", session, notify)

    task = asyncio.create_task(
        terminal.run_command("ls", cwd="/tmp", timeout_ms=5000, max_output_bytes=64)
    )
    await asyncio.sleep(0.01)

    submitted = session.inputs[0]
    marker = "__AGENT_CMD_" + submitted.decode().split("__AGENT_CMD_")[1].split("__")[0] + "__"

    assert events[0][0] == "agent_command_start"
    assert events[1] == ("agent_command_output", {"data": "ls\r\n"})
    # The wrapper may be echoed by an interactive shell; it is internal and must
    # not be shown to the browser or copied into the agent result.
    assert terminal.observe_output(submitted) == b""

    visible = terminal.observe_output(b"file\r\n")
    visible += terminal.observe_output((marker + "0\r\nprompt$ ").encode())
    result = await task

    assert result["status"] == "ok"
    assert result["exit_code"] == 0
    assert "file" in result["output"]
    assert marker not in result["output"]
    assert marker.encode() not in visible
    assert b"prompt$ " in visible
    assert events[-1][0] == "agent_command_end"


@pytest.mark.asyncio
async def test_terminal_command_rejects_concurrent_command_and_unlocks_after_done():
    async def notify(kind, payload):
        return None

    session = FakeSession()
    terminal = tc.ActiveTerminal("node-1", "term-1", session, notify)

    first = asyncio.create_task(terminal.run_command("pwd", timeout_ms=5000))
    await asyncio.sleep(0.01)
    assert terminal.input_locked is True

    with pytest.raises(tc.TerminalCommandError) as exc:
        await terminal.run_command("ls")
    assert exc.value.code == "busy"

    raw = session.inputs[0].decode()
    marker = "__AGENT_CMD_" + raw.split("__AGENT_CMD_")[1].split("__")[0] + "__"
    terminal.observe_output((marker + "0\r\n").encode())
    await first
    assert terminal.input_locked is False


@pytest.mark.asyncio
async def test_late_marker_after_timeout_is_filtered():
    async def notify(kind, payload):
        return None

    session = FakeSession()
    terminal = tc.ActiveTerminal("node-1", "term-1", session, notify)
    old_grace = tc.CANCEL_GRACE_SECONDS
    tc.CANCEL_GRACE_SECONDS = 0.01
    try:
        task = asyncio.create_task(terminal.run_command("sleep 100", timeout_ms=50))
        await asyncio.sleep(0.01)
        raw = session.inputs[0].decode()
        marker = "__AGENT_CMD_" + raw.split("__AGENT_CMD_")[1].split("__")[0] + "__"
        result = await task
    finally:
        tc.CANCEL_GRACE_SECONDS = old_grace

    assert result["status"] == "timeout"
    assert b"\x03" in session.inputs
    visible = terminal.observe_output(b"done\r\n" + marker.encode() + b"0\r\nprompt$ ")
    assert marker.encode() not in visible
    assert b"done" in visible
    assert b"prompt$ " in visible


def test_validate_command_and_windows_cwd_normalization():
    assert tc.validate_command("  ls -la  ") == "ls -la"
    assert tc.normalize_cwd_for_shell("/C:/Users/Admin", "powershell") == "C:\\Users\\Admin"
    assert tc.normalize_cwd_for_shell("/tmp", "posix") == "/tmp"

    for command, code in [
        ("", "invalid_command"),
        ("echo a\necho b", "invalid_command"),
        ("vim file.txt", "interactive_unsupported"),
    ]:
        with pytest.raises(tc.TerminalCommandError) as exc:
            tc.validate_command(command)
        assert exc.value.code == code
