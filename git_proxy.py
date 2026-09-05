"""Server-side git smart-HTTP reverse proxy (node control service).

The node clones a session's repo via
``http://<token>@{node_server_public_url}/api/v1/public/nodes/git/r/<repo_path>/``
instead of the real repo URL (dependency clones keep the bare ``.../git/``
form). ``<token>`` is a stateless HMAC keyed by the shared
``node_control_token``; the proxy verifies it, resolves the task's bound repo +
git identity from PostgreSQL (raw SQL — this process only registers its own
Tortoise models), injects the identity's real access token into the upstream
request, and streams the smart-HTTP response back.

The ``r/<repo_path>`` path form exists so ``git clone --recurse-submodules``
works through the proxy: the main clone URL embeds the real repo's
host-relative path, so a relative ``.gitmodules`` url like ``../sibling.git``
resolves to ``/git/r/<sibling-path>/`` — back inside this router. Each such
request is served only if ``<repo_path>`` is the task's own repository or a
same-host submodule the repository declares in ``.gitmodules``; the gateway
persists that allowlist to ``config_snapshot.submodule_paths`` at dispatch and
the proxy reads it in ``_resolve``. A node-supplied list is never trusted.
Submodule paths are fetch-only — pushes are accepted for the main repo path
only.

The node therefore never holds a real git credential. The token is scoped to a
single task and is revoked the moment the task leaves an active state:
``pending``/``processing``/``error`` only — a finished/stopped/deleted task
yields 403, so a token left behind in ``.git/config`` is useless once the task
ends.

Token format (keep in sync with ``monkeycode_compat.task_service``
``_git_proxy_token``):

    sig   = HMAC-SHA256(key=node_control_token,
                        msg="git-proxy:{task_id}:{scope}:{mode}").hexdigest()[:32]
    token = f"{task_id}.{scope}.{mode}.{sig}"

``scope`` is ``main`` for the task's own repository, or an associated project's
UUID for a dependency clone (project association feature). ``mode`` is ``ro``
(fetch only) or ``rw`` (fetch + push). Because the signature covers scope and
mode, a node cannot promote its own token to ``rw`` or point it at an
unassociated repository — both edits break the HMAC.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import aiohttp
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from loguru import logger

from .config import settings

_TOKEN_DOMAIN = "git-proxy"
_SCOPE_MAIN = "main"
_MODE_RO = "ro"
_MODE_RW = "rw"
_VALID_MODES = frozenset({_MODE_RO, _MODE_RW})

# Headers that must NOT be replayed to the upstream: hop-by-hop ones, the
# inbound Authorization (the node's proxy token — the upstream gets its own
# credential injected below), the inbound Host (ours, not the git host's —
# forwarding it would make the upstream serve the wrong virtual host), and
# content-length (aiohttp recomputes it for the body we hand it).
_REQUEST_STRIP = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
    "authorization", "host", "content-length",
})
# Response side: strip the same hop-by-hop set plus content-length, since the
# body is re-chunked as a stream and a stale length would desync the client.
_RESPONSE_STRIP = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-length",
})
_ACTIVE_TASK_STATUSES = frozenset({"pending", "processing", "error"})
# A task in ``error`` is usually terminal — but the only path that re-clones a
# repo is a *re-dispatch* of a task whose previous dispatch failed at git clone
# (the failure lands as status=error + workspace_state=dispatch_failed). Without
# error in the allowed set, that re-dispatch's clone 403s on its own task row, so
# the retry can never succeed. ``finished`` / ``stopped`` stay revoked: those are
# genuinely done and a stale token must not pull code.


class _GitProxyError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class _GitTarget:
    repo_url: str
    username: str | None
    access_token: str | None
    # Same-host submodule paths (``owner/repo.git``) this task's repo declares
    # in its ``.gitmodules``. The gateway persists them to
    # ``config_snapshot.submodule_paths`` at dispatch; the proxy uses them to
    # gate ``/git/r/<path>`` requests so a signed main-scope token can fetch the
    # declared submodules (and only those) but not arbitrary sibling repos.
    submodule_paths: list[str] = field(default_factory=list)


def _sign(task_id: str, scope: str, mode: str) -> str:
    key = (settings.node_control_token or "").encode("utf-8")
    digest = hmac.new(
        key,
        f"{_TOKEN_DOMAIN}:{task_id}:{scope}:{mode}".encode("utf-8"),
        hashlib.sha256,
    )
    return digest.hexdigest()[:32]


def _split_token(token: str) -> tuple[str, str, str, str]:
    """Split ``<task_id>.<scope>.<mode>.<sig>`` into its four parts.

    Returns empty strings when the shape does not match. The old 2-segment
    ``<task_id>.<sig>`` form is intentionally rejected: a re-dispatch mints the
    new shape, and accepting the legacy form would mean accepting a signature
    that does not cover scope/mode.
    """
    parts = token.split(".")
    if len(parts) != 4:
        return "", "", "", ""
    task_id, scope, mode, sig = parts
    return task_id.strip(), scope.strip(), mode.strip(), sig.strip()


def _valid_task_id(task_id: str) -> bool:
    try:
        uuid.UUID(task_id)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _valid_scope(scope: str) -> bool:
    """``main`` or a project UUID (an associated repository's project id)."""
    if scope == _SCOPE_MAIN:
        return True
    return _valid_task_id(scope)


def _parse_submodule_paths(snapshot: Any) -> list[str]:
    """Same-host submodule paths the task's repo declared in ``.gitmodules``.

    Persisted by the gateway into ``config_snapshot.submodule_paths`` as a list
    of ``owner/repo.git`` strings. Tortoise hands the JSONB column back as a
    decoded structure, but older / non-Tortoise callers (and the test fakes)
    may surface a string — accept either.
    """
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot) if snapshot else None
        except (ValueError, TypeError):
            return []
    if not isinstance(snapshot, dict):
        return []
    raw = snapshot.get("submodule_paths")
    if not isinstance(raw, list):
        return []
    paths = [str(item).strip() for item in raw if isinstance(item, (str, bytes))]
    return [p for p in paths if p]


# A ``/git/r/<repo-path>/<git-suffix>`` request: git resolves a relative
# ``.gitmodules`` url against the main clone URL (which now ends in
# ``/git/r/<parent-path>``), so a sibling submodule ``../x.git`` lands at
# ``/git/r/x.git``. The tail is one of the three smart-HTTP endpoints; anything
# in front of it is the repo path.
_R_SUFFIXES = ("git-receive-pack", "info/refs", "git-upload-pack")


def _split_r_path(suffix: str) -> tuple[str, str] | None:
    """Split ``r/<repo-path>/<tail>`` into ``(repo_path, tail)``.

    Returns ``None`` when the shape is not a submodule-style request.
    """
    rest = suffix[2:]  # strip the leading ``r/``
    for tail in _R_SUFFIXES:
        if rest == tail:
            return ("", tail)  # ``r/git-upload-pack`` — no repo path; malformed
        marker = "/" + tail
        if rest.endswith(marker):
            return (rest[: -len(tail) - 1].rstrip("/"), tail)
    return None


def _extract_token(request: Request) -> str | None:
    """Return the proxy token git placed in the Basic-auth username slot.

    A clone URL of ``http://<token>@host/...`` makes git send
    ``Authorization: Basic base64("<token>:")`` on every smart-HTTP request.
    """
    auth = (request.headers.get("authorization") or "").strip()
    if not auth.lower().startswith("basic "):
        return None
    try:
        decoded = base64.b64decode(auth[6:].strip(), validate=False).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None
    user, _sep, _password = decoded.partition(":")
    return user.strip() or None


def _auth_header(username: str | None, access_token: str | None) -> str | None:
    """Basic-auth credential for the upstream, mirroring the node's credential
    selection (token authenticates as the password half; alone it is the
    username half — the PAT-as-username form GitHub/Gitea/GitLab accept)."""
    if not access_token:
        return None
    user = (username or "").strip()
    credential = f"{user}:{access_token}" if user else f"{access_token}:"
    return "Basic " + base64.b64encode(credential.encode("utf-8")).decode("ascii")


async def _resolve(task_id: str, scope: str) -> _GitTarget:
    """Resolve task (+ scope) → repo + git identity → upstream access token.

    Only active tasks resolve; anything else is a 403 (revocation). The real
    access token lives in this request's locals only — never logged or returned
    beyond the upstream Authorization header.

    ``scope == "main"`` resolves the task's own bound repository. Any other scope
    is an associated project's id: it must be a live ``mc_project_associations``
    row whose source is the task's project, otherwise the token cannot reach it
    (403). The credential used is the SOURCE project's git identity — the same
    token whose reachability the gateway probed when it minted this scope.
    """
    from .shared_store import pool

    if pool() is None:
        raise _GitProxyError(503, "git proxy: control-plane database unavailable")

    task_uuid = uuid.UUID(task_id)
    async with pool().acquire() as conn:
        task = await conn.fetchrow(
            "SELECT status, deleted_at, config_snapshot FROM mc_tasks WHERE id=$1", task_uuid
        )
        if task is None or task["deleted_at"] is not None:
            raise _GitProxyError(403, "git proxy: task does not exist")
        if task["status"] not in _ACTIVE_TASK_STATUSES:
            # Record exactly what status blocked the clone so a future failure
            # names the cause instead of forcing a re-derivation. The most common
            # path here is the task being re-dispatched while a prior attempt's
            # terminal write (error/dispatch_failed) landed between this clone and
            # the gateway's status write — making the gap observable is the fix.
            raise _GitProxyError(
                403,
                f"git proxy: task is no longer active (status={task['status']})",
            )
        submodule_paths = _parse_submodule_paths(task.get("config_snapshot"))

        binding = await conn.fetchrow(
            "SELECT repo_url, git_identity_id, project_id FROM mc_project_tasks "
            "WHERE task_id=$1 ORDER BY created_at LIMIT 1",
            task_uuid,
        )
        if binding is None or not binding["repo_url"]:
            raise _GitProxyError(404, "git proxy: task has no bound repository")

        identity_id = binding["git_identity_id"]
        project_id = binding["project_id"]
        if identity_id is None and project_id is not None:
            project = await conn.fetchrow(
                "SELECT git_identity_id FROM mc_projects WHERE id=$1", project_id
            )
            if project is not None:
                identity_id = project["git_identity_id"]

        repo_url = str(binding["repo_url"])
        if scope != _SCOPE_MAIN:
            # Associated repository: the association must exist and originate
            # from this task's project. Without that check a node could point a
            # signed token at any project id it knows.
            if project_id is None:
                raise _GitProxyError(403, "git proxy: task has no project for an association scope")
            try:
                target_uuid = uuid.UUID(scope)
            except (ValueError, AttributeError, TypeError) as exc:
                raise _GitProxyError(403, "git proxy: malformed association scope") from exc
            assoc = await conn.fetchrow(
                "SELECT 1 FROM mc_project_associations "
                "WHERE source_project_id=$1 AND target_project_id=$2",
                project_id,
                target_uuid,
            )
            if assoc is None:
                raise _GitProxyError(403, "git proxy: project is not associated with this task")
            target_project = await conn.fetchrow(
                "SELECT repo_url FROM mc_projects WHERE id=$1", target_uuid
            )
            if target_project is None or not target_project["repo_url"]:
                raise _GitProxyError(404, "git proxy: associated project has no repository")
            repo_url = str(target_project["repo_url"])
            # Credentials stay the SOURCE project's identity (resolved above):
            # that is the token the gateway probed for reachability, and the
            # permission model the user asked for is "the source token's rights".

        username: str | None = None
        access_token: str | None = None
        if identity_id is not None:
            identity = await conn.fetchrow(
                "SELECT username, access_token FROM mc_git_identities WHERE id=$1",
                identity_id,
            )
            if identity is not None:
                username = identity["username"]
                access_token = identity["access_token"]

    return _GitTarget(
        repo_url=repo_url,
        username=username,
        access_token=access_token,
        submodule_paths=submodule_paths,
    )


def _upstream_url(repo_url: str, suffix: str, query: str) -> str:
    # Only http(s) repos can be proxied over smart HTTP. An ssh remote reaching
    # here means the dispatch side rewrote something it should not have; refuse
    # rather than build a nonsense URL.
    if not repo_url.startswith(("https://", "http://")):
        raise _GitProxyError(502, "git proxy: bound repository is not an http(s) remote")
    url = repo_url.rstrip("/") + "/" + suffix
    if query:
        url = f"{url}?{query}"
    return url


async def _forward(method: str, upstream: str, request: Request, auth: str | None):
    """Forward one smart-HTTP request and stream the upstream response back."""
    body = await request.body() if method == "POST" else None

    forward_headers = {
        k: v for k, v in request.headers.items() if k.lower() not in _REQUEST_STRIP
    }
    if auth:
        forward_headers["Authorization"] = auth

    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30.0, sock_read=300.0)
    # Smart-HTTP bytes are opaque. Keep gzip exactly as the upstream sent it:
    # auto-decompressing the body while forwarding Content-Encoding would make
    # git decode an already-decoded pack stream and corrupt the transfer.
    session = aiohttp.ClientSession(timeout=timeout, auto_decompress=False)
    try:
        resp = await session.request(method, upstream, data=body, headers=forward_headers)
    except aiohttp.ClientError as exc:
        await session.close()
        raise _GitProxyError(502, f"git proxy: upstream unreachable: {exc}") from exc
    except Exception:
        await session.close()
        raise

    resp_headers = {
        k: v for k, v in resp.headers.items() if k.lower() not in _RESPONSE_STRIP
    }

    async def stream():
        try:
            async for chunk in resp.content.iter_chunked(64 * 1024):
                yield chunk
        finally:
            resp.release()
            await session.close()

    return StreamingResponse(stream(), status_code=resp.status, headers=resp_headers)


def build_git_proxy_router() -> APIRouter:
    """Build the public ``/api/v1/public/nodes/git/*`` smart-HTTP proxy router.

    Served by the *control* service for the same reason the binaries router is:
    it is the origin the node already dials (``node_server_public_url``). The
    route is self-authenticating via the signed token, so it needs no admin
    session — safety comes from the HMAC + task-state revocation, not a login.

    Push is allowed only for a ``mode=rw`` token; the signature covers the mode
    so it cannot be self-upgraded by the node.
    """
    router = APIRouter(prefix="/api/v1/public/nodes", tags=["node-control-git-proxy"])

    @router.api_route("/git/{path:path}", methods=["GET", "POST"])
    async def git_proxy(path: str, request: Request):
        task_id = ""
        try:
            # Fail closed: without the shared control token the HMAC would be
            # keyed on an empty secret, i.e. forgeable by anyone. The dispatch
            # side refuses to mint proxy URLs in that case too.
            if not (settings.node_control_token or "").strip():
                raise _GitProxyError(503, "git proxy: control token is not configured")

            token = _extract_token(request)
            if not token:
                # Announce Basic so git retries with the URL's userinfo instead
                # of failing outright when it did not send it preemptively.
                return PlainTextResponse(
                    "git proxy: missing credentials\n",
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="git-proxy"'},
                )

            task_id, scope, mode, sig = _split_token(token)
            if not _valid_task_id(task_id) or not _valid_scope(scope) or not sig:
                raise _GitProxyError(403, "git proxy: malformed token")
            if mode not in _VALID_MODES:
                raise _GitProxyError(403, "git proxy: malformed token")
            # The signature covers scope + mode, so editing either clear-text
            # segment (e.g. ro→rw, or repointing scope) fails here.
            if not hmac.compare_digest(_sign(task_id, scope, mode), sig):
                raise _GitProxyError(403, "git proxy: invalid token")

            suffix = path.strip("/")
            if suffix.startswith("r/"):
                # Submodule-aware form: ``r/<repo-path>/<git-suffix>``. The main
                # clone URL embeds the real repo's host-relative path after
                # ``/git/r/`` (minted by the gateway), so git resolves a relative
                # ``.gitmodules`` url like ``../sibling.git`` into this same
                # namespace. Each request is validated against either the task's
                # own repo path or the ``.gitmodules``-derived allowlist the
                # gateway persisted — never against a node-supplied list.
                parsed_r = _split_r_path(suffix)
                if parsed_r is None:
                    raise _GitProxyError(404, "git proxy: unsupported git endpoint")
                repo_rel, tail = parsed_r
                if not repo_rel:
                    raise _GitProxyError(404, "git proxy: unsupported git endpoint")
                if scope != _SCOPE_MAIN:
                    # Dependency clones keep the legacy path form; ``r/`` is
                    # minted for the main repo only.
                    raise _GitProxyError(403, "git proxy: r/ path is main-scope only")
                target = await _resolve(task_id, scope)
                parent = urlparse(target.repo_url)
                if not target.repo_url.startswith(("https://", "http://")):
                    raise _GitProxyError(502, "git proxy: bound repository is not an http(s) remote")
                parent_path = (parent.path or "").strip("/")
                is_main_repo = repo_rel == parent_path
                if not is_main_repo and repo_rel not in target.submodule_paths:
                    raise _GitProxyError(
                        403,
                        "git proxy: path is not the task repository or a declared submodule",
                    )
                # A submodule fetch is read-only by construction: only the main
                # repo itself may receive pushes.
                writable = mode == _MODE_RW and is_main_repo
                if tail.startswith("git-receive-pack"):
                    if not writable:
                        raise _GitProxyError(403, "git proxy: push is not allowed (read-only token)")
                elif tail == "info/refs":
                    service = (request.query_params.get("service") or "").strip()
                    if service == "git-receive-pack":
                        if not writable:
                            raise _GitProxyError(403, "git proxy: push is not allowed (read-only token)")
                    elif service and service != "git-upload-pack":
                        raise _GitProxyError(403, "git proxy: unsupported git service")
                upstream_repo = f"{parent.scheme}://{parent.netloc}/{repo_rel}"
                upstream = _upstream_url(upstream_repo, tail, request.url.query)
                return await _forward(
                    request.method, upstream, request, _auth_header(target.username, target.access_token)
                )

            writable = mode == _MODE_RW
            if suffix.startswith("git-receive-pack"):
                if not writable:
                    raise _GitProxyError(403, "git proxy: push is not allowed (read-only token)")
            elif suffix == "info/refs":
                service = (request.query_params.get("service") or "").strip()
                if service == "git-receive-pack":
                    if not writable:
                        raise _GitProxyError(403, "git proxy: push is not allowed (read-only token)")
                elif service and service != "git-upload-pack":
                    raise _GitProxyError(403, "git proxy: unsupported git service")
            elif suffix != "git-upload-pack":
                raise _GitProxyError(404, "git proxy: unsupported git endpoint")

            target = await _resolve(task_id, scope)
            upstream = _upstream_url(target.repo_url, suffix, request.url.query)
            return await _forward(
                request.method, upstream, request, _auth_header(target.username, target.access_token)
            )
        except _GitProxyError as exc:
            return PlainTextResponse(exc.message + "\n", status_code=exc.status)
        except Exception:  # noqa: BLE001
            logger.exception("[nodeserver] git proxy failed for task {}", task_id or "<unknown>")
            return PlainTextResponse("git proxy: internal error\n", status_code=500)

    return router
