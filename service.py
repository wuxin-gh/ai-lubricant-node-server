"""NodeService business logic (Python port of ``pkg/agentcompose/api``).

This is the control-plane brain: onboarding + TOTP mint + optional manager
launch, approve/revoke/delete with the ownership/online guards, first-eligible
dispatch, session delete/follow/input, the eight split-config RPCs, and the
``NodeRecord → NodeInfo`` projection.

It operates on **protobuf message objects** (from :mod:`.agentcompose_v2_pb2`),
exactly as the Go handlers operate on generated structs. The unary HTTP layer
(:mod:`.unary_api`) converts JSON↔proto with ``google.protobuf.json_format`` so
the wire shape (camelCase fields, proto enum names) matches what the
data-side ``monkeycode_compat.node_client`` already sends — no hand-mapping of field names.

Errors are raised as :class:`RPCError` carrying a Connect status code; the HTTP
layer maps that to the Connect error envelope + HTTP status.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json

from google.protobuf import json_format

import uuid
from datetime import timedelta
from typing import Awaitable, Callable, Optional

from loguru import logger

from . import agentcompose_v2_pb2 as pb
from . import crypto
from .registry import Connection, OutputSink, Registry
from .store import (
    NODE_ROLE_EXECUTION,
    NODE_ROLE_MANAGEMENT,
    NODE_ROLE_PASSIVE_MANAGEMENT,
    NODE_ROLE_IOS_HOST,
    NODE_STARTUP_DOCKER,
    NODE_STARTUP_STANDALONE,
    NODE_STATUS_APPROVED,
    NODE_STATUS_PENDING,
    NODE_STATUS_REVOKED,
    NodeNotFound,
    NodeRecord,
    NodeSessionBinding,
    NodeStore,
    PublicIPLookupConfig,
    SessionNotBound,
    normalize_node_role,
    normalize_node_status,
    normalize_startup_method,
)

# How long since a node's last heartbeat the server still considers it online.
NODE_HEARTBEAT_TIMEOUT = timedelta(seconds=60)

# How long DispatchSession / config commands wait for the node's ack.
DISPATCH_ACK_TIMEOUT = 30.0  # seconds

# Binary file upload limits are enforced at every layer. Keeping them here too
# prevents a direct Connect caller from sending an oversized frame to the node.
MAX_UPLOAD_CHUNK_BYTES = 1024 * 1024
MAX_UPLOAD_TOTAL_BYTES = 10 * 1024 * 1024

# Editor install/upgrade runs a global npm install (or the editor's own updater)
# on the node, which routinely takes minutes on a cold cache — far longer than a
# session dispatch, so it gets its own ceiling.
EDITOR_ACK_TIMEOUT = 600.0  # seconds

# How long ManageNodeEnvironment (create/remove a shared env dir) waits for the
# node's ack. mkdir/remove are cheap, but a slow filesystem on a loaded node can
# lag, so allow the same headroom as a config ack.
ENVIRONMENT_ACK_TIMEOUT = 30.0  # seconds
# Self-upgrade only waits for the node to ACCEPT (start download+restart); the
# real confirmation is the reconnect reporting the new version, so a short wait
# is enough — the node acks immediately then restarts asynchronously.
SELF_UPGRADE_ACK_TIMEOUT = 60.0  # seconds

# Editor CLIs this system can install/upgrade and report versions for. Must stay
# in sync with agent.SupportedEditors on the Go node side.
SUPPORTED_EDITORS = ("claude", "codex", "gemini", "opencode")
SUPPORTED_MANAGED_TOOLS = SUPPORTED_EDITORS + ("ocr",)


# ── Connect status codes (subset we emit) ──────────────────────────────────────
class Code:
    CANCELED = "canceled"
    UNKNOWN = "unknown"
    INVALID_ARGUMENT = "invalid_argument"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    FAILED_PRECONDITION = "failed_precondition"
    UNAVAILABLE = "unavailable"
    INTERNAL = "internal"


class RPCError(Exception):
    """A Connect-coded error. ``code`` is one of :class:`Code`."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ── enum mapping (proto enum ↔ internal string) ─────────────────────────────────

_STATUS_TO_PROTO = {
    NODE_STATUS_APPROVED: pb.NodeStatus.NODE_STATUS_APPROVED,
    NODE_STATUS_REVOKED: pb.NodeStatus.NODE_STATUS_REVOKED,
    NODE_STATUS_PENDING: pb.NodeStatus.NODE_STATUS_PENDING,
}
_PROTO_TO_STATUS = {
    pb.NodeStatus.NODE_STATUS_APPROVED: NODE_STATUS_APPROVED,
    pb.NodeStatus.NODE_STATUS_REVOKED: NODE_STATUS_REVOKED,
    pb.NodeStatus.NODE_STATUS_PENDING: NODE_STATUS_PENDING,
}
_ROLE_TO_PROTO = {
    NODE_ROLE_MANAGEMENT: pb.NodeRole.NODE_ROLE_MANAGEMENT,
    NODE_ROLE_PASSIVE_MANAGEMENT: pb.NodeRole.NODE_ROLE_PASSIVE_MANAGEMENT,
    NODE_ROLE_EXECUTION: pb.NodeRole.NODE_ROLE_EXECUTION,
    NODE_ROLE_IOS_HOST: pb.NodeRole.NODE_ROLE_IOS_HOST,
}
_PROTO_TO_ROLE = {
    pb.NodeRole.NODE_ROLE_MANAGEMENT: NODE_ROLE_MANAGEMENT,
    pb.NodeRole.NODE_ROLE_PASSIVE_MANAGEMENT: NODE_ROLE_PASSIVE_MANAGEMENT,
    pb.NodeRole.NODE_ROLE_EXECUTION: NODE_ROLE_EXECUTION,
    pb.NodeRole.NODE_ROLE_IOS_HOST: NODE_ROLE_IOS_HOST,
}
_STARTUP_TO_PROTO = {
    "standalone": pb.NodeStartupMethod.NODE_STARTUP_METHOD_STANDALONE,
    "systemd": pb.NodeStartupMethod.NODE_STARTUP_METHOD_SYSTEMD,
    "docker": pb.NodeStartupMethod.NODE_STARTUP_METHOD_DOCKER,
    "docker-compose": pb.NodeStartupMethod.NODE_STARTUP_METHOD_DOCKER_COMPOSE,
}
_PROTO_TO_STARTUP = {
    pb.NodeStartupMethod.NODE_STARTUP_METHOD_STANDALONE: "standalone",
    pb.NodeStartupMethod.NODE_STARTUP_METHOD_SYSTEMD: "systemd",
    pb.NodeStartupMethod.NODE_STARTUP_METHOD_DOCKER: "docker",
    pb.NodeStartupMethod.NODE_STARTUP_METHOD_DOCKER_COMPOSE: "docker-compose",
}


def status_to_proto(status: str) -> int:
    return _STATUS_TO_PROTO.get(status, pb.NodeStatus.NODE_STATUS_UNSPECIFIED)


def status_from_proto(status: int) -> str:
    return _PROTO_TO_STATUS.get(status, "")


def role_to_proto(role: str) -> int:
    return _ROLE_TO_PROTO.get(normalize_node_role(role), pb.NodeRole.NODE_ROLE_EXECUTION)


def role_from_proto(role: int) -> str:
    return _PROTO_TO_ROLE.get(role, "")


def startup_to_proto(method: str) -> int:
    return _STARTUP_TO_PROTO.get(
        normalize_startup_method(method), pb.NodeStartupMethod.NODE_STARTUP_METHOD_UNSPECIFIED
    )


def startup_from_proto(method: int) -> str:
    return _PROTO_TO_STARTUP.get(method, "")


def _public_ip_config_proto(config: PublicIPLookupConfig) -> "pb.NodePublicIPLookupConfig":
    return pb.NodePublicIPLookupConfig(
        revision=max(int(config.revision or 0), 0),
        ipv4_urls=list(config.ipv4_urls or []),
        ipv6_urls=list(config.ipv6_urls or []),
    )


def _node_proxy_config_proto(
    *, revision: int, fields: dict, proxy_config_id: str = ""
) -> "pb.NodeProxyConfig":
    """Build a NodeProxyConfig from a resolved proxy-pool entry.

    ``fields`` is the output of ``resolve_proxy`` (``proxy_mode`` /
    ``proxy_url`` / ``proxy_url_prefix``); empty/direct → all three blank.
    ``proxy_config_id`` is the bound pool-entry id (echoed back so the console
    can preselect it in the node's egress-proxy card — empty = direct).
    """
    return pb.NodeProxyConfig(
        revision=max(int(revision or 0), 0),
        proxy_mode=str(fields.get("proxy_mode") or ""),
        proxy_url=str(fields.get("proxy_url") or ""),
        proxy_url_prefix=str(fields.get("proxy_url_prefix") or ""),
        proxy_config_id=(proxy_config_id or ""),
    )


async def _resolve_node_proxy_fields_safe(proxy_config_id: str) -> dict:
    """Resolve a proxy-pool entry id to the three frame fields (direct on empty).

    Reuses the upgrade path's resolver. Degrades to direct (empty dict) on ANY
    failure (unknown id, node mode, pool read error) so a node's connect never
    500s over a stale binding — the admin will see the failure in the
    ``UpdateNodeProxyConfig`` admin path instead, which surfaces real errors.
    """
    from .shared_store import ProxyResolveError, resolve_proxy_fields

    try:
        return await resolve_proxy_fields(proxy_config_id or "")
    except ProxyResolveError:
        return {}
    except Exception:
        return {}


async def _resolve_node_proxy_fields(proxy_config_id: str) -> dict:
    """Resolve a proxy-pool entry id to the three frame fields (strict).

    Used by the admin ``UpdateNodeProxyConfig`` path where an unknown id or a
    ``node``-mode entry must surface as INVALID_ARGUMENT, not silently direct.
    """
    from .shared_store import ProxyResolveError, resolve_proxy_fields

    try:
        return await resolve_proxy_fields(proxy_config_id or "")
    except ProxyResolveError as exc:
        raise RPCError(Code.INVALID_ARGUMENT, str(exc)) from exc


def _validated_report_ip(value: str, *, version: int) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    try:
        parsed = ipaddress.ip_address(text)
    except ValueError:
        return ""
    if parsed.version != version:
        return ""
    return parsed.compressed


# ── capability helpers (mirror node.go capabilityLabels/Platform) ───────────────

def _capability_labels(caps: Optional["pb.NodeCapabilities"]) -> dict[str, str]:
    labels: dict[str, str] = {}
    if caps is None:
        return labels
    for k, v in caps.labels.items():
        labels[k] = v
    labels["os"] = caps.os
    labels["arch"] = caps.arch
    if caps.docker:
        labels["docker"] = "true"
    if list(caps.providers):
        labels["providers"] = ",".join(caps.providers)
    # Editor mode capabilities are structured, but NodeRecord.capabilities is a
    # flat string map. Serialize them into one reserved key so the ledger schema
    # is untouched; node_info reconstructs the repeated field from it. Nodes
    # that never报 editors simply have no key and project to an empty list.
    if list(caps.editors):
        labels["editors_json"] = json.dumps(
            [
                json_format.MessageToDict(editor, preserving_proto_field_name=True)
                for editor in caps.editors
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    return labels


def _capability_platform(caps: Optional["pb.NodeCapabilities"]) -> str:
    if caps is None:
        return ""
    return f"{caps.os}/{caps.arch}".strip()


def _is_manager_role(role: str) -> bool:
    return normalize_node_role(role) in (NODE_ROLE_MANAGEMENT, NODE_ROLE_PASSIVE_MANAGEMENT)


def _is_passive_manager(record: NodeRecord) -> bool:
    """A pure ownership container: never dials in, no credential, launches
    nothing. Explicit passive_management role, or legacy management-with-no-secret."""
    if record.role == NODE_ROLE_PASSIVE_MANAGEMENT:
        return True
    return record.role == NODE_ROLE_MANAGEMENT and not (record.credential_secret_enc or "").strip()


def _install_command(script_url: str, node_id: str, secret: str) -> str:
    return (
        f'AGENT_COMPOSE_NODE_ID={node_id} AGENT_COMPOSE_NODE_SECRET={secret} '
        f'bash <(curl -fsSL "{script_url}")'
    )


def _skill_spec_from_dict(item: dict) -> "pb.SkillSpec":
    """Build a SkillSpec from a resolved wire-spec dict (resource_reference_service
    shape). Only fields the node reads are set; unknown keys are ignored."""
    return pb.SkillSpec(
        name=str(item.get("name") or ""),
        source=str(item.get("source") or ""),
        url=str(item.get("url") or ""),
        path=str(item.get("path") or ""),
        ref=str(item.get("ref") or ""),
        token=str(item.get("token") or ""),
    )


def _plugin_spec_from_dict(item: dict) -> "pb.NodePluginSpec":
    return pb.NodePluginSpec(
        name=str(item.get("name") or ""),
        url=str(item.get("url") or ""),
        version=str(item.get("version") or ""),
    )



class NodeService:
    """The NodeService control plane. One instance per running server.

    Holds the durable store, the live registry, the AES secret store, and the
    TOTP replay cache. Methods mirror the Go ``NodeHandler`` RPC surface and
    take/return protobuf messages.
    """

    def __init__(
        self,
        *,
        master_key: bytes,
        server_url: str,
        store: NodeStore,
        registry: Registry,
        agent_image: str = "",
    ) -> None:
        self.server_url = (server_url or "").strip().rstrip("/")
        self.agent_image = (agent_image or "").strip()
        self.store = store
        self.registry = registry
        self.secrets = crypto.SecretStore(master_key)
        self.replay = crypto.ReplayCache()
        # Release a node's TOTP claim the moment its live connection is gone, so
        # a genuine restart inside the same 30s code step can re-authenticate
        # immediately. A second concurrent process reusing the code is still
        # rejected while the first holds the connection. (See crypto.ReplayCache
        # and Registry.on_disconnect.)
        # node_hosted MCP（形态 C）的进程跑在节点上，节点掉线即该 MCP 不可用。把
        # host_status 打成 dead，agent 侧的就绪门据此挡住它，避免拿到一个连不上的
        # MCP 才在 call_tool 处炸。链式挂在 replay.release 之后而非覆盖它——覆盖会
        # 破坏节点重连时的 TOTP 释放。
        self.registry.on_disconnect = self._on_node_disconnect
        # Fired after a node's NodeConnect stream is (re)established. Host
        # terminals outlive the stream, so the terminal registry hooks this to
        # reattach its live terminals to the fresh connection instead of letting
        # them strand on the dead one. Set by the terminal gateway at wiring
        # time. Belongs in __init__: this line once sat (misindented) at the
        # tail of _on_node_disconnect, so every disconnect nulled the hook and
        # after the first drop no reconnect ever reattached host terminals.
        self.on_node_connected: "Optional[Callable[[str, Connection], Awaitable[None]]]" = None

    def _on_node_disconnect(self, node_id: str) -> None:
        self.replay.release(node_id)
        try:
            import asyncio

            # In-process reconcile over the shared pool. The old import of
            # mcp_runtime.node_hosted raised ModuleNotFoundError in this
            # standalone process (mcp_plugin_store lives under server/, which
            # python -m node_server doesn't put on sys.path) — and violated
            # shared_store's no-data-service-import rule — so the reconcile
            # never actually ran here.
            from .node_hosted_reconcile import mark_node_hosted_offline

            asyncio.get_running_loop().create_task(mark_node_hosted_offline(node_id))
        except RuntimeError:
            pass  # 没有运行中的 loop（测试/同步路径），跳过对账
        except Exception as exc:  # noqa: BLE001 — 对账失败不该阻断连接拆除
            logger.debug("[nodeserver] node-hosted reconcile failed for {}: {}", node_id, exc)

    async def fire_node_connected(self, node_id: str, conn: Connection) -> None:
        """Best-effort notify that ``node_id`` has a fresh live connection."""
        hook = self.on_node_connected
        if hook is None:
            return
        try:
            await hook(node_id, conn)
        except Exception as exc:  # noqa: BLE001 — a hook error must not break the stream
            logger.debug("[nodeserver] on_node_connected hook failed for {}: {}", node_id, exc)

    async def rebind_host_terminals(self, node_id: str, conn: Connection) -> None:
        """Rebind host terminals for a node that just reconnected.

        Host PTYs survive a dropped NodeConnect stream, so a reconnect must
        reattach to the existing PTY rather than opening a fresh shell (which
        would lose cwd and any running foreground process).
        """
        hook = self.on_node_connected
        if hook is None:
            return
        # The hook is the terminal registry's rebind handler.
        try:
            await hook(node_id, conn)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[nodeserver] rebind_host_terminals for {} failed: {}", node_id, exc)

    # ── host terminal management console (batch-3) ─────────────────────────────
    async def query_terminals(self, node_id: str) -> "pb.NodeTerminalListResult":
        """List every open host terminal on a node and the command it last ran.

        The node is the source of truth for its PTYs; this sends a
        ``NodeTerminalListRequest`` (correlated by ``request_id``) and awaits
        the reply. The management console renders the result so an operator can
        see what each terminal is doing before interrupting or closing it.
        """
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if record.status != NODE_STATUS_APPROVED:
            raise RPCError(Code.PERMISSION_DENIED, f"node {node_id} is not approved")
        conn = self.registry.lookup(node_id)
        if conn is None or conn.closed:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} is offline")

        request_id = str(uuid.uuid4())
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.terminal_list.CopyFrom(pb.NodeTerminalListRequest(request_id=request_id))
        result_future = conn.await_terminal_list(request_id)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_terminal_list(request_id)
            raise RPCError(Code.UNAVAILABLE, f"dispatch terminal list to node {node_id}: {exc}")
        try:
            return await asyncio.wait_for(result_future, timeout=DISPATCH_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_terminal_list(request_id)
            raise RPCError(Code.DEADLINE_EXCEEDED, f"node {node_id} did not return terminal list in time")
        except ConnectionError:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} disconnected during terminal list")

    async def interrupt_terminal(self, node_id: str, terminal_id: str) -> None:
        """Interrupt the command currently running on a host terminal.

        Sends a Ctrl-C byte into the PTY; the terminal stays open. This is
        ``stop what it is doing``, not ``close it`` — the management console
        uses it to end a runaway command without losing the shell.
        """
        node_id = (node_id or "").strip()
        terminal_id = (terminal_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        if not terminal_id:
            raise RPCError(Code.INVALID_ARGUMENT, "terminal_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if record.status != NODE_STATUS_APPROVED:
            raise RPCError(Code.PERMISSION_DENIED, f"node {node_id} is not approved")
        conn = self.registry.lookup(node_id)
        if conn is None or conn.closed:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} is offline")
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.terminal_interrupt.CopyFrom(pb.NodeTerminalInterrupt(terminal_id=terminal_id))
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            raise RPCError(Code.UNAVAILABLE, f"dispatch interrupt to node {node_id}: {exc}")

    # ── long-running external tool runs (tunnel manager) ──────────────────
    async def start_tool_run(
        self,
        node_id: str,
        run_id: str,
        binary_path: str,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        cwd: str = "",
        revision: int = 0,
    ) -> None:
        """Start a long-running external CLI (frpc/cloudflared/npc) on a node.

        Returns once the start frame is dispatched; output + exit arrive as
        NodeToolRunEvent frames on ``conn.open_tool_run(run_id)``. The caller
        owns the run_id and the event-stream consumption.
        """
        node_id = (node_id or "").strip()
        run_id = (run_id or "").strip()
        binary_path = (binary_path or "").strip()
        if not node_id or not run_id or not binary_path:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id, run_id, binary_path are required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if record.status != NODE_STATUS_APPROVED:
            raise RPCError(Code.PERMISSION_DENIED, f"node {node_id} is not approved")
        conn = self.registry.lookup(node_id)
        if conn is None or conn.closed:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} is offline")
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        req = pb.NodeToolRunRequest(
            run_id=run_id, binary_path=binary_path, args=list(args or []),
            env=dict(env or {}), cwd=cwd or "", node_id=node_id,
            revision=max(int(revision or 0), 0),
        )
        frame.tool_run_request.CopyFrom(req)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.close_tool_run(run_id)
            raise RPCError(Code.UNAVAILABLE, f"dispatch tool run to node {node_id}: {exc}")

    async def stop_tool_run(self, node_id: str, run_id: str, *, grace_ms: int = 0) -> None:
        """Stop a previously started tool run by run_id (SIGTERM then SIGKILL)."""
        node_id = (node_id or "").strip()
        run_id = (run_id or "").strip()
        if not node_id or not run_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id and run_id are required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        conn = self.registry.lookup(node_id)
        if conn is None or conn.closed:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} is offline")
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.tool_run_stop.CopyFrom(
            pb.NodeToolRunStop(run_id=run_id, grace_ms=int(grace_ms or 0), node_id=node_id)
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            raise RPCError(Code.UNAVAILABLE, f"dispatch tool stop to node {node_id}: {exc}")

    def open_tool_run(self, node_id: str, run_id: str) -> asyncio.Queue:
        """Register an event-stream queue for a tool run (before start)."""
        conn = self.registry.lookup(node_id)
        if conn is None or conn.closed:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} is offline")
        return conn.open_tool_run(run_id)

    def close_tool_run(self, node_id: str, run_id: str) -> None:
        conn = self.registry.lookup(node_id)
        if conn is not None:
            conn.close_tool_run(run_id)

    # ── script URLs (mirror node_onboard.go scriptURL/ScriptFilename) ──────────
    def script_filename(self, role: str, method: str) -> str:
        role = normalize_node_role(role) or NODE_ROLE_EXECUTION
        method = normalize_startup_method(method) or NODE_STARTUP_STANDALONE
        return f"install-{role}-{method}.sh"

    def script_url(self, role: str, method: str) -> str:
        path = "/api/nodes/scripts/" + self.script_filename(role, method)
        return (self.server_url + path) if self.server_url else path

    async def public_ip_lookup_config_frame(self) -> "pb.NodeDownstreamFrame":
        config = await self.store.get_public_ip_lookup_config()
        frame = pb.NodeDownstreamFrame(created_at=crypto.rfc3339nano(crypto.utc_now()))
        frame.public_ip_lookup_config.CopyFrom(_public_ip_config_proto(config))
        return frame

    async def node_proxy_config_frame(
        self, node_id: str
    ) -> "pb.NodeDownstreamFrame":
        """Snapshot of one node's own egress-proxy binding, pushed on connect.

        Per-node: reads the node's ``proxy_config_id`` + ``proxy_revision``,
        resolves the pool entry to the three frame fields (direct on empty or
        on resolution failure — a node's connect must never 500 over a stale
        binding), and embeds ``proxy_revision`` so the Go revision gate accepts
        the freshest binding on reconnect.
        """
        record = await self.store.get_node_if_exists((node_id or "").strip())
        proxy_config_id = str(getattr(record, "proxy_config_id", "") or "") if record else ""
        revision = int(getattr(record, "proxy_revision", 0) or 0) if record else 0
        fields = await _resolve_node_proxy_fields_safe(proxy_config_id)
        frame = pb.NodeDownstreamFrame(created_at=crypto.rfc3339nano(crypto.utc_now()))
        frame.node_proxy_config.CopyFrom(
            _node_proxy_config_proto(
                revision=revision, fields=fields, proxy_config_id=proxy_config_id
            )
        )
        return frame

    async def get_node_proxy_config(
        self, req: "pb.GetNodeProxyConfigRequest"
    ) -> "pb.NodeProxyConfig":
        """Read one node's resolved egress-proxy binding."""
        node_id = (req.node_id or "").strip()
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        fields = await _resolve_node_proxy_fields_safe(record.proxy_config_id)
        return _node_proxy_config_proto(
            revision=record.proxy_revision,
            fields=fields,
            proxy_config_id=str(getattr(record, "proxy_config_id", "") or ""),
        )

    async def update_node_proxy_config(
        self, req: "pb.UpdateNodeProxyConfigRequest"
    ) -> "pb.NodeProxyConfig":
        """Bind a proxy-pool entry to one node, resolve, persist, push to it.

        Per-node: the resolved snapshot is pushed to *only* this node's live
        connection (no global broadcast). Offline nodes get the persisted
        binding on next connect via ``node_proxy_config_frame``. Empty
        ``proxy_config_id`` = direct. ``node``-mode and unknown ids are
        INVALID_ARGUMENT (surfaced here, unlike the connect-time safe path).
        """
        node_id = (req.node_id or "").strip()
        proxy_config_id = (req.proxy_config_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        # Strict resolution: reject node-mode / unknown ids before persisting.
        fields = await _resolve_node_proxy_fields(proxy_config_id)
        record = await self.store.update_node_proxy(
            node_id, proxy_config_id=proxy_config_id
        )
        snapshot = _node_proxy_config_proto(
            revision=record.proxy_revision,
            fields=fields,
            proxy_config_id=proxy_config_id,
        )
        conn = self.registry.lookup(node_id)
        if conn is not None:
            frame = pb.NodeDownstreamFrame(
                created_at=crypto.rfc3339nano(crypto.utc_now())
            )
            frame.node_proxy_config.CopyFrom(snapshot)
            try:
                conn.send(frame)
            except ConnectionError as exc:
                logger.debug(
                    "[nodeserver] node proxy config push to {} failed: {}",
                    node_id,
                    exc,
                )
        return snapshot

    async def set_node_last_proxy(
        self, req: "pb.SetNodeLastProxyRequest"
    ) -> "pb.SetNodeLastProxyResponse":
        """Record the proxy used by a node's last *successful* upgrade.

        Called by the upgrade path only after the upgrade RPC returns success,
        so a failed dispatch never overwrites the remembered good proxy. No
        validation here (the proxy id was already validated when the upgrade
        target was built); just persist.
        """
        node_id = (req.node_id or "").strip()
        proxy_config_id = (req.proxy_config_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        try:
            await self.store.set_node_last_proxy(node_id, proxy_config_id)
        except NodeNotFound as exc:
            raise RPCError(Code.NOT_FOUND, str(exc)) from exc
        return pb.SetNodeLastProxyResponse(
            node_id=node_id, last_proxy_config_id=proxy_config_id
        )

    async def get_public_ip_lookup_config(
        self, _req: "pb.GetPublicIPLookupConfigRequest"
    ) -> "pb.NodePublicIPLookupConfig":
        return _public_ip_config_proto(await self.store.get_public_ip_lookup_config())

    async def update_public_ip_lookup_config(
        self, req: "pb.UpdatePublicIPLookupConfigRequest"
    ) -> "pb.NodePublicIPLookupConfig":
        try:
            config = await self.store.update_public_ip_lookup_config(
                list(req.ipv4_urls), list(req.ipv6_urls)
            )
        except ValueError as exc:
            raise RPCError(Code.INVALID_ARGUMENT, str(exc)) from exc
        snapshot = _public_ip_config_proto(config)
        for node_id in self.registry.list():
            conn = self.registry.lookup(node_id)
            if conn is None:
                continue
            frame = pb.NodeDownstreamFrame(created_at=crypto.rfc3339nano(crypto.utc_now()))
            frame.public_ip_lookup_config.CopyFrom(snapshot)
            try:
                conn.send(frame)
            except ConnectionError as exc:
                logger.debug("[nodeserver] public-ip config broadcast to {} failed: {}", node_id, exc)
        return snapshot

    # ── NodeInfo projection (mirror node.go nodeInfo) ──────────────────────────
    def node_info(self, record: NodeRecord) -> "pb.NodeInfo":
        info = pb.NodeInfo(
            node_id=record.id,
            node_name=record.name,
            status=status_to_proto(record.status),
            role=role_to_proto(record.role),
            startup_method=startup_to_proto(record.startup_method),
            manager_node_id=record.manager_node_id,
        )
        # Reconstruct advertised capabilities from the stored label map so
        # listings surface os/arch/docker/providers.
        caps = record.capabilities or {}
        pb_caps = pb.NodeCapabilities(os=caps.get("os", ""), arch=caps.get("arch", ""))
        if caps.get("docker") == "true":
            pb_caps.docker = True
        providers = caps.get("providers", "")
        if providers:
            pb_caps.providers.extend([p for p in providers.split(",") if p])
        for k, v in caps.items():
            if k not in ("os", "arch", "docker", "providers", "editors_json"):
                pb_caps.labels[k] = v
        editors_json = caps.get("editors_json", "")
        if editors_json:
            try:
                for editor in json.loads(editors_json):
                    json_format.ParseDict(
                        editor, pb_caps.editors.add(), ignore_unknown_fields=True
                    )
            except (TypeError, ValueError, json_format.ParseError, json.JSONDecodeError):
                logger.warning("invalid stored editor capability for node {}", record.id)
        info.capabilities.CopyFrom(pb_caps)

        # Per-node egress-proxy binding + last-successful-upgrade proxy, surfaced
        # so the admin node-detail page can preselect / change the binding.
        info.proxy_config_id = str(getattr(record, "proxy_config_id", "") or "")
        info.last_proxy_config_id = str(
            getattr(record, "last_proxy_config_id", "") or ""
        )

        if record.last_seen_at is not None:
            info.last_heartbeat_at = crypto.rfc3339nano(_aware(record.last_seen_at))

        # Passive manager: online without a live connection.
        if _is_passive_manager(record):
            info.online = True
            return info

        conn = self.registry.lookup(record.id)
        if conn is not None:
            info.connected = True
            info.active_session_ids.extend(conn.active_sessions())
            if conn.connected_at is not None:
                info.connected_at = crypto.rfc3339nano(conn.connected_at)
            info.online = _connection_live(conn)
            # Prefer the address of the CURRENTLY-LIVE connection over any value
            # persisted to labels at register time: a node connected before the
            # persisted-label code shipped still gets its address surfaced, and a
            # reconnect from a new address is reflected without waiting for the
            # label to be rewritten.
            peer = (getattr(conn, "peer_address", "") or "").strip()
            if peer:
                info.capabilities.labels["server_seen_address"] = peer
        return info

    # ── NodeConnect auth (mirror node.go authenticateRegistration) ─────────────
    async def authenticate_registration(
        self, register: "pb.NodeRegister", server_time, *, peer_address: str = ""
    ) -> NodeRecord:
        """Validate the register frame's TOTP against the node's stored secret;
        return the (refreshed) ledger record. Raises RPCError (PermissionDenied
        for any auth failure, indistinguishable, to avoid leaking node ids).

        ``peer_address`` is the node's address as seen by the server (proxy-aware,
        computed in the ASGI layer); it is folded into the stored capability
        labels as ``server_seen_address`` so the console can show where the node
        connected from, distinct from the node's self-reported internal/public IP."""
        node_id = (register.node_id or "").strip()
        if not node_id:
            raise RPCError(Code.PERMISSION_DENIED, "node_id is required")
        code = (register.totp_code or "").strip()
        if not code:
            raise RPCError(Code.PERMISSION_DENIED, "totp code is required")

        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            # Unknown id — do not distinguish from a bad code.
            raise RPCError(Code.PERMISSION_DENIED, "node authentication failed")
        if record.status == NODE_STATUS_REVOKED:
            raise RPCError(Code.PERMISSION_DENIED, f"node {record.id} is revoked")
        if not (record.credential_secret_enc or "").strip():
            raise RPCError(Code.PERMISSION_DENIED, "node authentication failed")

        try:
            secret_b32 = self.secrets.open(record.credential_secret_enc)
            secret = crypto.decode_secret(secret_b32.decode("ascii"))
        except Exception as exc:  # noqa: BLE001
            raise RPCError(Code.INTERNAL, f"open node credential: {exc}")

        if not crypto.validate(secret, code, server_time, self.replay, record.id):
            raise RPCError(Code.PERMISSION_DENIED, "node authentication failed")

        # Authenticated: fold in self-reported name/platform/capabilities while
        # pinning role/manager/status/secret to the stored (authoritative) values.
        updated = self._refreshed_record(record, register, peer_address=peer_address)
        return await self.store.upsert_node(updated)

    def _refreshed_record(
        self, record: NodeRecord, register: "pb.NodeRegister", *, peer_address: str = ""
    ) -> NodeRecord:
        caps = register.capabilities if register.HasField("capabilities") else None
        # 入驻时管理员填的节点名是权威值,不得被节点自报的 hostname 覆盖;仅当入驻
        # 时未填名字才回退到节点自报名。自报名(实际就是机器 hostname)另存一份到
        # 前端列表「机器信息」列用,不再顶掉管理员命名。
        self_reported = (register.node_name or "").strip()
        name = record.name or self_reported or record.id
        labels = _capability_labels(caps)
        if record.role:
            labels["role"] = record.role
        if self_reported and self_reported != name:
            labels["hostname"] = self_reported
        # 节点自报的 internal_ip / public_ip 已随 caps.labels 复制进 labels（见
        # _capability_labels）。这里再补一个服务端视角的对端地址：与自报 IP 区分，
        # 供控制台核对两者是否一致（NAT/端口转发场景可能不同）。
        if peer_address:
            labels["server_seen_address"] = peer_address
        return NodeRecord(
            id=record.id,
            name=name,
            status=record.status,
            role=record.role,
            startup_method=record.startup_method,
            manager_node_id=record.manager_node_id,
            credential_secret_enc=record.credential_secret_enc,
            platform=_capability_platform(caps),
            capabilities=labels,
            last_seen_at=crypto.utc_now().replace(tzinfo=None),
        )

    async def handle_upstream(self, node_id: str, conn: Connection, frame: "pb.NodeUpstreamFrame") -> None:
        """Route one upstream frame from the node (mirror node.go handleUpstream)."""
        which = frame.WhichOneof("frame")
        if which == "heartbeat":
            heartbeat = frame.heartbeat
            try:
                if heartbeat.HasField("public_ip_report"):
                    report = heartbeat.public_ip_report
                    ipv4 = _validated_report_ip(report.ipv4, version=4)
                    ipv6 = _validated_report_ip(report.ipv6, version=6)
                    await self.store.patch_node_public_ip_report(
                        node_id,
                        ipv4=ipv4 or None,
                        ipv6=ipv6 or None,
                        clear_ipv4=bool(report.ipv4_disabled),
                        clear_ipv6=bool(report.ipv6_disabled),
                        config_revision=int(report.config_revision or 0),
                        ipv4_resolved_at=(report.ipv4_resolved_at or "").strip(),
                        ipv6_resolved_at=(report.ipv6_resolved_at or "").strip(),
                    )
                else:
                    await self.store.touch_node_last_seen(node_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[nodeserver] update heartbeat {} failed: {}", node_id, exc)
            conn.note_heartbeat(list(heartbeat.active_session_ids))
            conn.note_active_terminal_ids(list(heartbeat.active_terminal_ids))
            conn.note_active_tool_runs(list(heartbeat.active_tool_runs))
            if self.registry.on_tool_runs is not None:
                try:
                    self.registry.on_tool_runs(node_id, conn.active_tool_runs())
                except Exception:  # noqa: BLE001
                    pass
        elif which == "session_output":
            conn.deliver_output(frame.session_output)
        elif which == "session_result":
            result = frame.session_result
            conn.deliver_result(result)
            # Persist the task's terminal state here, at the single choke point
            # every result frame passes through — independent of whether a
            # FollowNodeSession subscriber is attached. Without this, a session
            # that ends with no live SSE follower (e.g. an instant exit-1 from a
            # missing runtime) would leave mc_tasks.status stuck at processing.
            # Idempotent with the gateway's task_events finalize; best-effort.
            from .task_finalize import finalize_task_for_session

            # The node's own error string is often just "exit status 1"; the
            # actual cause was printed to the provider's stderr. Pass the
            # retained tail so the stored reason names the real failure.
            await finalize_task_for_session(
                result.session_id,
                success=bool(result.success),
                exit_code=int(result.exit_code),
                error=result.error or "",
                stderr_tail=conn.stderr_tail(result.session_id),
            )
            conn.forget_stderr(result.session_id)
        elif which == "session_stage":
            # Per-step bring-up progress. Recorded here (not only fanned out to a
            # live follower) because the value is precisely in the no-subscriber
            # case: a session that dies during preparation must still leave a
            # trail naming the step that broke.
            from .task_stage import record_session_stage

            stage = frame.session_stage
            # Store the enum's *name*, not its number: the number is meaningless
            # in a DB row and would silently shift if the proto were renumbered.
            # Name() raises on a value this build does not know, which a newer
            # node can legitimately send — fall back to the number so an unknown
            # stage is still recorded instead of breaking the frame loop.
            try:
                stage_name = pb.SessionStage.Name(stage.stage)
            except ValueError:
                stage_name = f"SESSION_STAGE_{int(stage.stage)}"
            await record_session_stage(
                stage.session_id,
                stage_name=stage_name,
                ok=bool(stage.ok),
                detail=stage.detail or "",
                error=stage.error or "",
            )
        elif which == "session_event":
            event = frame.session_event
            conn.deliver_structured(event)
            # Persist structured runtime events at the control-plane choke point,
            # independently of whether a browser is following the SSE stream.
            from .task_event_log import record_session_event

            await record_session_event(
                event.session_id,
                seq=int(event.seq),
                event_type=event.event_type or "",
                item_type=event.item_type or "",
                agent_id=event.agent_id or "",
                payload_json=event.payload_json or "",
                logical_event_id=event.logical_event_id or "",
                event_kind=event.event_kind or "",
                tool_name=event.tool_name or "",
                subagent_id=event.subagent_id or "",
                phase=event.phase or "",
                status=event.status or "",
            )
            # Message delivery-status events (input_status / agent_turn_*) advance
            # the user_message row's state machine here too — the SSE follower is
            # not always attached, same rationale as task_finalize.
            if (event.event_type or "") in (
                "input_status", "agent_turn_started", "agent_turn_completed",
            ):
                from .task_message_status import record_message_status

                await record_message_status(
                    event.session_id,
                    event.event_type or "",
                    event.payload_json or "",
                )
            # Runtime error frames (provider 429, upstream 5xx, agent crash) are
            # turn-level signals: the runtime process often stays up (so
            # task_finalize never fires and mc_tasks.status stays processing) yet
            # the turn is dead — delivery_status would otherwise stick at
            # received/running and the UI keeps showing "Agent 正在处理" for a
            # failed turn. Close out the session's in-flight message rows.
            # Sub-agent errors don't end the root turn, so only root-scoped
            # frames qualify (subagent_id empty).
            elif (event.event_type or "") == "error" and not (event.subagent_id or ""):
                from .task_message_status import (
                    error_message_id_from_payload,
                    error_reason_from_payload,
                    fail_inflight_messages,
                )

                # The error frame carries the failing message's id when the runtime knew
                # which turn failed (payload-embedded scheme). With it, fail_inflight
                # marks just that one message and recovers the from-state for the history
                # row; without it (parse failure / outer fallback, no message context) it
                # falls back to closing out every in-flight message of the session.
                payload = event.payload_json or ""
                await fail_inflight_messages(
                    event.session_id,
                    error_reason_from_payload(payload),
                    client_message_id=error_message_id_from_payload(payload) or None,
                )
        elif which == "command_ack":
            conn.deliver_ack(frame.command_ack)
        elif which == "host_exec_result":
            conn.deliver_host_exec(frame.host_exec_result)
        elif which == "file_upload_result":
            conn.deliver_file_upload(frame.file_upload_result)
        elif which == "tunnel_response":
            conn.deliver_tunnel_response(frame.tunnel_response)
        elif which == "terminal_output":
            conn.deliver_terminal_frame(frame.terminal_output.terminal_id, frame.terminal_output)
        elif which == "terminal_exit":
            conn.deliver_terminal_frame(frame.terminal_exit.terminal_id, frame.terminal_exit)
        elif which == "terminal_list_result":
            conn.deliver_terminal_list(frame.terminal_list_result)
        elif which == "tool_run_event":
            conn.deliver_tool_run_event(frame.tool_run_event)
        elif which == "ios_devices_report":
            conn.note_ios_inventory(frame.ios_devices_report)
        elif which == "ios_job_event":
            conn.deliver_ios_job_event(frame.ios_job_event)
            conn.update_ios_job_snapshot_event(frame.ios_job_event)
        elif which == "ios_job_result":
            conn.deliver_ios_job_result(frame.ios_job_result)
        elif which == "node_build_event":
            conn.deliver_build_event(frame.node_build_event)
            conn.update_build_snapshot_event(frame.node_build_event)
        elif which == "node_build_result":
            conn.deliver_build_result(frame.node_build_result)
        elif which == "error":
            conn.note_error(frame.error.code, frame.error.message)

    # ── ListNodes / Approve / Revoke / Delete ──────────────────────────────────
    async def list_nodes(self, req: "pb.ListNodesRequest") -> "pb.ListNodesResponse":
        status = status_from_proto(req.status)
        records = await self.store.list_nodes(status=status)
        resp = pb.ListNodesResponse()
        for record in records:
            resp.nodes.append(self.node_info(record))
        return resp

    async def approve_node(self, req: "pb.ApproveNodeRequest") -> "pb.ApproveNodeResponse":
        node_id = (req.node_id or "").strip()
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if not _is_passive_manager(record):
            caps = record.capabilities or {}
            missing: list[str] = []
            if not (caps.get("node_version") or "").strip():
                missing.append("Node.js")
            if not (caps.get("npm_version") or "").strip():
                missing.append("npm")
            if not (caps.get("runtime_version") or "").strip():
                missing.append("agent-compose runtime")
            if not (caps.get("providers") or "").strip():
                missing.append("至少一个编辑器客户端")
            if missing:
                raise RPCError(
                    Code.FAILED_PRECONDITION,
                    "节点基础环境未完成：" + "、".join(missing),
                )
        try:
            await self.store.set_node_status(node_id, NODE_STATUS_APPROVED)
        except NodeNotFound as exc:
            raise RPCError(Code.NOT_FOUND, str(exc))
        record = await self.store.get_node_if_exists(node_id)
        resp = pb.ApproveNodeResponse()
        if record is not None:
            resp.node.CopyFrom(self.node_info(record))
        return resp

    async def revoke_node(self, req: "pb.RevokeNodeRequest") -> "pb.RevokeNodeResponse":
        node_id = (req.node_id or "").strip()
        try:
            await self.store.set_node_status(node_id, NODE_STATUS_REVOKED)
        except NodeNotFound as exc:
            raise RPCError(Code.NOT_FOUND, str(exc))
        # Drop any live connection so the node stops receiving work immediately.
        self.registry.disconnect(node_id)
        record = await self.store.get_node_if_exists(node_id)
        resp = pb.RevokeNodeResponse()
        if record is not None:
            resp.node.CopyFrom(self.node_info(record))
        return resp

    async def move_node(self, node_id: str, manager_node_id: str) -> "NodeRecord":
        """把执行节点挪到另一个管理节点下。管理节点本身不可移动。
        直接接受纯字符串,避免为这一处单独生成 proto 消息。"""
        node_id = (node_id or "").strip()
        manager_node_id = (manager_node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        if not manager_node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "manager_node_id is required")
        try:
            await self.store.set_node_manager(node_id, manager_node_id)
        except NodeNotFound as exc:
            raise RPCError(Code.NOT_FOUND, str(exc))
        except ValueError as exc:
            raise RPCError(Code.FAILED_PRECONDITION, str(exc))
        return await self.store.get_node(node_id)

    async def delete_node(self, req: "pb.DeleteNodeRequest") -> "pb.DeleteNodeResponse":
        node_id = (req.node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            return pb.DeleteNodeResponse(deleted=False)  # idempotent

        # A management node still owning execution nodes is always refused.
        if _is_manager_role(record.role):
            owned = await self.store.list_nodes()
            count = sum(1 for n in owned if n.manager_node_id == node_id)
            if count > 0:
                raise RPCError(
                    Code.FAILED_PRECONDITION,
                    f"management node {node_id} still owns {count} execution node(s); "
                    "delete or reassign them first",
                )
        # An online node is refused without force.
        if self.registry.lookup(node_id) is not None and not req.force:
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} is online; retry with force to delete it anyway",
            )
        try:
            await self.store.delete_node(node_id)
        except NodeNotFound as exc:
            raise RPCError(Code.NOT_FOUND, str(exc))
        self.registry.disconnect(node_id)
        return pb.DeleteNodeResponse(deleted=True)

    # ── OnboardNode / RevokeOnboardNode ─────────────────────────────────────────
    async def onboard_node(self, req: "pb.OnboardNodeRequest") -> "pb.OnboardNodeResponse":
        role = role_from_proto(req.role) or NODE_ROLE_EXECUTION
        node_id = "node-" + str(uuid.uuid4())
        name = (req.node_name or "").strip() or node_id
        labels = {k.strip(): v for k, v in req.labels.items() if k.strip()}
        proxy_config_id = (req.proxy_config_id or "").strip()

        # Validate the egress-proxy binding up front: reject ``node``-mode and
        # unknown pool-entry ids BEFORE minting a secret or creating the row, so a
        # bad onboard fails fast with no cleanup. Passive management never
        # downloads, so it skips this (and the binding is not stored for it).
        if role != NODE_ROLE_PASSIVE_MANAGEMENT and proxy_config_id:
            await _resolve_node_proxy_fields(proxy_config_id)

        # Passive management role → pure grouping container. No credential, no
        # client, approved immediately: it only groups execution nodes for
        # per-group authorization; nothing ever installs or dials in for it.
        if role == NODE_ROLE_PASSIVE_MANAGEMENT:
            labels["role"] = NODE_ROLE_PASSIVE_MANAGEMENT
            record = await self.store.upsert_node(
                NodeRecord(
                    id=node_id,
                    name=name,
                    status=NODE_STATUS_APPROVED,
                    role=NODE_ROLE_PASSIVE_MANAGEMENT,
                    capabilities=labels,
                )
            )
            resp = pb.OnboardNodeResponse(node_id=record.id)
            resp.node.CopyFrom(self.node_info(record))
            return resp

        # Management (with client) role → a real client that both groups
        # execution nodes AND dials in to launch them on its host. It mints a
        # credential and install command exactly like an execution node, but has
        # no owning manager of its own (it is the owner) and no launch dispatch.
        if role == NODE_ROLE_MANAGEMENT:
            method = startup_from_proto(req.startup_method) or NODE_STARTUP_DOCKER
            labels["role"] = NODE_ROLE_MANAGEMENT
            return await self._mint_credentialed_node(
                node_id=node_id,
                name=name,
                role=NODE_ROLE_MANAGEMENT,
                method=method,
                manager_id="",
                labels=labels,
                proxy_config_id=proxy_config_id,
            )

        # iOS host role → a real client that dials in for identity/heartbeat/
        # version-report/self-upgrade only. It runs no sessions and launches
        # nothing, so it mints a credential like management but has no owning
        # manager and no launch dispatch. Its paired iPhones are driven over a
        # separate device-control WebSocket, disjoint from this control plane.
        if role == NODE_ROLE_IOS_HOST:
            method = startup_from_proto(req.startup_method) or NODE_STARTUP_STANDALONE
            labels["role"] = NODE_ROLE_IOS_HOST
            return await self._mint_credentialed_node(
                node_id=node_id,
                name=name,
                role=NODE_ROLE_IOS_HOST,
                method=method,
                manager_id="",
                labels=labels,
                proxy_config_id=proxy_config_id,
            )

        # Execution role → pending record + minted TOTP secret, owned by a
        # management node (either kind) which may launch it.
        method = startup_from_proto(req.startup_method) or NODE_STARTUP_STANDALONE
        labels["role"] = role
        manager_id = await self._resolve_manager((req.manager_node_id or "").strip())
        resp = await self._mint_credentialed_node(
            node_id=node_id,
            name=name,
            role=role,
            method=method,
            manager_id=manager_id,
            labels=labels,
            proxy_config_id=proxy_config_id,
        )
        # Ask the (connected, non-passive) owning manager to launch it, if any.
        launched = await self._dispatch_create_execution_node(
            manager_id, await self.store.get_node(node_id), method, resp.secret
        )
        if launched:
            resp.launched = True
        return resp

    async def _mint_credentialed_node(
        self,
        *,
        node_id: str,
        name: str,
        role: str,
        method: str,
        manager_id: str,
        labels: dict,
        proxy_config_id: str = "",
    ) -> "pb.OnboardNodeResponse":
        """Create a pending node with a freshly minted TOTP secret + install
        command. Shared by the execution role and the management-with-client
        role: both are real clients that download the agent binary and dial in.
        The admin's chosen egress-proxy binding (``proxy_config_id``) is
        persisted on the row so the install script (baked from the bootstrap
        record) and the connect-time NodeProxyConfig push use the same proxy.
        """
        secret_b32 = crypto.generate_secret()
        try:
            sealed = self.secrets.seal(secret_b32.encode("ascii"))
        except Exception as exc:  # noqa: BLE001
            raise RPCError(Code.INTERNAL, f"seal node credential: {exc}")

        record = await self.store.upsert_node(
            NodeRecord(
                id=node_id,
                name=name,
                status=NODE_STATUS_PENDING,
                role=role,
                startup_method=method,
                manager_node_id=manager_id,
                credential_secret_enc=sealed,
                capabilities=labels,
                proxy_config_id=proxy_config_id,
            )
        )

        script_url = self.script_url(role, method)
        resp = pb.OnboardNodeResponse(
            node_id=record.id,
            secret=secret_b32,
            script_url=script_url,
            install_command=_install_command(script_url, record.id, secret_b32),
            launched=False,
            otpauth_uri=crypto.otpauth_uri(secret_b32, name),
        )
        resp.node.CopyFrom(self.node_info(record))
        return resp

    async def _resolve_manager(self, manager_id: str) -> str:
        if not manager_id:
            raise RPCError(
                Code.INVALID_ARGUMENT,
                "manager_node_id is required for an execution node: onboard a "
                "management node first and pass its id",
            )
        record = await self.store.get_node_if_exists(manager_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"manager node {manager_id} not found")
        if not _is_manager_role(record.role):
            raise RPCError(Code.FAILED_PRECONDITION, f"node {manager_id} is not a management node")
        return manager_id

    async def _dispatch_create_execution_node(
        self, manager_id: str, record: NodeRecord, method: str, secret_b32: str
    ) -> bool:
        """Ask a connected management node to launch this execution node. Best-
        effort: returns False if the manager is passive/offline/does not ack ok."""
        manager = await self.store.get_node_if_exists(manager_id)
        if manager is None or manager.status != NODE_STATUS_APPROVED:
            return False
        if _is_passive_manager(manager):
            return False
        conn = self.registry.lookup(manager_id)
        if conn is None:
            return False
        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.create_execution_node.CopyFrom(
            pb.NodeCreateExecutionNode(
                launch_id=record.id,
                server_url=self.server_url,
                node_id=record.id,
                secret=secret_b32,
                startup_method=startup_to_proto(method),
                node_name=record.name,
                guest_image=str((record.capabilities or {}).get("guest_image") or ""),
            )
        )
        try:
            conn.send(frame)
        except Exception:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            return False
        try:
            ack = await asyncio.wait_for(ack_future, timeout=DISPATCH_ACK_TIMEOUT)
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            conn.cancel_ack(frame_id)
            return False
        return ack is not None and ack.ok

    # ── ManageEditor (install/upgrade an editor CLI on an execution node) ───────
    async def manage_editor(self, node_id: str, editor: str, action: str) -> dict:
        """Ask a connected node to install/upgrade one editor CLI.

        Waits for the node's ack (a global npm install takes far longer than a
        session dispatch, hence the dedicated timeout) and, on success, folds the
        reported version back into the node's stored capability labels so the
        console reflects it without waiting for a re-register.
        """
        node_id = (node_id or "").strip()
        name = (editor or "").strip().lower()
        verb = (action or "").strip().lower()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        if name not in SUPPORTED_MANAGED_TOOLS:
            raise RPCError(
                Code.INVALID_ARGUMENT,
                f"unsupported managed tool {editor!r}; supported: {', '.join(SUPPORTED_MANAGED_TOOLS)}",
            )
        if verb not in ("install", "upgrade"):
            raise RPCError(Code.INVALID_ARGUMENT, "action must be install or upgrade")

        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if _is_passive_manager(record):
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} is a grouping container with no client; nothing to install on",
            )
        conn = self.registry.lookup(node_id)
        if conn is None:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is offline")

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.manage_editor.CopyFrom(
            pb.NodeManageEditor(
                editor=name,
                action=(
                    pb.EditorAction.EDITOR_ACTION_UPGRADE
                    if verb == "upgrade"
                    else pb.EditorAction.EDITOR_ACTION_INSTALL
                ),
            )
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=EDITOR_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not finish {verb} of {name} within "
                f"{int(EDITOR_ACK_TIMEOUT)}s; it may still be running",
            )
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"{verb} {name} on {node_id} failed: {message}")

        version = (ack.editor_version or "").strip()
        if version:
            await self._store_editor_version(node_id, name, version)
        return {"node_id": node_id, "editor": name, "action": verb, "version": version}

    async def _store_editor_version(self, node_id: str, editor: str, version: str) -> None:
        """Persist an editor version label so listings/detail refresh immediately."""
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            return
        labels = dict(record.capabilities or {})
        key = "ocr_version" if editor == "ocr" else f"editor_version_{editor}"
        labels[key] = version
        record.capabilities = labels
        try:
            await self.store.upsert_node(record)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[nodeserver] persist editor version failed {}: {}", node_id, exc)

    # ── NodeEnvironment (provision / sync / inspect a shared environment) ───────
    # The user-facing ledger (which environments exist, their resource sets) lives
    # in the data service (monkeycode_compat.models_environment). node_server is a
    # stateless relay: it pushes create/remove/sync frames to the node and reports
    # back the node's on-disk inventory. It owns no environment rows.
    async def _require_online_execution(self, node_id: str) -> "Connection":
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if _is_passive_manager(record):
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} is a grouping container with no client; no host to place an environment on",
            )
        conn = self.registry.lookup(node_id)
        if conn is None:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is offline")
        return conn

    async def manage_environment(self, node_id: str, env_id: str, action: str) -> dict:
        """Create or remove one shared-environment directory on a connected node.

        CREATE is idempotent (leaves an existing env intact); REMOVE deletes the
        tree to reclaim disk. Ledger bookkeeping is the data service's job — this
        just pushes the frame and waits for the node ack.
        """
        env_id = (env_id or "").strip()
        verb = (action or "").strip().lower()
        if not env_id:
            raise RPCError(Code.INVALID_ARGUMENT, "env_id is required")
        if verb not in ("create", "remove"):
            raise RPCError(Code.INVALID_ARGUMENT, "action must be create or remove")
        conn = await self._require_online_execution(node_id)

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.manage_environment.CopyFrom(
            pb.NodeManageEnvironment(
                env_id=env_id,
                action=(
                    pb.EnvironmentAction.ENVIRONMENT_ACTION_REMOVE
                    if verb == "remove"
                    else pb.EnvironmentAction.ENVIRONMENT_ACTION_CREATE
                ),
            )
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=ENVIRONMENT_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not finish {verb} of environment {env_id} in time",
            )
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"{verb} environment {env_id} on {node_id} failed: {message}")
        return {"node_id": node_id, "env_id": env_id, "action": verb, "ok": True}

    async def sync_environment(
        self, node_id: str, env_id: str, skills: list[dict], plugins: list[dict]
    ) -> dict:
        """Install the exact desired skill/plugin set into an environment HOME.

        Skills/plugins are files; the node writes them under the env HOME's
        ``.agents`` tree (exact-set: extras from a previous sync are pruned, but
        NOT things installed by hand — those live outside the managed set). MCP is
        never synced here: it is config resolved per task, never materialized into
        a shared HOME. Wire specs are the same shapes DispatchSession uses.
        """
        env_id = (env_id or "").strip()
        if not env_id:
            raise RPCError(Code.INVALID_ARGUMENT, "env_id is required")
        conn = await self._require_online_execution(node_id)

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        sync = pb.NodeSyncEnvironment(env_id=env_id)
        for item in skills or []:
            sync.skills.append(_skill_spec_from_dict(item))
        for item in plugins or []:
            sync.plugins.append(_plugin_spec_from_dict(item))
        frame.sync_environment.CopyFrom(sync)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=EDITOR_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not finish syncing environment {env_id} in time",
            )
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"sync environment {env_id} on {node_id} failed: {message}")
        return {"node_id": node_id, "env_id": env_id, "ok": True}

    async def inspect_environment(self, node_id: str, env_id: str) -> dict:
        """Ask a node what is physically installed in an environment HOME.

        Returns the observed skill/plugin inventory (names + versions) so the
        data service can diff it against the desired resource set and show
        已安装 / 待安装 / 多余. Never includes MCP (not a file on disk).
        """
        env_id = (env_id or "").strip()
        if not env_id:
            raise RPCError(Code.INVALID_ARGUMENT, "env_id is required")
        conn = await self._require_online_execution(node_id)

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.inspect_environment.CopyFrom(pb.NodeInspectEnvironment(env_id=env_id))
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=ENVIRONMENT_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not report environment {env_id} inventory in time",
            )
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"inspect environment {env_id} on {node_id} failed: {message}")
        installed = [
            {"kind": item.kind, "name": item.name, "version": item.version}
            for item in ack.environment_inventory
        ]
        return {"node_id": node_id, "env_id": env_id, "installed": installed}

    # ── System environment (the node operator's real HOME) ────────────────────────
    def _system_env_entry(self, item) -> dict:
        """Project one NodeSystemEnvEntry proto onto the wire dict the data service
        consumes. Kept in one place so inspect and sync acks shape identically."""
        return {
            "kind": item.kind,
            "name": item.name,
            "version": item.version,
            "provider": item.provider,
            "path": item.path,
            "platform_managed": bool(item.platform_managed),
        }

    async def inspect_system_env(self, node_id: str, provider: str = "") -> dict:
        """Ask a node what the providers would discover in the operator's real HOME.

        Returns the observed skill/plugin/MCP inventory so the console can finally
        SHOW what a system-env session actually gets — today it is invisible.
        Read-only; the node never writes its operator's home on this path.
        """
        conn = await self._require_online_execution(node_id)

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.inspect_system_env.CopyFrom(
            pb.NodeInspectSystemEnv(provider=(provider or "").strip())
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=ENVIRONMENT_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not report system environment inventory in time",
            )
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"inspect system env on {node_id} failed: {message}")
        return {
            "node_id": node_id,
            "installed": [self._system_env_entry(item) for item in ack.system_env_inventory],
        }

    async def sync_system_env(
        self,
        node_id: str,
        skills: list,
        plugins: list,
        overwrite: bool = False,
        remove: list | None = None,
    ) -> dict:
        """Install platform resources into the operator's real HOME, incrementally.

        Never an exact-set sync: absent entries are untouched, existing ones are
        skipped unless ``overwrite``, and ``remove`` only accepts names the node
        itself installed (manifest-tracked), so the operator's own resources
        cannot be deleted through this path. Real downloads — long ack timeout.
        """
        conn = await self._require_online_execution(node_id)

        sync = pb.NodeSyncSystemEnv(overwrite=bool(overwrite))
        for item in skills or []:
            sync.skills.append(_skill_spec_from_dict(item))
        for item in plugins or []:
            sync.plugins.append(_plugin_spec_from_dict(item))
        for target in remove or []:
            sync.remove.append(str(target))

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.sync_system_env.CopyFrom(sync)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=EDITOR_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not ack system environment sync in time",
            )
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"sync system env on {node_id} failed: {message}")
        return {
            "node_id": node_id,
            "ok": True,
            "touched": [self._system_env_entry(item) for item in ack.system_env_inventory],
        }

    async def archive_system_env_resource(
        self, node_id: str, kind: str, name: str, upload_url: str, upload_token: str
    ) -> dict:
        """Tar one resource out of the operator's HOME and upload it to the server.

        The node does the packing and the HTTP POST; this frame only tells it which
        resource and where to send it. Used to archive a locally installed
        skill/plugin into the platform library for reuse on other nodes.
        """
        conn = await self._require_online_execution(node_id)

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.archive_system_env_resource.CopyFrom(
            pb.NodeArchiveSystemEnvResource(
                kind=(kind or "").strip(),
                name=(name or "").strip(),
                upload_url=(upload_url or "").strip(),
                upload_token=(upload_token or "").strip(),
            )
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=EDITOR_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not ack system environment archive in time",
            )
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"archive system env on {node_id} failed: {message}")
        return {"node_id": node_id, "kind": kind, "name": name, "ok": True}

    # ── iOS device management (role ios_host) ───────────────────────────────────
    # Discovery, claim, release, configure, and WDA job dispatch for iOS control
    # nodes. A node must have role=ios_host, be online, and carry the ios_mgmt=true
    # capability label. Claim/release/configure wait for an ack; WDA job dispatch
    # returns immediately (the job result is tracked separately in Stage 3).

    IOS_CLAIM_ACK_TIMEOUT = 30.0  # claim → pair → device-control WS register
    IOS_RELEASE_ACK_TIMEOUT = 10.0  # tear down goroutine + optional credential delete
    IOS_CONFIGURE_ACK_TIMEOUT = 10.0  # revision check + config merge
    IOS_WDA_JOB_ACK_TIMEOUT = 5.0  # job accepted (not completed; job sends result separately)

    async def _require_online_ios_host(self, node_id: str) -> Connection:
        """Guard: node must be online, role=ios_host, and carry ios_mgmt=true."""
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if record.role != NODE_ROLE_IOS_HOST:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is not an iOS host node")
        conn = self.registry.lookup(node_id)
        if conn is None:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is offline")
        caps = record.capabilities or {}
        if caps.get("ios_mgmt") != "true":
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} does not support iOS management (upgrade node-ios to the latest version)",
            )
        return conn

    async def ios_discover(self, node_id: str) -> dict:
        """Request one ios_host to enumerate its attached devices.

        The node streams a NodeIosDevicesReport back unsolicited; this frame just
        triggers a fresh snapshot. Used by the management console when the user
        clicks "Scan Devices" or when the host reconnects.
        """
        conn = await self._require_online_ios_host(node_id)
        request_id = str(uuid.uuid4())
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.ios_discover.CopyFrom(pb.NodeIosDiscover(request_id=request_id))
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            raise RPCError(Code.UNAVAILABLE, f"send discover to node {node_id} failed: {exc}")
        return {"node_id": node_id, "request_id": request_id}

    async def ios_claim_device(
        self, node_id: str, udid: str, device_label: str, pairing_code: str
    ) -> dict:
        """Dispatch a claim frame carrying a one-time pairing code.

        The node redeems the code at POST /device-control/pair (the same endpoint
        the Android app uses) and starts a device-control goroutine for that device.
        """
        conn = await self._require_online_ios_host(node_id)
        udid = (udid or "").strip()
        if not udid:
            raise RPCError(Code.INVALID_ARGUMENT, "udid is required")
        if not pairing_code:
            raise RPCError(Code.INVALID_ARGUMENT, "pairing_code is required")

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.ios_claim_device.CopyFrom(
            pb.NodeIosClaimDevice(
                request_id=frame_id,
                udid=udid,
                device_label=(device_label or "").strip(),
                pairing_code=pairing_code,
                server_url=self.server_url,
                # transport/wda_bundle_id/xctest_config_name/config_revision are
                # set at configure time; claim only bootstraps the credential.
            )
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send claim to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=self.IOS_CLAIM_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not ack claim for {udid} in time",
            )
        except ConnectionError:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} disconnected during claim")
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"claim {udid} on {node_id} failed: {message}")
        return {"node_id": node_id, "udid": udid}

    async def ios_release_device(
        self, node_id: str, device_id: str, udid: str, *, delete_credential: bool = False
    ) -> dict:
        """Dispatch a release frame to stop the device-control goroutine.

        Optionally deletes the local credential file so the device must be
        re-paired before it can be used again (used when revoking access).
        """
        conn = await self._require_online_ios_host(node_id)
        udid = (udid or "").strip()
        if not udid:
            raise RPCError(Code.INVALID_ARGUMENT, "udid is required")

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.ios_release_device.CopyFrom(
            pb.NodeIosReleaseDevice(
                request_id=frame_id,
                device_id=(device_id or "").strip(),
                udid=udid,
                delete_credential=bool(delete_credential),
                uninstall_wda=False,  # Stage 3 optional
            )
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send release to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=self.IOS_RELEASE_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not ack release for {udid} in time",
            )
        except ConnectionError:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} disconnected during release")
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"release {udid} on {node_id} failed: {message}")
        return {"node_id": node_id, "udid": udid, "deleted_credential": delete_credential}

    async def ios_configure_device(
        self,
        node_id: str,
        device_id: str,
        udid: str,
        config_revision: int,
        *,
        transport: str = "",
        wda_bundle_id: str = "",
        xctest_config_name: str = "",
        auto_prepare: bool = False,
        renew_before_days: int = 14,
    ) -> dict:
        """Push WDA/transport configuration to a claimed device.

        The node applies it only if config_revision > last_applied_revision (the
        node guards against out-of-order delivery). Used when the user changes
        WDA settings in the device detail panel.
        """
        conn = await self._require_online_ios_host(node_id)
        udid = (udid or "").strip()
        if not udid:
            raise RPCError(Code.INVALID_ARGUMENT, "udid is required")

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.ios_configure_device.CopyFrom(
            pb.NodeIosConfigureDevice(
                request_id=frame_id,
                device_id=(device_id or "").strip(),
                udid=udid,
                config_revision=max(int(config_revision or 0), 0),
                transport=(transport or "").strip(),
                wda_bundle_id=(wda_bundle_id or "").strip(),
                xctest_config_name=(xctest_config_name or "").strip(),
                host_wda_port=0,  # dynamic allocation
                auto_prepare=bool(auto_prepare),
                renew_before_days=max(int(renew_before_days or 0), 0) or 14,
            )
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send configure to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=self.IOS_CONFIGURE_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not ack configure for {udid} in time",
            )
        except ConnectionError:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} disconnected during configure")
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"configure {udid} on {node_id} failed: {message}")
        return {"node_id": node_id, "udid": udid, "config_revision": config_revision}

    async def get_ios_devices(self, node_id: str) -> dict:
        """Retrieve the cached device inventory for one ios_host node.

        Returns the last NodeIosDevicesReport the node sent (on register / attach-
        detach / claim / WDA state change). No frame is dispatched — this is a
        pure registry read for the management console's device list.
        """
        conn = await self._require_online_ios_host(node_id)
        report = conn.ios_inventory()
        if report is None:
            # Node just connected and has not sent its first report yet.
            return {"node_id": node_id, "devices": []}
        devices = []
        for dev in report.devices:
            devices.append(
                {
                    "udid": dev.udid,
                    "name": dev.name,
                    "model": dev.model,
                    "product_version": dev.product_version,
                    "connection_type": dev.connection_type,
                    "present": dev.present,
                    "claimed": dev.claimed,
                    "device_id": dev.device_id,
                    "device_control_online": dev.device_control_online,
                    "wda_state": dev.wda_state,
                    "wda_bundle_id": dev.wda_bundle_id,
                    "profile_expires_at": dev.profile_expires_at,
                    "last_error": dev.last_error,
                    "config_revision_applied": dev.config_revision_applied,
                    "developer_mode_enabled": dev.developer_mode_enabled,
                }
            )
        return {
            "node_id": node_id,
            "snapshot_revision": report.snapshot_revision,
            "reported_at": report.reported_at,
            "devices": devices,
            "enumerate_error": report.enumerate_error,
        }

    async def ios_start_wda_job(
        self,
        node_id: str,
        job_id: str,
        udid: str,
        device_id: str,
        action: str,
        *,
        artifact: dict | None = None,
        signing_profile: dict | None = None,
        wda_bundle_id: str = "",
        xctest_config_name: str = "",
    ) -> dict:
        """Dispatch a WDA job (prepare/renew/reinstall) to an ios_host node.

        Returns immediately after the node acks receipt (not completion). The node
        streams NodeIosJobEvent frames as progress updates and sends exactly one
        NodeIosJobResult when done. The job_id is caller-provided (UUID from the
        data service) so the data side can correlate progress/result to its own
        job tracking.

        artifact: {id?, sha256, download_url, size_bytes, version}
        signing_profile: {kind: "asc"|"p12", secret_data: {...}}
        """
        conn = await self._require_online_ios_host(node_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        req = pb.NodeIosWdaJobRequest(
            job_id=job_id,
            udid=udid,
            device_id=device_id,
            action=action,
            wda_bundle_id=wda_bundle_id,
            xctest_config_name=xctest_config_name,
        )
        if artifact:
            art = req.artifact
            art.artifact_id = str(artifact.get("id") or "")
            art.sha256 = str(artifact.get("sha256") or "")
            # proto 字段名是 url（不是 download_url）
            art.url = str(artifact.get("download_url") or "")
            art.size_bytes = int(artifact.get("size_bytes") or 0)
            art.version = str(artifact.get("version") or "")
        if signing_profile:
            kind = str(signing_profile.get("kind") or "")
            secret = signing_profile.get("secret_data") or {}
            if kind == "asc":
                asc = req.signing_asc
                asc.p8_key = str(secret.get("p8_key") or "")
                asc.key_id = str(secret.get("key_id") or "")
                asc.issuer_id = str(secret.get("issuer_id") or "")
                asc.team_id = str(secret.get("team_id") or "")
            elif kind == "p12":
                p12 = req.signing_p12
                p12.p12_base64 = str(secret.get("p12_base64") or "")
                p12.p12_password = str(secret.get("p12_password") or "")
                p12.mobileprovision_base64 = str(secret.get("mobileprovision_base64") or "")
        frame.ios_wda_job.CopyFrom(req)

        # Initialize job snapshot for polling queries
        conn.init_ios_job_snapshot(job_id, device_id, udid, action)

        ack_fut = conn.await_ack(frame.server_frame_id)
        try:
            conn.send(frame)
            ack = await asyncio.wait_for(ack_fut, timeout=self.IOS_WDA_JOB_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame.server_frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"ios_start_wda_job on {node_id} timed out (job may still start)",
            ) from None
        except Exception as exc:
            conn.cancel_ack(frame.server_frame_id)
            raise RPCError(Code.INTERNAL, f"ios_start_wda_job on {node_id} failed: {exc}") from exc

        if not ack.ok:
            message = ack.error_message or "node rejected WDA job"
            raise RPCError(Code.INTERNAL, f"ios_start_wda_job on {node_id} failed: {message}")
        return {"node_id": node_id, "job_id": job_id, "udid": udid}

    async def ios_cancel_wda_job(self, node_id: str, job_id: str) -> dict:
        """Cancel a running WDA job (cooperative cancellation at stage boundaries)."""
        conn = await self._require_online_ios_host(node_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.ios_job_cancel.CopyFrom(pb.NodeIosJobCancel(job_id=job_id))
        try:
            conn.send(frame)
        except Exception as exc:
            raise RPCError(Code.INTERNAL, f"ios_cancel_wda_job on {node_id} failed: {exc}") from exc
        return {"node_id": node_id, "job_id": job_id, "cancelled": True}

    async def get_ios_wda_job_status(self, node_id: str, job_id: str) -> dict:
        """Query WDA job status from registry snapshot (polling endpoint)."""
        conn = await self._require_online_ios_host(node_id)
        snapshot = conn.get_ios_job_snapshot(job_id)
        if not snapshot:
            raise RPCError(Code.NOT_FOUND, f"job {job_id} not found or already expired")
        return snapshot

    # ── generic node builds (project-page「构建」tab; mirrors the WDA job trio) ──

    async def start_node_build(
        self,
        node_id: str,
        build_id: str,
        *,
        recipe_kind: str,
        source_url: str,
        source_ref: str = "",
        steps: list[str] | None = None,
        artifact_glob: str = "",
        upload_url: str = "",
        upload_token: str = "",
        timeout_seconds: int = 0,
        artifact_name: str = "",
        artifact_version: str = "",
    ) -> dict:
        """Dispatch a build job to a node that mounts the build runner.

        Returns immediately after the node acks receipt (not completion). The
        node streams NodeBuildEvent frames as progress and sends exactly one
        NodeBuildResult when done. The build_id is caller-provided (UUID from
        the data service) so the data side can correlate progress/result.
        """
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if _is_passive_manager(record):
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} is a grouping container with no client; nothing to build on",
            )
        conn = self.registry.lookup(node_id)
        if conn is None:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is offline")

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.node_build.CopyFrom(
            pb.NodeBuildRequest(
                build_id=build_id,
                recipe_kind=recipe_kind,
                source_url=source_url,
                source_ref=source_ref,
                steps=list(steps or []),
                artifact_glob=artifact_glob,
                upload_url=upload_url,
                upload_token=upload_token,
                timeout_seconds=int(timeout_seconds or 0),
                artifact_name=artifact_name,
                artifact_version=artifact_version,
            )
        )

        # Initialize build snapshot for polling queries (before send, like the
        # WDA job dispatch, so a fast progress event cannot race the init).
        conn.init_build_snapshot(build_id, recipe_kind, node_id)

        try:
            conn.send(frame)
            ack = await asyncio.wait_for(ack_future, timeout=self.IOS_WDA_JOB_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"start_node_build on {node_id} timed out (build may still start)",
            ) from None
        except Exception as exc:
            conn.cancel_ack(frame_id)
            raise RPCError(Code.INTERNAL, f"start_node_build on {node_id} failed: {exc}") from exc

        if not ack.ok:
            message = ack.error_message or "node rejected build job"
            raise RPCError(Code.INTERNAL, f"start_node_build on {node_id} failed: {message}")
        return {"node_id": node_id, "build_id": build_id, "status": "accepted"}

    async def get_node_build_status(self, node_id: str, build_id: str) -> dict:
        """Query build status from registry snapshot (polling endpoint)."""
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        conn = self.registry.lookup(node_id)
        if conn is None:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is offline")
        snapshot = conn.get_build_snapshot(build_id)
        if not snapshot:
            raise RPCError(Code.NOT_FOUND, f"build {build_id} not found or already expired")
        return snapshot

    async def cancel_node_build(self, node_id: str, build_id: str) -> dict:
        """Cancel a running build (cooperative cancellation at step boundaries)."""
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        conn = self.registry.lookup(node_id)
        if conn is None:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is offline")
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.node_build_cancel.CopyFrom(pb.NodeBuildCancel(build_id=build_id))
        try:
            conn.send(frame)
        except Exception as exc:
            raise RPCError(Code.INTERNAL, f"cancel_node_build on {node_id} failed: {exc}") from exc
        return {"node_id": node_id, "build_id": build_id, "cancelled": True}

    # ── RuntimeUpgrade (download JS runtime archive; no Go restart) ───────────────
    async def runtime_upgrade_node(self, node_id: str, *, target: dict | None = None) -> dict:
        """Ask the node to download and activate its JavaScript runtime.

        ``target`` is always resolved by the caller and carries the archive's
        download URL, sha256 and proxy fields. The control plane never resolves
        it itself: both the release catalogue and the proxy pool live on the
        data side, so picking an asset here would mean reaching back into it.
        """
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if _is_passive_manager(record):
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} is a grouping container with no runtime to upgrade",
            )
        conn = self.registry.lookup(node_id)
        if conn is None:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is offline")

        caps = record.capabilities or {}
        os_name = (caps.get("os") or "").strip()
        arch = (caps.get("arch") or "").strip()
        if not os_name or not arch:
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} has not reported its os/arch yet; cannot pick a runtime archive",
            )
        if not target:
            raise RPCError(
                Code.INVALID_ARGUMENT,
                "target is required: the caller must supply the runtime archive "
                "(download_url / sha256 / proxy fields)",
            )
        target_version = str(target.get("target_version") or "").strip()
        download_url = str(target.get("download_url") or "").strip()
        sha256 = str(target.get("sha256") or "").strip()
        proxy_fields: dict = {
            "proxy_mode": str(target.get("proxy_mode") or ""),
            "proxy_url": str(target.get("proxy_url") or ""),
            "proxy_url_prefix": str(target.get("proxy_url_prefix") or ""),
        }
        if not download_url:
            raise RPCError(Code.INVALID_ARGUMENT, "target.download_url is required")

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.runtime_upgrade.CopyFrom(
            pb.NodeRuntimeUpgrade(
                target_version=target_version,
                download_url=download_url,
                sha256=sha256,
                proxy_mode=proxy_fields.get("proxy_mode", ""),
                proxy_url=proxy_fields.get("proxy_url", ""),
                proxy_url_prefix=proxy_fields.get("proxy_url_prefix", ""),
            )
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=SELF_UPGRADE_ACK_TIMEOUT)
        except TimeoutError as exc:
            conn.cancel_ack(frame_id)
            raise RPCError(Code.DEADLINE_EXCEEDED, "runtime upgrade ack timed out") from exc
        if not ack.ok:
            raise RPCError(Code.INTERNAL, ack.error or "runtime upgrade failed")
        await self._store_runtime_version(node_id, target_version)
        return {
            "node_id": node_id,
            "target_version": target_version,
            "download_url": download_url,
            "sha256": sha256,
        }

    async def upgrade_node(
        self,
        node_id: str,
        *,
        runtime_target: dict | None = None,
        node_target: dict | None = None,
    ) -> dict:
        """Unified upgrade: drive RuntimeUpgrade then SelfUpgrade sequentially.

        Both targets carry a server-resolved ``node-releases/version.json`` asset
        (GitHub direct link + sha256 + proxy fields). Runtime swaps hot (no Go
        restart); the node program replaces and reconnects last — ordering matters,
        because a self-upgrade restart would abort an in-flight runtime swap.
        Either target may be ``None`` when the release only ships one of the two
        for this platform/role, in which case that step is skipped.
        """
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        if runtime_target is None and node_target is None:
            raise RPCError(
                Code.INVALID_ARGUMENT,
                "upgrade requires at least one of runtime_target / node_target",
            )
        runtime_result: dict | None = None
        if runtime_target:
            runtime_result = await self.runtime_upgrade_node(node_id, target=runtime_target)
        node_result: dict | None = None
        if node_target:
            node_result = await self.self_upgrade_node(node_id, target=node_target)
        return {
            "node_id": node_id,
            "runtime": runtime_result,
            "node": node_result,
            "accepted": True,
        }

    async def _store_runtime_version(self, node_id: str, version: str) -> None:
        record = await self.store.get_node_if_exists(node_id)
        if record is None or not version:
            return
        labels = dict(record.capabilities or {})
        labels["runtime_version"] = version
        record.capabilities = labels
        await self.store.upsert_node(record)

    # ── SelfUpgrade (download a new node binary + restart) ──────────────────────
    async def self_upgrade_node(self, node_id: str, *, target: dict | None = None) -> dict:
        """Ask a connected node to download and install the latest binary.

        When ``target`` is provided it carries a server-resolved marketplace asset
        (GitHub direct link, sha256, and proxy fields) — the node downloads
        straight from GitHub and no server-side mirror is involved. Without it
        the method falls back to the locally hosted binary mirror.

        The node acks "accepted" immediately then restarts asynchronously; the new
        ``client_version`` on reconnect is the real confirmation.
        """
        node_id = (node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if _is_passive_manager(record):
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} is a grouping container with no client to upgrade",
            )
        conn = self.registry.lookup(node_id)
        if conn is None:
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} is offline")

        caps = record.capabilities or {}
        os_name = (caps.get("os") or "").strip()
        arch = (caps.get("arch") or "").strip()
        if not os_name or not arch:
            raise RPCError(
                Code.FAILED_PRECONDITION,
                f"node {node_id} has not reported its os/arch yet; cannot pick a binary",
            )

        proxy_fields: dict = {}
        if target:
            target_version = str(target.get("target_version") or "").strip()
            download_url = str(target.get("download_url") or "").strip()
            sha256 = str(target.get("sha256") or "").strip()
            proxy_fields = {
                "proxy_mode": str(target.get("proxy_mode") or ""),
                "proxy_url": str(target.get("proxy_url") or ""),
                "proxy_url_prefix": str(target.get("proxy_url_prefix") or ""),
            }
            if not download_url:
                raise RPCError(Code.INVALID_ARGUMENT, "target.download_url is required")
        else:
            # Legacy path: serve the locally hosted build through our own mirror.
            from .binaries import (
                binary_name_for,
                latest_node_version,
                node_binary_sha256,
            )
            try:
                bin_name = binary_name_for(record.role, os_name, arch)
            except ValueError as exc:
                raise RPCError(Code.FAILED_PRECONDITION, str(exc))
            if not self.server_url:
                raise RPCError(
                    Code.FAILED_PRECONDITION,
                    "server_url is not configured; cannot build a download URL for the node",
                )
            download_url = f"{self.server_url}/api/v1/public/nodes/binaries/{bin_name}"
            target_version = latest_node_version()
            sha256 = node_binary_sha256(bin_name)

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.self_upgrade.CopyFrom(
            pb.NodeSelfUpgrade(
                target_version=target_version,
                download_url=download_url,
                sha256=sha256,
                proxy_mode=proxy_fields.get("proxy_mode", ""),
                proxy_url=proxy_fields.get("proxy_url", ""),
                proxy_url_prefix=proxy_fields.get("proxy_url_prefix", ""),
            )
        )
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"send to node {node_id} failed: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=SELF_UPGRADE_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"node {node_id} did not accept the upgrade within "
                f"{int(SELF_UPGRADE_ACK_TIMEOUT)}s",
            )
        if ack is None or not ack.ok:
            message = (getattr(ack, "error", "") or "").strip() or "node reported failure"
            raise RPCError(Code.INTERNAL, f"self-upgrade on {node_id} failed: {message}")
        return {
            "node_id": node_id,
            "target_version": target_version,
            "download_url": download_url,
            "accepted": True,
        }

    async def revoke_onboard_node(self, req: "pb.RevokeOnboardNodeRequest") -> "pb.RevokeOnboardNodeResponse":
        node_id = (req.node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "node_id is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            return pb.RevokeOnboardNodeResponse()  # idempotent

        never_connected = record.last_seen_at is None
        if self.registry.lookup(node_id) is not None:
            never_connected = False
        if never_connected:
            try:
                await self.store.delete_node(node_id)
            except NodeNotFound as exc:
                raise RPCError(Code.NOT_FOUND, str(exc))
            return pb.RevokeOnboardNodeResponse(deleted=True)

        try:
            await self.store.set_node_status(node_id, NODE_STATUS_REVOKED)
        except NodeNotFound as exc:
            raise RPCError(Code.NOT_FOUND, str(exc))
        self.registry.disconnect(node_id)
        updated = await self.store.get_node_if_exists(node_id)
        resp = pb.RevokeOnboardNodeResponse(revoked=True)
        if updated is not None:
            resp.node.CopyFrom(self.node_info(updated))
        return resp

    # ── DispatchSession / DeleteNodeSession / SendSessionInput ──────────────────
    @staticmethod
    def _session_binding(spec: "pb.NodeCreateSession", session_id: str, node_id: str, status: str) -> NodeSessionBinding:
        """Build the store binding for a dispatched session.

        Shared by the fresh-dispatch path and the idempotent ``already exists``
        rebind below so the two never drift on which fields are persisted.
        """
        return NodeSessionBinding(
            session_id=session_id,
            node_id=node_id,
            project_id=(spec.project_id or "").strip(),
            task_id=(spec.task_id or "").strip(),
            editor_id=(spec.editor_id or "").strip(),
            editor_session_id=(spec.editor_session_id or "").strip(),
            provider=(spec.provider or "").strip(),
            model=(spec.model or "").strip(),
            mode=(spec.mode or "").strip(),
            status=status,
        )

    async def dispatch_session(self, req: "pb.DispatchSessionRequest") -> "pb.DispatchSessionResponse":
        if not req.HasField("session"):
            raise RPCError(Code.INVALID_ARGUMENT, "dispatch session: session spec is required")
        spec = req.session
        session_id = (spec.session_id or "").strip()
        if not session_id:
            session_id = "sess-" + str(uuid.uuid4())
            spec.session_id = session_id

        node_id, conn = await self._select_node((req.node_id or "").strip(), spec)

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.create_session.CopyFrom(spec)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"dispatch session to node {node_id}: {exc}")

        try:
            ack = await asyncio.wait_for(ack_future, timeout=DISPATCH_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED,
                f"dispatch session {session_id}: node {node_id} did not ack in time",
            )
        except ConnectionError:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} disconnected during dispatch")

        if ack is None or not ack.ok:
            msg = "node rejected the session"
            if ack is not None and (ack.error or "").strip():
                msg = ack.error
            # Idempotent dispatch: the node already holds this session id (a
            # previous dispatch created it, but the caller lost its handle — the
            # task row's node_session_id was cleared while the node kept the
            # session). "already exists" means the session IS placed: adopt it
            # (rebind + accepted) instead of rejecting, so a re-dispatch
            # self-heals instead of terminalizing the task as error.
            if ack is not None and "already exists" in msg.lower():
                status = "provisioned" if spec.defer_start else "running"
                await self.store.bind_session_to_node(
                    self._session_binding(spec, session_id, node_id, status)
                )
                return pb.DispatchSessionResponse(
                    session_id=session_id, node_id=node_id, accepted=True
                )
            return pb.DispatchSessionResponse(
                session_id=session_id, node_id=node_id, accepted=False, error=msg
            )

        status = "provisioned" if spec.defer_start else "running"
        await self.store.bind_session_to_node(
            self._session_binding(spec, session_id, node_id, status)
        )
        return pb.DispatchSessionResponse(session_id=session_id, node_id=node_id, accepted=True)

    async def delete_node_session(self, req: "pb.DeleteNodeSessionRequest") -> "pb.DeleteNodeSessionResponse":
        session_id = (req.session_id or "").strip()
        if not session_id:
            raise RPCError(Code.INVALID_ARGUMENT, "delete node session: session_id is required")
        binding = await self.store.get_session_node(session_id)
        if binding is None:
            raise RPCError(Code.NOT_FOUND, f"session {session_id} is not placed on any node")
        deleted = False
        conn = self.registry.lookup(binding.node_id)
        if conn is not None:
            frame_id = str(uuid.uuid4())
            ack_future = conn.await_ack(frame_id)
            frame = pb.NodeDownstreamFrame(
                server_frame_id=frame_id,
                created_at=crypto.rfc3339nano(crypto.utc_now()),
            )
            frame.delete_session.CopyFrom(pb.NodeDeleteSession(session_id=session_id))
            try:
                conn.send(frame)
                ack = await asyncio.wait_for(ack_future, timeout=DISPATCH_ACK_TIMEOUT)
                deleted = ack is not None and ack.ok
            except (asyncio.TimeoutError, ConnectionError, Exception):  # noqa: BLE001
                conn.cancel_ack(frame_id)
        await self.store.unbind_session(session_id)
        return pb.DeleteNodeSessionResponse(deleted=deleted)

    async def send_session_input(self, req: "pb.SendSessionInputRequest") -> "pb.SendSessionInputResponse":
        session_id = (req.session_id or "").strip()
        if not session_id:
            raise RPCError(Code.INVALID_ARGUMENT, "send session input: session_id is required")
        kind = (req.kind or "").strip() or "human_message"
        binding = await self.store.get_session_node(session_id)
        if binding is None:
            raise RPCError(Code.NOT_FOUND, f"session {session_id} is not placed on any node")
        conn = self.registry.lookup(binding.node_id)
        if conn is None:
            raise RPCError(Code.UNAVAILABLE, f"node {binding.node_id} for session {session_id} is offline")
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        session_input = pb.NodeSessionInput(
            session_id=session_id,
            kind=kind,
            text=req.text,
            model=(getattr(req, "model", "") or ""),
            mode=(getattr(req, "mode", "") or ""),
            client_message_id=(getattr(req, "client_message_id", "") or "").strip(),
            delivery_attempt=max(int(getattr(req, "delivery_attempt", 0) or 0), 0),
        )
        if req.HasField("llm"):
            session_input.llm.CopyFrom(req.llm)
        frame.session_input.CopyFrom(session_input)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            return pb.SendSessionInputResponse(accepted=False, error=str(exc))
        return pb.SendSessionInputResponse(accepted=True)

    async def host_exec(self, req: "pb.NodeHostExecRequest") -> "pb.NodeHostExecResult":
        """Execute one structured host command on an approved live node."""
        node_id = (req.node_id or "").strip() if hasattr(req, "node_id") else ""
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "host exec: node_id is required")
        command = (req.command or "").strip()
        if not command:
            raise RPCError(Code.INVALID_ARGUMENT, "host exec: command is required")
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if record.status != NODE_STATUS_APPROVED:
            raise RPCError(Code.PERMISSION_DENIED, f"node {node_id} is not approved")
        conn = self.registry.lookup(node_id)
        if conn is None or conn.closed:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} is offline")
        labels = getattr(record, "capabilities", None) or {}
        if labels.get("host_exec") != "true":
            raise RPCError(Code.FAILED_PRECONDITION, f"node {node_id} does not support host exec")

        request_id = str(uuid.uuid4())
        payload = pb.NodeHostExecRequest(
            request_id=request_id,
            command=command,
            cwd=(req.cwd or "").strip(),
            timeout_ms=max(int(req.timeout_ms or 0), 0),
            max_output_bytes=max(int(req.max_output_bytes or 0), 0),
        )
        result_future = conn.await_host_exec(request_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.host_exec.CopyFrom(payload)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_host_exec(request_id)
            raise RPCError(Code.UNAVAILABLE, f"dispatch host command to node {node_id}: {exc}")
        try:
            return await asyncio.wait_for(result_future, timeout=DISPATCH_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_host_exec(request_id)
            raise RPCError(Code.DEADLINE_EXCEEDED, f"node {node_id} did not return host command in time")
        except ConnectionError:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} disconnected during host command")

    async def host_file_upload(self, req: "pb.HostFileUploadRequest") -> "pb.HostFileUploadResponse":
        """Push one chunk of a binary file upload to an approved live node.

        The caller drives chunking and awaits each chunk's result before sending
        the next, so ordering is enforced by the request sequence rather than by
        buffering here. Guards mirror :meth:`host_exec` (exists → approved →
        online → capability) because both write to the node's host filesystem.
        """
        node_id = (req.node_id or "").strip()
        if not node_id:
            raise RPCError(Code.INVALID_ARGUMENT, "host file upload: node_id is required")
        upload_id = (req.upload_id or "").strip()
        if not upload_id:
            raise RPCError(Code.INVALID_ARGUMENT, "host file upload: upload_id is required")
        path = (req.path or "").strip()
        if not path:
            raise RPCError(Code.INVALID_ARGUMENT, "host file upload: path is required")
        if len(req.data) > MAX_UPLOAD_CHUNK_BYTES:
            raise RPCError(
                Code.INVALID_ARGUMENT,
                f"host file upload: chunk exceeds {MAX_UPLOAD_CHUNK_BYTES} bytes",
            )
        if int(req.total_size or 0) > MAX_UPLOAD_TOTAL_BYTES:
            raise RPCError(
                Code.INVALID_ARGUMENT,
                f"host file upload: total size exceeds {MAX_UPLOAD_TOTAL_BYTES} bytes",
            )
        record = await self.store.get_node_if_exists(node_id)
        if record is None:
            raise RPCError(Code.NOT_FOUND, f"node {node_id} not found")
        if record.status != NODE_STATUS_APPROVED:
            raise RPCError(Code.PERMISSION_DENIED, f"node {node_id} is not approved")
        conn = self.registry.lookup(node_id)
        if conn is None or conn.closed:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} is offline")
        labels = getattr(record, "capabilities", None) or {}
        if labels.get("file_upload") != "true":
            raise RPCError(
                Code.FAILED_PRECONDITION, f"node {node_id} does not support file upload"
            )

        payload = pb.NodeFileUploadRequest(
            upload_id=upload_id,
            path=path,
            offset=max(int(req.offset or 0), 0),
            data=bytes(req.data),
            total_size=max(int(req.total_size or 0), 0),
            sha256=(req.sha256 or "").strip(),
            overwrite=bool(req.overwrite),
            final=bool(req.final),
        )
        result_future = conn.await_file_upload(upload_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=str(uuid.uuid4()),
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        frame.file_upload.CopyFrom(payload)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_file_upload(upload_id)
            raise RPCError(Code.UNAVAILABLE, f"dispatch file chunk to node {node_id}: {exc}")
        try:
            result = await asyncio.wait_for(result_future, timeout=DISPATCH_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_file_upload(upload_id)
            raise RPCError(
                Code.DEADLINE_EXCEEDED, f"node {node_id} did not ack the file chunk in time"
            )
        except ConnectionError:
            raise RPCError(Code.UNAVAILABLE, f"node {node_id} disconnected during file upload")
        return pb.HostFileUploadResponse(
            ok=bool(result.ok),
            bytes_written=int(result.bytes_written or 0),
            path=result.path or path,
            error=result.error or "",
        )

    async def _node_satisfies_spec(
        self, record: NodeRecord, conn: Connection, spec: "pb.NodeCreateSession"
    ) -> tuple[str, bool]:
        """Check provider/driver capability plus configured session capacity."""
        reason, ok = _node_capability_satisfies_spec(conn, spec)
        if not ok:
            return reason, False
        reason, ok = _node_mode_satisfies_spec(conn, spec)
        if not ok:
            return reason, False
        capacity = record.capacity or {}
        active = len(conn.active_sessions())
        max_sessions = int(capacity.get("max_sessions") or 0)
        if max_sessions > 0 and active >= max_sessions:
            return f"node session capacity reached ({active}/{max_sessions})", False
        # Every editor session consumes the configured global default request.
        from .config import settings

        cpu_total = float(capacity.get("cpu_total") or 0)
        if cpu_total > 0 and settings.node_default_session_cpu > 0:
            if (active + 1) * settings.node_default_session_cpu > cpu_total:
                return "node CPU capacity reached", False
        memory_total = int(capacity.get("memory_total") or 0)
        if memory_total > 0 and settings.node_default_session_memory > 0:
            if (active + 1) * settings.node_default_session_memory > memory_total:
                return "node memory capacity reached", False
        return "", True

    async def _select_node(
        self, explicit_node_id: str, spec: "pb.NodeCreateSession"
    ) -> tuple[str, Connection]:
        if explicit_node_id:
            record = await self.store.get_node_if_exists(explicit_node_id)
            if record is None:
                raise RPCError(Code.NOT_FOUND, f"node {explicit_node_id} not found")
            if record.status != NODE_STATUS_APPROVED:
                raise RPCError(
                    Code.FAILED_PRECONDITION,
                    f"node {explicit_node_id} is not approved (status {record.status})",
                )
            conn = self.registry.lookup(explicit_node_id)
            if conn is None:
                raise RPCError(Code.UNAVAILABLE, f"node {explicit_node_id} is offline")
            # A registered stream whose heartbeat has gone silent is not
            # dispatchable: the reaper has a 60 s grace window, but dispatching
            # into a dead peer just stalls. Treat stale heartbeat as offline.
            if not _connection_live(conn):
                raise RPCError(
                    Code.UNAVAILABLE,
                    f"node {explicit_node_id} heartbeat stale",
                )
            reason, ok = await self._node_satisfies_spec(record, conn, spec)
            if not ok:
                raise RPCError(
                    Code.FAILED_PRECONDITION,
                    f"node {explicit_node_id} cannot run this session: {reason}",
                )
            return explicit_node_id, conn
        # Auto-select: first approved + online (heartbeat fresh) + capable node.
        for node_id in self.registry.list():
            record = await self.store.get_node_if_exists(node_id)
            if record is None or record.status != NODE_STATUS_APPROVED:
                continue
            conn = self.registry.lookup(node_id)
            if conn is None or not _connection_live(conn):
                continue
            _, ok = await self._node_satisfies_spec(record, conn, spec)
            if not ok:
                continue
            return node_id, conn
        raise RPCError(
            Code.UNAVAILABLE, "no approved, connected node satisfies the session requirements"
        )

    # ── FollowNodeSession (server stream) ───────────────────────────────────────
    async def resolve_follow(self, session_id: str) -> tuple[Connection, str]:
        """Resolve the live connection for a session to follow. Raises RPCError."""
        session_id = (session_id or "").strip()
        if not session_id:
            raise RPCError(Code.INVALID_ARGUMENT, "follow node session: session_id is required")
        binding = await self.store.get_session_node(session_id)
        if binding is None:
            raise RPCError(Code.NOT_FOUND, f"session {session_id} is not placed on any node")
        conn = self.registry.lookup(binding.node_id)
        if conn is None:
            raise RPCError(Code.UNAVAILABLE, f"node {binding.node_id} for session {session_id} is offline")
        return conn, session_id

    # ── Split-config RPCs (mirror node_config.go) ───────────────────────────────
    def _next_revision(self) -> int:
        import time as _t

        return _t.time_ns()

    async def _dispatch_config_command(
        self, session_id: str, build_frame, *, revision: int, mutate_mode: str = ""
    ) -> "pb.NodeSessionConfigAck":
        session_id = (session_id or "").strip()
        if not session_id:
            raise RPCError(Code.INVALID_ARGUMENT, "session_id is required")
        binding = await self.store.get_session_node(session_id)
        if binding is None:
            raise RPCError(Code.NOT_FOUND, f"session {session_id} is not placed on any node")
        conn = self.registry.lookup(binding.node_id)
        if conn is None:
            raise RPCError(Code.UNAVAILABLE, f"node {binding.node_id} for session {session_id} is offline")

        frame_id = str(uuid.uuid4())
        ack_future = conn.await_ack(frame_id)
        frame = pb.NodeDownstreamFrame(
            server_frame_id=frame_id,
            created_at=crypto.rfc3339nano(crypto.utc_now()),
        )
        build_frame(frame)
        try:
            conn.send(frame)
        except Exception as exc:  # noqa: BLE001
            conn.cancel_ack(frame_id)
            raise RPCError(Code.UNAVAILABLE, f"dispatch config to node {binding.node_id}: {exc}")
        try:
            ack = await asyncio.wait_for(ack_future, timeout=DISPATCH_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            conn.cancel_ack(frame_id)
            raise RPCError(Code.DEADLINE_EXCEEDED, f"session {session_id}: node did not ack config in time")
        except ConnectionError:
            raise RPCError(Code.UNAVAILABLE, f"node {binding.node_id} disconnected during config")

        if ack is not None and ack.ok:
            # Persist the config snapshot best-effort (swallow failures).
            try:
                await self.store.update_session_config_snapshot(
                    NodeSessionBinding(
                        session_id=session_id,
                        mode=mutate_mode,
                        applied_revision=ack.applied_revision,
                        effective_revision=ack.effective_revision,
                    )
                )
            except (SessionNotBound, Exception):  # noqa: BLE001
                pass
        return _config_ack_from_command_ack(ack)

    async def configure_session_llm(self, req: "pb.ConfigureNodeSessionLLMRequest") -> "pb.NodeSessionConfigAck":
        revision = self._next_revision()

        def build(frame: "pb.NodeDownstreamFrame") -> None:
            payload = pb.ConfigureSessionLLM(session_id=req.session_id, revision=revision)
            if req.HasField("llm"):
                payload.llm.CopyFrom(req.llm)
            frame.configure_session_llm.CopyFrom(payload)

        return await self._dispatch_config_command(req.session_id, build, revision=revision)

    async def apply_session_mcps(self, req: "pb.ApplyNodeSessionMCPsRequest") -> "pb.NodeSessionConfigAck":
        revision = self._next_revision()

        def build(frame: "pb.NodeDownstreamFrame") -> None:
            payload = pb.ApplySessionMCPs(session_id=req.session_id, revision=revision)
            payload.mcps.extend(req.mcps)
            frame.apply_session_mcps.CopyFrom(payload)

        return await self._dispatch_config_command(req.session_id, build, revision=revision)

    async def apply_session_skills(self, req: "pb.ApplyNodeSessionSkillsRequest") -> "pb.NodeSessionConfigAck":
        revision = self._next_revision()

        def build(frame: "pb.NodeDownstreamFrame") -> None:
            payload = pb.ApplySessionSkills(session_id=req.session_id, revision=revision)
            payload.skills.extend(req.skills)
            frame.apply_session_skills.CopyFrom(payload)

        return await self._dispatch_config_command(req.session_id, build, revision=revision)

    async def apply_session_plugins(self, req: "pb.ApplyNodeSessionPluginsRequest") -> "pb.NodeSessionConfigAck":
        revision = self._next_revision()

        def build(frame: "pb.NodeDownstreamFrame") -> None:
            payload = pb.ApplySessionPlugins(session_id=req.session_id, revision=revision)
            payload.plugins.extend(req.plugins)
            frame.apply_session_plugins.CopyFrom(payload)

        return await self._dispatch_config_command(req.session_id, build, revision=revision)

    async def configure_session_mode(self, req: "pb.ConfigureNodeSessionModeRequest") -> "pb.NodeSessionConfigAck":
        revision = self._next_revision()

        def build(frame: "pb.NodeDownstreamFrame") -> None:
            frame.configure_session_mode.CopyFrom(
                pb.ConfigureSessionMode(session_id=req.session_id, revision=revision, mode=req.mode)
            )

        return await self._dispatch_config_command(
            req.session_id, build, revision=revision, mutate_mode=(req.mode or "").strip()
        )

    async def start_session_runtime(self, req: "pb.StartNodeSessionRuntimeRequest") -> "pb.NodeSessionConfigAck":
        def build(frame: "pb.NodeDownstreamFrame") -> None:
            frame.start_session_runtime.CopyFrom(pb.StartSessionRuntime(session_id=req.session_id))

        return await self._dispatch_config_command(req.session_id, build, revision=0)

    async def restart_session_runtime(self, req: "pb.RestartNodeSessionRuntimeRequest") -> "pb.NodeSessionConfigAck":
        def build(frame: "pb.NodeDownstreamFrame") -> None:
            frame.restart_session_runtime.CopyFrom(
                pb.RestartSessionRuntime(session_id=req.session_id, fresh=req.fresh)
            )

        return await self._dispatch_config_command(req.session_id, build, revision=0)

    async def collect_session_artifacts(self, req: "pb.CollectNodeSessionArtifactsRequest") -> "pb.NodeSessionConfigAck":
        def build(frame: "pb.NodeDownstreamFrame") -> None:
            frame.collect_session_artifacts.CopyFrom(
                pb.CollectSessionArtifacts(session_id=req.session_id, path=req.path)
            )

        return await self._dispatch_config_command(req.session_id, build, revision=0)


# ── module-level helpers ────────────────────────────────────────────────────────

def _aware(dt):
    """Treat a naive datetime as UTC (the compat layer stores naive UTC)."""
    from datetime import timezone as _tz

    if dt.tzinfo is None:
        return dt.replace(tzinfo=_tz.utc)
    return dt


def _connection_live(conn: Connection) -> bool:
    connected_at, last_hb, _ = conn.snapshot()
    liveness = last_hb
    if liveness is None or (connected_at is not None and connected_at > liveness):
        liveness = connected_at
    if liveness is None:
        return False
    return (crypto.utc_now() - liveness) <= NODE_HEARTBEAT_TIMEOUT


def _node_capability_satisfies_spec(conn: Connection, spec: "pb.NodeCreateSession") -> tuple[str, bool]:
    caps = conn.capabilities
    driver = (spec.driver or "").strip().lower()
    if driver == "docker":
        if caps is None or not caps.docker:
            return "node does not offer the docker driver", False
        return "", True
    if driver in ("", "local", "process"):
        provider = (spec.provider or "").strip()
        if not provider:
            return "", True
        if caps is None:
            return "node advertised no capabilities", False
        for p in caps.providers:
            if p.strip().lower() == provider.lower():
                return "", True
        return f'provider "{provider}" is not installed on the node', False
    return f'unsupported driver "{driver}"', False


def _node_mode_satisfies_spec(conn: Connection, spec: "pb.NodeCreateSession") -> tuple[str, bool]:
    """Reject a session whose requested editor ``mode`` the node's editor does
    not advertise.

    Empty mode means "use the editor's default" and always passes (backward
    compatible with old nodes that never reported editor capabilities). A
    non-empty mode must exactly match one of the mode ids in the matching
    provider's advertised EditorCapability; "provider installed" is deliberately
    NOT treated as "supports every mode", so a task can never silently run with
    broader permissions than requested.
    """
    mode = (spec.mode or "").strip()
    if not mode:
        return "", True
    provider = (spec.provider or "").strip().lower()
    caps = conn.capabilities
    if caps is None:
        return "node advertised no capabilities", False
    for editor in caps.editors:
        if editor.provider.strip().lower() != provider:
            continue
        available = [m.id for m in editor.modes]
        for mode_id in available:
            if mode_id == mode:
                return "", True
        listed = ", ".join(available) or "无"
        return (
            f'editor "{provider}" does not support mode "{mode}" '
            f"(available: {listed})",
            False,
        )
    return f'node did not report editor capabilities for provider "{provider}"', False


def _config_ack_from_command_ack(ack: Optional["pb.NodeCommandAck"]) -> "pb.NodeSessionConfigAck":
    if ack is None:
        return pb.NodeSessionConfigAck(ok=False, error="node did not ack")
    return pb.NodeSessionConfigAck(
        ok=ack.ok,
        error=ack.error,
        applied_revision=ack.applied_revision,
        effective_revision=ack.effective_revision,
        restart_required=ack.restart_required,
    )
