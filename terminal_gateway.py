"""Internal WebSocket gateway for node terminals.

The control process owns PTY sessions and the live Registry. The data process
uses :func:`proxy_terminal` and never imports the terminal manager.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import hmac
import json
import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Body, Header, HTTPException, WebSocket, WebSocketDisconnect

from .terminal_bridge import (
    NodeHostTerminalRegistry,
    NodeTerminalManager,
    PersistentTerminalRegistry,
)
from .terminal_commands import (
    ActiveTerminal,
    ActiveTerminalRegistry,
    TerminalCommandError,
)
from .store import NODE_ROLE_PASSIVE_MANAGEMENT, NODE_STATUS_APPROVED
from .service import Code as _Code

_CLOSE_UNAVAILABLE = 4503
# No frame at all from the browser — not even a keep-alive ping — means the peer
# is gone. Bounds the receive so a half-open socket cannot pin the browser
# websocket forever. The PTY itself outlives the socket (it belongs to the node),
# so this only ends the observation, never the work.
_IDLE_TIMEOUT = 120.0
# Idle budget for a persistent terminal with nobody attached. Host terminals use
# their own detached TTL (see NodeHostTerminalRegistry); this one bounds editor
# workspace terminals.
_INACTIVITY_TIMEOUT = 900.0


def _authorized_header(header: str, token: str) -> bool:
    return bool(token) and header.startswith("Bearer ") and hmac.compare_digest(
        header[7:].strip(), token
    )


def _authorized(websocket: WebSocket, token: str) -> bool:
    return _authorized_header(websocket.headers.get("authorization", ""), token)


async def _send(websocket: WebSocket, kind: str, data: str = "") -> None:
    await websocket.send_text(json.dumps({"type": kind, "data": data}, ensure_ascii=False))


async def _shell_flavor(service, node_id: str) -> str:
    """Which wrapper syntax this node's shell needs (powershell vs posix).

    Agent commands are wrapped differently per shell, so the flavor must be known
    before one is submitted. An unknown node degrades to posix — the same default
    the websocket path uses.
    """
    record = await service.store.get_node_if_exists(node_id)
    caps = (getattr(record, "capabilities", None) or {}) if record is not None else {}
    return "powershell" if caps.get("os") == "windows" else "posix"


def build_control_terminal_router(service, token: str) -> APIRouter:
    router = APIRouter(tags=["internal-node-terminal"])
    persistent = PersistentTerminalRegistry(NodeTerminalManager(service.registry), _INACTIVITY_TIMEOUT)
    # Persistent HOST terminals (admin/user node shells). A browser websocket is
    # only an observer: closing the tab detaches it; the PTY survives so a
    # reconnect keeps cwd + foreground processes. Bounded per node across all
    # entry points by the configured cap.
    from .config import settings as _node_settings

    host = NodeHostTerminalRegistry(
        NodeTerminalManager(service.registry),
        max_active_per_node=_node_settings.node_terminal_max_active_per_node,
        detached_ttl=_node_settings.node_terminal_detached_ttl_seconds,
    )
    # When a node reconnects, reattach its host terminals to the fresh stream so
    # the PTY (and its foreground processes) survive the reconnect.
    async def _reattach_host_terminals(node_id: str, conn) -> None:
        await host.rebind_all(node_id, conn)

    service.on_node_connected = _reattach_host_terminals
    # Agent-addressable terminals. An entry lives as long as the PTY, not as long
    # as a browser websocket: a command started before the operator closed the tab
    # keeps running and stays addressable/observable.
    active = ActiveTerminalRegistry()

    # A terminal that is really gone must fail its in-flight command (the result
    # marker can never arrive). Detach does not come through here.
    host.on_retired = active.retire

    def _terminal_has_running_work(node_id: str, terminal_id: str) -> bool:
        """Keep the reaper off a detached terminal that is still doing work."""
        agent = active.get(node_id, terminal_id)
        return agent is not None and agent.input_locked

    host.has_running_work = _terminal_has_running_work

    async def session_binding(session_id: str):
        binding = await service.store.get_session_node(session_id)
        if binding is None:
            raise HTTPException(status_code=404, detail="session not found")
        record = await service.store.get_node_if_exists(binding.node_id)
        if record is None or (record.capabilities or {}).get("terminal") != "true":
            raise HTTPException(status_code=503, detail="terminal unsupported")
        return binding

    def require_token(authorization: str) -> None:
        if not _authorized_header(authorization, token):
            raise HTTPException(status_code=403, detail="invalid or missing bearer token")

    @router.get("/internal/session-terminals/{session_id}")
    async def list_session_terminals(
        session_id: str, authorization: str = Header(default="")
    ) -> dict:
        require_token(authorization)
        await session_binding(session_id)
        return {"terminals": await persistent.list(session_id)}

    @router.delete("/internal/session-terminals/{session_id}/{terminal_id}")
    async def delete_session_terminal(
        session_id: str, terminal_id: str, authorization: str = Header(default="")
    ) -> dict:
        require_token(authorization)
        await session_binding(session_id)
        if not await persistent.delete(session_id, terminal_id):
            raise HTTPException(status_code=404, detail="terminal not found")
        return {"deleted": True}

    @router.websocket("/internal/node-terminal/{node_id}")
    async def node_terminal(websocket: WebSocket, node_id: str) -> None:
        if not _authorized(websocket, token):
            await websocket.close(code=4403, reason="invalid or missing bearer token")
            return
        record = await service.store.get_node_if_exists(node_id)
        if record is None:
            await websocket.close(code=4404, reason="node not found")
            return
        if record.role == NODE_ROLE_PASSIVE_MANAGEMENT:
            await websocket.close(code=4403, reason="grouping container has no terminal")
            return
        if record.status != NODE_STATUS_APPROVED:
            await websocket.close(code=4403, reason="node not approved")
            return
        if (record.capabilities or {}).get("terminal") != "true":
            await websocket.close(code=_CLOSE_UNAVAILABLE, reason="terminal unsupported")
            return
        rows = int(websocket.query_params.get("rows") or 24)
        cols = int(websocket.query_params.get("cols") or 80)
        # A stable, browser-supplied terminal_id lets a reconnect reattach to the
        # SAME node PTY (preserving cwd + foreground processes). Empty means a
        # legacy client that never reattaches — mint a fresh id per connection.
        terminal_id = (websocket.query_params.get("terminal_id") or "").strip()
        if len(terminal_id) > 128:
            await websocket.close(code=4400, reason="invalid terminal id")
            return
        if not terminal_id:
            terminal_id = str(uuid.uuid4())
        # Attribution for the management Tab / audit; the proxy forwards it from
        # the data-service route which resolved the authenticated caller.
        owner = (websocket.query_params.get("owner") or "").strip()[:128]
        # Optional maintenance shell inside a named shared environment: the node
        # opens the shell with HOME pointed at the env dir. Empty = host home.
        env_id = (websocket.query_params.get("env_id") or "").strip()[:128]
        await websocket.accept()
        try:
            terminal = await host.get_or_create(
                node_id,
                terminal_id,
                owner,
                rows=rows,
                cols=cols,
                env_id=env_id,
            )
        except ConnectionError as exc:
            await _send(websocket, "error", str(exc))
            reason = (
                "该节点终端数已达上限"
                if "terminal_limit_reached" in str(exc)
                else "node offline"
            )
            await websocket.close(code=_CLOSE_UNAVAILABLE, reason=reason)
            return
        shell_flavor = "powershell" if (record.capabilities or {}).get("os") == "windows" else "posix"
        # Same rule as _shell_flavor; the record is already loaded here.
        await _bridge_persistent(
            websocket,
            terminal,
            {"node_id": node_id, "terminal_id": terminal.terminal_id},
            active=active,
            shell_flavor=shell_flavor,
        )

    @router.get("/internal/node-terminals/{node_id}")
    async def list_node_terminals(
        node_id: str, authorization: str = Header(default="")
    ) -> dict:
        """Every host terminal on a node, with what it is currently running.

        The node is the source of truth for its PTYs, so the list comes from it
        (:meth:`NodeService.query_terminals`). Two things the node cannot know are
        layered on top by the server:

        * ``owner`` — which admin/user opened the terminal, recorded when the
          control-plane bridge was created.
        * agent attribution — the node sees a submitted command line but not
          whether an agent or an operator typed it, and the wrapper it observes is
          bookkeeping noise. ``ActiveTerminalRegistry`` holds the real command, so
          an agent command in flight overrides the node's report.

        A terminal the server has no bridge for is still listed: it exists on the
        node, and hiding it would make the console lie about what is running.
        """
        require_token(authorization)
        try:
            result = await service.query_terminals(node_id)
        except Exception as exc:  # noqa: BLE001 — RPCError carries the real cause
            code = getattr(exc, "code", "")
            if code == _Code.NOT_FOUND:
                raise HTTPException(status_code=404, detail="node not found")
            if code == _Code.UNAVAILABLE:
                raise HTTPException(status_code=503, detail="node offline")
            if code == _Code.PERMISSION_DENIED:
                raise HTTPException(status_code=403, detail="node not approved")
            if code == _Code.DEADLINE_EXCEEDED:
                raise HTTPException(status_code=504, detail="node did not answer in time")
            raise HTTPException(status_code=503, detail=str(exc))

        bridges = {item["id"]: item for item in await host.list_for_node(node_id)}
        terminals: list[dict] = []
        for status in result.terminals:
            bridge = bridges.get(status.terminal_id) or {}
            agent_terminal = active.get(node_id, status.terminal_id)
            agent = agent_terminal.agent_state() if agent_terminal is not None else None
            if agent is not None and agent["running"]:
                source = "agent"
                current_command = agent["command"]
                started_at = agent["started_at"]
                running = True
            else:
                source = "personal"
                current_command = status.current_command
                started_at = status.started_at or None
                running = bool(status.running)
            terminals.append(
                {
                    "id": status.terminal_id,
                    "node_id": node_id,
                    "source": source,
                    "owner": bridge.get("owner", ""),
                    "current_command": current_command,
                    "running": running,
                    "started_at": started_at,
                    "created_at": status.created_at or None,
                    # The node reports whether IT is streaming; the server knows
                    # whether a browser is actually watching. Both matter: a
                    # terminal can be live on the node with nobody looking at it.
                    "node_attached": bool(status.attached),
                    "browser_attached": bool(bridge.get("attached")),
                    "managed": bool(bridge),
                }
            )
        terminals.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return {"terminals": terminals}

    @router.post("/internal/node-terminals/{node_id}/{terminal_id}/interrupt")
    async def interrupt_node_terminal(
        node_id: str, terminal_id: str, authorization: str = Header(default="")
    ) -> dict:
        """Stop the command running in a terminal, keep the terminal open.

        Ctrl-C goes to the node's PTY. When an agent command is in flight the
        server also fails it locally, otherwise the agent would sit waiting for a
        result marker that the interrupted command will never print.
        """
        require_token(authorization)
        agent_terminal = active.get(node_id, terminal_id)
        try:
            await service.interrupt_terminal(node_id, terminal_id)
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", "")
            if code == _Code.NOT_FOUND:
                raise HTTPException(status_code=404, detail="node not found")
            if code == _Code.UNAVAILABLE:
                raise HTTPException(status_code=503, detail="node offline")
            if code == _Code.PERMISSION_DENIED:
                raise HTTPException(status_code=403, detail="node not approved")
            raise HTTPException(status_code=503, detail=str(exc))
        interrupted_agent = False
        if agent_terminal is not None and agent_terminal.input_locked:
            agent_terminal.cancel_command("命令已被管理员中断")
            interrupted_agent = True
        return {"interrupted": True, "agent_command_interrupted": interrupted_agent}

    @router.delete("/internal/node-terminals/{node_id}/{terminal_id}")
    async def close_node_terminal(
        node_id: str, terminal_id: str, authorization: str = Header(default="")
    ) -> dict:
        """Close a terminal for good: kill the PTY and drop the bridge.

        This is the explicit "terminate everything here" action. Any agent command
        in flight is failed first so it reports a real error instead of hanging on
        a PTY that is about to disappear.
        """
        require_token(authorization)
        agent_terminal = active.get(node_id, terminal_id)
        if agent_terminal is not None and agent_terminal.input_locked:
            agent_terminal.cancel_command("终端已被管理员关闭，命令中断")
        if not await host.delete(node_id, terminal_id):
            # No control-plane bridge (e.g. a terminal that outlived a server
            # restart). The PTY is still the node's, so close it there directly
            # through the terminal manager (which only sends terminal_close).
            try:
                persistent_manager = NodeTerminalManager(service.registry)
                persistent_manager.close(node_id, terminal_id)
            except ConnectionError:
                raise HTTPException(status_code=503, detail="node offline")
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=503, detail=str(exc))
        return {"closed": True}

    @router.post("/internal/node-terminal/{node_id}/{terminal_id}/commands")
    async def run_terminal_command(
        node_id: str,
        terminal_id: str,
        authorization: str = Header(default=""),
        body: dict | None = Body(default=None),
    ) -> dict:
        body = body or {}
        require_token(authorization)
        terminal = active.get(node_id, terminal_id)
        if terminal is None:
            # No entry means no live PTY for this terminal — not merely "no browser
            # attached". A terminal whose operator closed the tab still has its
            # entry, so an agent command can start (or keep running) there and the
            # operator sees the output when they reattach.
            bridged = await host.get_if_live(node_id, terminal_id)
            if bridged is None:
                return {
                    "status": "error",
                    "code": "terminal_unavailable",
                    "error": "该节点终端不存在或已关闭，无法在终端中执行命令",
                    "terminal_id": terminal_id,
                }
            # A live PTY the agent registry has not seen yet (e.g. the terminal was
            # rebound after a node reconnect and no browser has attached since).
            # Adopt it so the command runs in the terminal the operator will see.
            shell_flavor = await _shell_flavor(service, node_id)
            terminal = active.get_or_create(
                node_id, terminal_id, bridged.session, shell_flavor=shell_flavor
            )
        try:
            return await terminal.run_command(
                str(body.get("command") or ""),
                cwd=str(body.get("cwd") or ""),
                timeout_ms=int(body.get("timeout_ms") or 0),
                max_output_bytes=int(body.get("max_output_bytes") or 0),
            )
        except TerminalCommandError as exc:
            # A refusal the agent must see verbatim (busy / disconnected /
            # interactive), not an opaque HTTP 500.
            return {
                "status": "error",
                "code": exc.code,
                "error": exc.message,
                "terminal_id": terminal_id,
            }

    @router.websocket("/internal/session-terminal/{session_id}")
    async def session_terminal(websocket: WebSocket, session_id: str) -> None:
        if not _authorized(websocket, token):
            await websocket.close(code=4403, reason="invalid or missing bearer token")
            return
        try:
            binding = await session_binding(session_id)
        except HTTPException as exc:
            await websocket.close(
                code=4404 if exc.status_code == 404 else _CLOSE_UNAVAILABLE,
                reason=str(exc.detail),
            )
            return
        terminal_id = (websocket.query_params.get("terminal_id") or "").strip()
        if not terminal_id or len(terminal_id) > 128:
            await websocket.close(code=4400, reason="invalid terminal id")
            return
        rows = int(websocket.query_params.get("rows") or 24)
        cols = int(websocket.query_params.get("cols") or 80)
        await websocket.accept()
        try:
            terminal = await persistent.get_or_create(
                session_id,
                binding.node_id,
                terminal_id,
                rows=rows,
                cols=cols,
            )
        except ConnectionError as exc:
            await _send(websocket, "error", str(exc))
            await websocket.close(code=_CLOSE_UNAVAILABLE, reason="node offline")
            return
        await _bridge_persistent(
            websocket,
            terminal,
            {"session_id": session_id, "terminal_id": terminal.terminal_id},
        )

    return router


async def _bridge_persistent(
    websocket: WebSocket,
    terminal,
    identity: dict,
    active: "ActiveTerminalRegistry | None" = None,
    shell_flavor: str = "posix",
) -> None:
    """Attach one browser websocket without owning the persistent PTY lifetime.

    When ``active`` is provided (host terminals), the terminal is registered as
    agent-addressable for as long as this browser is attached: agent commands run
    in *this* PTY, their marker is stripped from the output the browser sees, and
    the input is locked while a command owns the line. Editor terminals pass
    ``None`` — they do not drive agent commands.
    """
    queue = terminal.subscribe()
    await _send(websocket, "connected", json.dumps(identity, ensure_ascii=False))

    async def _notify(kind: str, payload: dict) -> None:
        await _send(websocket, kind, json.dumps(payload, ensure_ascii=False))

    node_id = str(identity.get("node_id") or "")
    terminal_id = str(identity.get("terminal_id") or "")
    agent: ActiveTerminal | None = None
    if active is not None and node_id and terminal_id:
        # Reuse the existing entry when one is there: a browser reconnecting to a
        # terminal that is mid-command must land on the SAME ActiveTerminal, or
        # the running command would be orphaned (no marker stripping, and the
        # console would report the terminal as idle).
        agent = active.get_or_create(
            node_id, terminal_id, terminal.session, shell_flavor=shell_flavor
        )
        agent.bind_notify(_notify)

    async def output() -> None:
        while True:
            chunk = await queue.get()
            if chunk is None:
                return
            # Strip agent-command markers so the operator never sees the wrapper.
            visible = agent.observe_output(chunk) if agent is not None else chunk
            if visible:
                await _send(websocket, "data", base64.b64encode(visible).decode("ascii"))

    async def input_frames() -> None:
        while True:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=_IDLE_TIMEOUT)
            try:
                frame = json.loads(raw)
            except (TypeError, ValueError):
                continue
            kind = frame.get("type")
            if kind == "data":
                # While an agent command owns the input line, operator keystrokes
                # would interleave with it, so they are dropped here too (the
                # frontend disables stdin; this is the server-side belt).
                if agent is not None and agent.input_locked:
                    continue
                terminal.send_input(base64.b64decode(frame.get("data") or ""))
            elif kind == "resize":
                try:
                    size = json.loads(frame.get("data") or "{}")
                    terminal.resize(int(size.get("row") or 0), int(size.get("col") or 0))
                except (TypeError, ValueError):
                    pass
            elif kind == "close":
                # Explicit "close terminal" from the browser: the operator chose to
                # terminate the shell (and its foreground processes), not just
                # detach. Kill the PTY; the pump then ends the output loop.
                terminal.close()
                return

    output_task = asyncio.create_task(output())
    input_task = asyncio.create_task(input_frames())
    try:
        done, pending = await asyncio.wait(
            {output_task, input_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            with contextlib.suppress(WebSocketDisconnect, asyncio.TimeoutError, RuntimeError, ConnectionError):
                await task
        for task in pending:
            task.cancel()
    finally:
        if agent is not None:
            # Detach only: unbind this socket's notify sink but leave the entry in
            # the registry. A command still running keeps running on the node —
            # closing the tab is not "cancel my task". The entry is retired when
            # the PTY itself goes away (see the terminal's finished hook).
            agent.unbind_notify(_notify)
            if terminal.closed:
                active.retire(node_id, terminal_id)
        terminal.unsubscribe(queue)
        for task in (output_task, input_task):
            task.cancel()
            with contextlib.suppress(BaseException):
                await task
        with contextlib.suppress(Exception):
            await websocket.close()


async def proxy_terminal(websocket: WebSocket, control_url: str, token: str, path: str) -> None:
    """Proxy browser WebSocket frames to the control terminal gateway."""
    import aiohttp

    query = urlencode({k: v for k, v in websocket.query_params.multi_items()})
    url = f"{control_url.rstrip('/')}{path}"
    if query:
        url += "?" + query
    await websocket.accept()
    timeout = aiohttp.ClientTimeout(total=None)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as client:
            async with client.ws_connect(url, headers={"Authorization": f"Bearer {token}"}) as upstream:
                async def browser_to_control() -> None:
                    while True:
                        await upstream.send_str(await websocket.receive_text())

                async def control_to_browser() -> None:
                    async for message in upstream:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            await websocket.send_text(message.data)
                        elif message.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            return

                await asyncio.gather(browser_to_control(), control_to_browser())
    except (WebSocketDisconnect, asyncio.CancelledError, aiohttp.ClientError):
        pass
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()
