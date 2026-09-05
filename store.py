"""Durable node ledger for the standalone NodeService control process.

This is the Python port of the Go daemon's SQLite ledger
(``pkg/storage/configstore/node_store.go`` + ``pkg/model/node_model.go``). It
owns two additive ``mc_ac_*`` tables:

* ``mc_ac_nodes`` — the node registration ledger (id, approval status, role,
  startup method, owner, the AES-GCM-sealed TOTP secret, platform, capability
  labels, liveness hint).
* ``mc_ac_node_sessions`` — session→node placement bindings plus a lightweight
  config snapshot (provider/model/mode/status + applied/effective revisions).

The node itself is stateless; this ledger is the authority on which nodes
exist, their approval status, and where each session was placed. Live
connection state (the bidi stream, heartbeats, sinks) lives in
:mod:`.registry`, never here.

Both models are registered only by :mod:`node_server.database`, which uses an
independent Tortoise connection while pointing at the same PostgreSQL database
as the data service. Columns are additive; the sealed-secret column is never
serialized outward.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

from tortoise import fields
from tortoise.exceptions import IntegrityError
from tortoise.models import Model
from tortoise.transactions import in_transaction

# ── Domain constants (mirror pkg/model/node_model.go) ──────────────────────────

NODE_STATUS_PENDING = "pending"
NODE_STATUS_APPROVED = "approved"
NODE_STATUS_REVOKED = "revoked"

NODE_ROLE_EXECUTION = "execution"
NODE_ROLE_MANAGEMENT = "management"
NODE_ROLE_PASSIVE_MANAGEMENT = "passive_management"
NODE_ROLE_IOS_HOST = "ios_host"

NODE_STARTUP_STANDALONE = "standalone"
NODE_STARTUP_SYSTEMD = "systemd"
NODE_STARTUP_DOCKER = "docker"
NODE_STARTUP_DOCKER_COMPOSE = "docker-compose"

# Global public-IP lookup configuration. The node control ledger owns a single
# revisioned row so every execution/management client receives the same ordered
# IPv4/IPv6 URL lists.
PUBLIC_IP_LOOKUP_KEY = "default"
PUBLIC_IP_LOOKUP_MAX_URLS = 64
PUBLIC_IP_LOOKUP_MAX_URL_LEN = 512
PUBLIC_IP_LOOKUP_MIN_URLS = 3

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _normalize_lookup_urls(raw) -> list[str]:
    """Normalize a free-form IPv4/IPv6 URL list into ordered, deduped HTTP(S) URLs.

    Accepts a list/tuple or a JSON string. Trims entries, drops blanks, removes
    duplicates while preserving first-seen order, and requires each value to be
    an absolute HTTP or HTTPS URL. Raises ValueError on any invalid entry.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "[]")
        except (ValueError, TypeError):
            raise ValueError("public ip url list must be a JSON array")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("public ip url list must be a JSON array")

    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            raise ValueError("public ip url must be a string")
        url = item.strip()
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"public ip url must be an absolute HTTP or HTTPS URL: {url!r}")
        if len(url) > PUBLIC_IP_LOOKUP_MAX_URL_LEN:
            raise ValueError(f"public ip url too long: {url[:64]!r}")
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    if len(out) > PUBLIC_IP_LOOKUP_MAX_URLS:
        raise ValueError(
            f"public ip url list too long: max {PUBLIC_IP_LOOKUP_MAX_URLS} entries"
        )
    if 0 < len(out) < PUBLIC_IP_LOOKUP_MIN_URLS:
        raise ValueError(
            f"public ip url list must be empty or at least {PUBLIC_IP_LOOKUP_MIN_URLS} unique URLs"
        )
    return out


def _now() -> datetime:
    # Naive UTC to match the compat layer's use_tz=False convention.
    return datetime.utcnow()


def normalize_node_status(status: str) -> str:
    s = (status or "").strip().lower()
    if s == NODE_STATUS_APPROVED:
        return NODE_STATUS_APPROVED
    if s == NODE_STATUS_REVOKED:
        return NODE_STATUS_REVOKED
    return NODE_STATUS_PENDING


def normalize_node_role(role: str) -> str:
    s = (role or "").strip().lower()
    if s == NODE_ROLE_MANAGEMENT:
        return NODE_ROLE_MANAGEMENT
    if s == NODE_ROLE_PASSIVE_MANAGEMENT:
        return NODE_ROLE_PASSIVE_MANAGEMENT
    if s == NODE_ROLE_IOS_HOST:
        return NODE_ROLE_IOS_HOST
    return NODE_ROLE_EXECUTION


def normalize_startup_method(method: str) -> str:
    s = (method or "").strip().lower()
    if s in (
        NODE_STARTUP_STANDALONE,
        NODE_STARTUP_SYSTEMD,
        NODE_STARTUP_DOCKER,
        NODE_STARTUP_DOCKER_COMPOSE,
    ):
        return s
    return ""


def normalize_node_capacity(value) -> dict[str, int | float]:
    """Normalize operator capacity limits; absent/zero fields mean unlimited."""
    if isinstance(value, str):
        try:
            value = json.loads(value or "{}")
        except (ValueError, TypeError):
            value = {}
    if not isinstance(value, dict):
        return {}
    out: dict[str, int | float] = {}
    try:
        max_sessions = int(value.get("max_sessions") or 0)
        if max_sessions > 0:
            out["max_sessions"] = max_sessions
    except (TypeError, ValueError):
        pass
    try:
        cpu_total = float(value.get("cpu_total") or 0)
        if cpu_total > 0:
            out["cpu_total"] = cpu_total
    except (TypeError, ValueError):
        pass
    try:
        memory_total = int(value.get("memory_total") or 0)
        if memory_total > 0:
            out["memory_total"] = memory_total
    except (TypeError, ValueError):
        pass
    return out


# ── Tortoise models ────────────────────────────────────────────────────────────


class ACNode(Model):
    """Node registration ledger row (Go ``node`` table → ``mc_ac_nodes``).

    ``credential_secret_enc`` holds the base64 ``nonce||ciphertext||tag`` sealing
    the node's base32 TOTP secret under the server master key. It is never
    serialized into any API response (the record→NodeInfo projection drops it).
    """

    id = fields.CharField(max_length=128, pk=True)
    name = fields.CharField(max_length=255, default="")
    status = fields.CharField(max_length=16, default=NODE_STATUS_PENDING)
    role = fields.CharField(max_length=32, default=NODE_ROLE_EXECUTION)
    startup_method = fields.CharField(max_length=32, default="")
    manager_node_id = fields.CharField(max_length=128, default="")
    credential_secret_enc = fields.TextField(default="")
    platform = fields.CharField(max_length=64, default="")
    capabilities_json = fields.TextField(default="{}")
    # Operator-configured capacity; kept separate from node-reported capabilities.
    # {"max_sessions": int, "cpu_total": float, "memory_total": int(bytes)}
    capacity_json = fields.TextField(default="{}")
    # Per-node egress-proxy binding: proxy_config_id names a proxy-pool entry the
    # node uses for GitHub downloads ("" = direct). Picked at onboard, mutable on
    # the node detail page. last_proxy_config_id remembers the proxy used by the
    # node's last *successful* upgrade (upgrade-dialog preselect). proxy_revision
    # is a per-node monotonic counter bumped on every binding change; it feeds the
    # Go client's revision gate so a reassigned binding survives reconnect.
    proxy_config_id = fields.CharField(max_length=64, default="")
    last_proxy_config_id = fields.CharField(max_length=64, default="")
    proxy_revision = fields.BigIntField(default=0)
    last_seen_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "mc_ac_nodes"
        indexes = (("status",), ("manager_node_id",))


class ACPublicIPLookupConfig(Model):
    """Singleton global public-IP lookup URL snapshot."""

    key = fields.CharField(max_length=32, pk=True, default=PUBLIC_IP_LOOKUP_KEY)
    revision = fields.BigIntField(default=0)
    ipv4_urls_json = fields.TextField(default="[]")
    ipv6_urls_json = fields.TextField(default="[]")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "mc_ac_public_ip_lookup_config"


class ACNodeProxyConfig(Model):
    """DEPRECATED: legacy global singleton node-egress-proxy table.

    The node egress proxy is now a per-node binding stored on ``ACNode``
    (``proxy_config_id`` / ``last_proxy_config_id`` / ``proxy_revision``).
    This model is kept only so Tortoise does not error on the existing
    ``mc_ac_node_proxy_config`` table during the additive migration; nothing
    reads or writes it anymore. Safe to drop after the next release.
    """

    key = fields.CharField(max_length=32, pk=True, default="default")
    revision = fields.BigIntField(default=0)
    proxy_mode = fields.CharField(max_length=16, default="")
    proxy_url = fields.TextField(default="")
    proxy_url_prefix = fields.TextField(default="")
    proxy_config_id = fields.CharField(max_length=64, default="")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "mc_ac_node_proxy_config"


class ACNodeSession(Model):
    """Session→node placement binding (Go ``node_session`` → ``mc_ac_node_sessions``)."""

    session_id = fields.CharField(max_length=128, pk=True)
    node_id = fields.CharField(max_length=128)
    project_id = fields.CharField(max_length=128, default="")
    task_id = fields.CharField(max_length=128, default="")
    editor_id = fields.CharField(max_length=128, default="")
    editor_session_id = fields.CharField(max_length=128, default="")
    provider = fields.CharField(max_length=64, default="")
    model = fields.CharField(max_length=128, default="")
    mode = fields.CharField(max_length=64, default="")
    status = fields.CharField(max_length=32, default="")
    applied_revision = fields.BigIntField(default=0)
    effective_revision = fields.BigIntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "mc_ac_node_sessions"
        indexes = (("node_id",), ("project_id",), ("task_id",))


# ── Plain-data views (decoupled from the ORM row, mirror the Go structs) ────────


@dataclass
class NodeRecord:
    id: str = ""
    name: str = ""
    status: str = NODE_STATUS_PENDING
    role: str = NODE_ROLE_EXECUTION
    startup_method: str = ""
    manager_node_id: str = ""
    credential_secret_enc: str = ""
    platform: str = ""
    capabilities: dict[str, str] = field(default_factory=dict)
    capacity: dict[str, int | float] = field(default_factory=dict)
    proxy_config_id: str = ""
    last_proxy_config_id: str = ""
    proxy_revision: int = 0
    last_seen_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: ACNode) -> "NodeRecord":
        try:
            caps = json.loads(row.capabilities_json or "{}")
            if not isinstance(caps, dict):
                caps = {}
        except (ValueError, TypeError):
            caps = {}
        return cls(
            id=row.id,
            name=row.name,
            status=row.status,
            role=row.role,
            startup_method=row.startup_method,
            manager_node_id=row.manager_node_id,
            credential_secret_enc=row.credential_secret_enc,
            platform=row.platform,
            capabilities={str(k): str(v) for k, v in caps.items()},
            capacity=normalize_node_capacity(getattr(row, "capacity_json", "") or "{}"),
            proxy_config_id=str(getattr(row, "proxy_config_id", "") or ""),
            last_proxy_config_id=str(getattr(row, "last_proxy_config_id", "") or ""),
            proxy_revision=int(getattr(row, "proxy_revision", 0) or 0),
            last_seen_at=row.last_seen_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


@dataclass
class PublicIPLookupConfig:
    revision: int = 0
    ipv4_urls: list[str] = field(default_factory=list)
    ipv6_urls: list[str] = field(default_factory=list)
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: ACPublicIPLookupConfig | None) -> "PublicIPLookupConfig":
        if row is None:
            return cls()

        def _load(value: str) -> list[str]:
            try:
                parsed = json.loads(value or "[]")
            except (ValueError, TypeError):
                return []
            if not isinstance(parsed, list):
                return []
            return [str(item) for item in parsed if isinstance(item, str)]

        return cls(
            revision=int(row.revision or 0),
            ipv4_urls=_load(row.ipv4_urls_json),
            ipv6_urls=_load(row.ipv6_urls_json),
            updated_at=row.updated_at,
        )


@dataclass
class NodeProxyConfigView:
    """Plain-data view of a node's egress-proxy binding.

    Per-node (NOT a global singleton): each node resolves its own
    ``proxy_config_id`` into the three frame fields. ``proxy_mode=""`` means
    direct download. ``proxy_config_id`` is the source pool entry the admin
    picked (kept for the admin UI to preselect); the resolved ``proxy_url`` /
    ``proxy_url_prefix`` are what the node uses. ``revision`` is the node's
    own ``proxy_revision`` counter — feeds the Go client's revision gate.
    """

    revision: int = 0
    proxy_mode: str = ""
    proxy_url: str = ""
    proxy_url_prefix: str = ""
    proxy_config_id: str = ""

    @classmethod
    def from_record(cls, rec: "NodeRecord") -> "NodeProxyConfigView":
        return cls(
            revision=int(getattr(rec, "proxy_revision", 0) or 0),
            proxy_config_id=str(getattr(rec, "proxy_config_id", "") or ""),
        )


@dataclass
class NodeSessionBinding:
    session_id: str = ""
    node_id: str = ""
    project_id: str = ""
    task_id: str = ""
    editor_id: str = ""
    editor_session_id: str = ""
    provider: str = ""
    model: str = ""
    mode: str = ""
    status: str = ""
    applied_revision: int = 0
    effective_revision: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: ACNodeSession) -> "NodeSessionBinding":
        return cls(
            session_id=row.session_id,
            node_id=row.node_id,
            project_id=row.project_id,
            task_id=row.task_id,
            editor_id=row.editor_id,
            editor_session_id=row.editor_session_id,
            provider=row.provider,
            model=row.model,
            mode=row.mode,
            status=row.status,
            applied_revision=int(row.applied_revision or 0),
            effective_revision=int(row.effective_revision or 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


# ── Store API (mirrors the Go nodeStore method surface) ─────────────────────────


class NodeStore:
    """Async facade over the two ledger tables.

    Stateless: every method reads/writes the DB directly, so a singleton is
    fine. Method names mirror the Go ``nodeStore`` so the service layer reads
    like the original.
    """

    async def get_public_ip_lookup_config(self) -> PublicIPLookupConfig:
        row = await ACPublicIPLookupConfig.get_or_none(key=PUBLIC_IP_LOOKUP_KEY)
        return PublicIPLookupConfig.from_row(row)

    async def update_public_ip_lookup_config(
        self, ipv4_urls, ipv6_urls
    ) -> PublicIPLookupConfig:
        ipv4 = _normalize_lookup_urls(ipv4_urls)
        ipv6 = _normalize_lookup_urls(ipv6_urls)
        async with in_transaction() as conn:
            row = (
                await ACPublicIPLookupConfig.filter(key=PUBLIC_IP_LOOKUP_KEY)
                .using_db(conn)
                .select_for_update()
                .first()
            )
            if row is None:
                row = await ACPublicIPLookupConfig.create(
                    key=PUBLIC_IP_LOOKUP_KEY,
                    revision=1,
                    ipv4_urls_json=json.dumps(ipv4),
                    ipv6_urls_json=json.dumps(ipv6),
                    using_db=conn,
                )
            else:
                row.revision = int(row.revision or 0) + 1
                row.ipv4_urls_json = json.dumps(ipv4)
                row.ipv6_urls_json = json.dumps(ipv6)
                await row.save(
                    update_fields=["revision", "ipv4_urls_json", "ipv6_urls_json", "updated_at"],
                    using_db=conn,
                )
        return await self.get_public_ip_lookup_config()

    async def update_node_proxy(
        self,
        node_id: str,
        *,
        proxy_config_id: str,
    ) -> NodeRecord:
        """Bind a proxy-pool entry to one node, bumping its per-node revision.

        ``proxy_config_id`` is the raw pool-entry id ("" = direct); resolution
        to the three frame fields happens in the service layer. The
        ``proxy_revision`` counter is bumped so the Go client's revision gate
        accepts the reassigned binding on reconnect. The bound id survives
        re-register (``upsert_node`` pins it).
        """
        node_id = (node_id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        async with in_transaction() as conn:
            row = (
                await ACNode.filter(id=node_id)
                .using_db(conn)
                .select_for_update()
                .first()
            )
            if row is None:
                raise NodeNotFound(node_id)
            row.proxy_config_id = (proxy_config_id or "").strip()
            row.proxy_revision = int(row.proxy_revision or 0) + 1
            # revision 0 would make the Go gate drop the first push after a DB
            # reset; clamp to 1 so a binding always ships.
            if row.proxy_revision < 1:
                row.proxy_revision = 1
            await row.save(
                update_fields=["proxy_config_id", "proxy_revision", "updated_at"],
                using_db=conn,
            )
        return await self.get_node(node_id)

    async def set_node_last_proxy(
        self, node_id: str, proxy_config_id: str
    ) -> None:
        """Record the proxy used by a node's last *successful* upgrade.

        The upgrade dialog preselects this value next time. Only set after the
        upgrade RPC returns success (a failed dispatch must not overwrite the
        remembered good proxy). Best-effort: a missing node never fails an
        upgrade that already shipped.
        """
        node_id = (node_id or "").strip()
        if not node_id:
            return
        await ACNode.filter(id=node_id).update(
            last_proxy_config_id=(proxy_config_id or "").strip(),
            updated_at=_now(),
        )


    async def patch_node_public_ip_report(
        self,
        node_id: str,
        *,
        ipv4: str | None = None,
        ipv6: str | None = None,
        clear_ipv4: bool = False,
        clear_ipv6: bool = False,
        config_revision: int = 0,
        ipv4_resolved_at: str = "",
        ipv6_resolved_at: str = "",
    ) -> None:
        row = await ACNode.get_or_none(id=(node_id or "").strip())
        if row is None:
            raise NodeNotFound((node_id or "").strip())
        try:
            caps = json.loads(row.capabilities_json or "{}")
            if not isinstance(caps, dict):
                caps = {}
        except (ValueError, TypeError):
            caps = {}
        if clear_ipv4:
            caps.pop("public_ip", None)
            caps.pop("public_ip_resolved_at", None)
        elif ipv4:
            caps["public_ip"] = ipv4
            if ipv4_resolved_at:
                caps["public_ip_resolved_at"] = ipv4_resolved_at
        if clear_ipv6:
            caps.pop("public_ipv6", None)
            caps.pop("public_ipv6_resolved_at", None)
        elif ipv6:
            caps["public_ipv6"] = ipv6
            if ipv6_resolved_at:
                caps["public_ipv6_resolved_at"] = ipv6_resolved_at
        if config_revision:
            caps["public_ip_config_revision"] = str(config_revision)
        now = _now()
        await ACNode.filter(id=row.id).update(
            capabilities_json=json.dumps({str(k): str(v) for k, v in caps.items()}, sort_keys=True),
            last_seen_at=now,
            updated_at=now,
        )

    # -- node registrations --------------------------------------------------

    async def upsert_node(self, item: NodeRecord) -> NodeRecord:
        """Insert or refresh a node registration, idempotent on the node id.

        A reconnecting node refreshes name/platform/capabilities without losing
        its approval status, created_at, or sealed secret. The secret is
        preserved unless a non-empty value is supplied (minted once at onboard,
        never rotates — mirrors the Go ``ON CONFLICT`` CASE).
        """
        node_id = (item.id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        name = (item.name or "").strip() or node_id
        status = normalize_node_status(item.status)
        role = normalize_node_role(item.role)
        startup_method = normalize_startup_method(item.startup_method)
        manager = (item.manager_node_id or "").strip()
        platform = (item.platform or "").strip()
        caps_json = json.dumps(
            {str(k): str(v) for k, v in (item.capabilities or {}).items()},
            sort_keys=True,
        )

        existing = await ACNode.get_or_none(id=node_id)
        if existing is None:
            # First onboard: persist the admin's chosen egress-proxy binding and
            # seed proxy_revision to 1 so the Go revision gate accepts the first
            # push (revision 0 is the "never applied" sentinel). An empty
            # proxy_config_id (direct) still seeds revision 1 — a fresh node
            # always accepts its first NodeProxyConfig frame.
            proxy_config_id = (item.proxy_config_id or "").strip()
            await ACNode.create(
                id=node_id,
                name=name,
                status=status,
                role=role,
                startup_method=startup_method,
                manager_node_id=manager,
                credential_secret_enc=item.credential_secret_enc or "",
                platform=platform,
                capabilities_json=caps_json,
                proxy_config_id=proxy_config_id,
                proxy_revision=1,
                last_seen_at=item.last_seen_at,
            )
        else:
            # Only mutate the fields the Go upsert's DO UPDATE touches:
            # name/endpoint(unused)/platform/capabilities always; secret and
            # last_seen only when a non-empty/newer value is supplied. Status,
            # role, manager, created_at are pinned to the stored values. The
            # per-node egress-proxy binding (proxy_config_id /
            # last_proxy_config_id / proxy_revision) is admin-owned and must
            # survive re-register — it is NEVER overwritten here.
            existing.name = name
            existing.platform = platform
            existing.capabilities_json = caps_json
            if item.credential_secret_enc:
                existing.credential_secret_enc = item.credential_secret_enc
            if item.last_seen_at is not None:
                existing.last_seen_at = item.last_seen_at
            await existing.save(
                update_fields=[
                    "name",
                    "platform",
                    "capabilities_json",
                    "credential_secret_enc",
                    "last_seen_at",
                    "updated_at",
                ]
            )
        return await self.get_node(node_id)

    async def set_node_status(self, node_id: str, status: str) -> None:
        node_id = (node_id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        rows = await ACNode.filter(id=node_id).update(
            status=normalize_node_status(status), updated_at=_now()
        )
        if rows == 0:
            raise NodeNotFound(node_id)

    async def touch_node_last_seen(self, node_id: str, at: datetime | None = None) -> None:
        node_id = (node_id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        when = at or _now()
        await ACNode.filter(id=node_id).update(last_seen_at=when, updated_at=_now())

    async def get_node(self, node_id: str) -> NodeRecord:
        rec = await self.get_node_if_exists(node_id)
        if rec is None:
            raise NodeNotFound((node_id or "").strip())
        return rec

    async def get_node_if_exists(self, node_id: str) -> NodeRecord | None:
        key = (node_id or "").strip()
        if not key:
            raise ValueError("node id is required")
        row = await ACNode.get_or_none(id=key)
        return NodeRecord.from_row(row) if row is not None else None

    async def list_nodes(self, status: str = "", query: str = "") -> list[NodeRecord]:
        rows = await ACNode.all().order_by("name", "id")
        q = (query or "").strip().lower()
        filter_status = bool((status or "").strip())
        want_status = normalize_node_status(status)
        out: list[NodeRecord] = []
        for row in rows:
            rec = NodeRecord.from_row(row)
            if q and q not in rec.name.lower() and q not in rec.id.lower():
                continue
            if filter_status and rec.status != want_status:
                continue
            out.append(rec)
        return out

    async def set_node_capacity(self, node_id: str, capacity: dict | None) -> NodeRecord:
        """Persist operator-configured capacity limits (empty dict = unlimited)."""
        node_id = (node_id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        normalized = normalize_node_capacity(capacity or {})
        rows = await ACNode.filter(id=node_id).update(
            capacity_json=json.dumps(normalized, sort_keys=True), updated_at=_now()
        )
        if rows == 0:
            raise NodeNotFound(node_id)
        return await self.get_node(node_id)

    async def get_node_capacities(self, node_ids: list[str] | None = None) -> dict[str, dict]:
        """Operator-configured capacity per node id (missing/empty = unlimited)."""
        query = ACNode.all()
        if node_ids is not None:
            ids = [str(item) for item in node_ids if item]
            if not ids:
                return {}
            query = query.filter(id__in=ids)
        out: dict[str, dict] = {}
        for row in await query:
            capacity = normalize_node_capacity(getattr(row, "capacity_json", "") or "{}")
            if capacity:
                out[row.id] = capacity
        return out

    async def count_node_sessions(self, node_ids: list[str] | None = None) -> dict[str, int]:
        """Active session placements per node (capacity admission + occupancy UI)."""
        query = ACNodeSession.all()
        if node_ids is not None:
            ids = [str(item) for item in node_ids if item]
            if not ids:
                return {}
            query = query.filter(node_id__in=ids)
        counts: dict[str, int] = {}
        for row in await query:
            if (row.status or "") == "closed":
                continue
            counts[row.node_id] = counts.get(row.node_id, 0) + 1
        return counts

    async def set_node_credential_secret(self, node_id: str, sealed: str) -> None:
        node_id = (node_id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        rows = await ACNode.filter(id=node_id).update(
            credential_secret_enc=sealed, updated_at=_now()
        )
        if rows == 0:
            raise NodeNotFound(node_id)

    async def set_node_manager(self, node_id: str, manager_node_id: str) -> None:
        """把执行节点挪到另一个管理节点下（改归属）。管理节点本身不可移动。"""
        node_id = (node_id or "").strip()
        manager_node_id = (manager_node_id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        if not manager_node_id:
            raise ValueError("manager_node_id is required")
        if node_id == manager_node_id:
            raise ValueError("cannot move a node under itself")
        node = await self.get_node_if_exists(node_id)
        if node is None:
            raise NodeNotFound(node_id)
        if node.role != NODE_ROLE_EXECUTION:
            raise ValueError("only execution nodes can be moved")
        target = await self.get_node_if_exists(manager_node_id)
        if target is None:
            raise NodeNotFound(manager_node_id)
        if target.role != NODE_ROLE_MANAGEMENT:
            raise ValueError("target must be a management node")
        rows = await ACNode.filter(id=node_id).update(
            manager_node_id=manager_node_id, updated_at=_now()
        )
        if rows == 0:
            raise NodeNotFound(node_id)

    async def delete_node(self, node_id: str) -> None:
        node_id = (node_id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        # Emulate the Go FK ON DELETE CASCADE: drop the node's session bindings.
        await ACNodeSession.filter(node_id=node_id).delete()
        rows = await ACNode.filter(id=node_id).delete()
        if rows == 0:
            raise NodeNotFound(node_id)

    # -- session bindings ----------------------------------------------------

    async def bind_session_to_node(self, binding: NodeSessionBinding) -> None:
        session_id = (binding.session_id or "").strip()
        node_id = (binding.node_id or "").strip()
        if not session_id or not node_id:
            raise ValueError("session id and node id are required")
        always = {
            "node_id": node_id,
            "project_id": (binding.project_id or "").strip(),
            "task_id": (binding.task_id or "").strip(),
            "editor_id": (binding.editor_id or "").strip(),
            "editor_session_id": (binding.editor_session_id or "").strip(),
            "applied_revision": int(binding.applied_revision or 0),
            "effective_revision": int(binding.effective_revision or 0),
        }
        # Empty incoming values mean "keep whatever is already bound", so a
        # partial re-bind never blanks a field that the first dispatch filled in.
        when_present = {
            "provider": (binding.provider or "").strip(),
            "model": (binding.model or "").strip(),
            "mode": (binding.mode or "").strip(),
            "status": (binding.status or "").strip(),
        }

        # Idempotent upsert on the session_id primary key. A plain
        # ``get_or_none`` → ``create`` is a TOCTOU race: a retry landing on top of
        # the first dispatch, or two clients binding the same session, both see
        # "no row" and both insert, so the loser trips the primary key and the
        # dispatch surfaces to the user as a failure even though the node already
        # accepted the session. Locking the row when it exists and treating a lost
        # insert race as an update makes the second writer harmless.
        for attempt in range(2):
            async with in_transaction() as conn:
                row = (
                    await ACNodeSession.filter(session_id=session_id)
                    .using_db(conn)
                    .select_for_update()
                    .first()
                )
                if row is not None:
                    for key, value in always.items():
                        setattr(row, key, value)
                    for key, value in when_present.items():
                        if value:
                            setattr(row, key, value)
                    await row.save(using_db=conn)
                    return
            # Insert outside the read transaction: a lost race then aborts nothing
            # we still need, and the retry finds the winner's row to update.
            try:
                await ACNodeSession.create(
                    session_id=session_id, **always, **when_present
                )
            except IntegrityError:
                if attempt:
                    raise
                continue
            return

    async def update_session_config_snapshot(self, binding: NodeSessionBinding) -> None:
        session_id = (binding.session_id or "").strip()
        if not session_id:
            raise ValueError("session id is required")
        existing = await ACNodeSession.get_or_none(session_id=session_id)
        if existing is None:
            raise SessionNotBound(session_id)
        if binding.provider.strip():
            existing.provider = binding.provider.strip()
        if binding.model.strip():
            existing.model = binding.model.strip()
        if binding.mode.strip():
            existing.mode = binding.mode.strip()
        if binding.status.strip():
            existing.status = binding.status.strip()
        existing.applied_revision = binding.applied_revision
        existing.effective_revision = binding.effective_revision
        await existing.save(
            update_fields=[
                "provider",
                "model",
                "mode",
                "status",
                "applied_revision",
                "effective_revision",
                "updated_at",
            ]
        )

    async def get_session_node(self, session_id: str) -> NodeSessionBinding | None:
        session_id = (session_id or "").strip()
        if not session_id:
            raise ValueError("session id is required")
        row = await ACNodeSession.get_or_none(session_id=session_id)
        return NodeSessionBinding.from_row(row) if row is not None else None

    async def list_node_sessions(self, node_id: str) -> list[NodeSessionBinding]:
        node_id = (node_id or "").strip()
        if not node_id:
            raise ValueError("node id is required")
        rows = await ACNodeSession.filter(node_id=node_id).order_by("created_at")
        return [NodeSessionBinding.from_row(r) for r in rows]

    async def unbind_session(self, session_id: str) -> None:
        session_id = (session_id or "").strip()
        if not session_id:
            raise ValueError("session id is required")
        await ACNodeSession.filter(session_id=session_id).delete()


class NodeNotFound(Exception):
    def __init__(self, node_id: str) -> None:
        super().__init__(f"node {node_id} not found")
        self.node_id = node_id


class SessionNotBound(Exception):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"session {session_id} is not bound")
        self.session_id = session_id


# Module singleton (stateless).
node_store = NodeStore()
