"""Server-side git smart-HTTP proxy: auth, task revocation, read-only, forwarding.

These exercise the router built by ``node_server.git_proxy`` against a stubbed
asyncpg pool (raw-SQL task/identity resolution) and a stubbed ``aiohttp``
client (upstream forwarding), so no live Postgres / git host is needed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from types import SimpleNamespace
from typing import Any

import aiohttp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import node_server.git_proxy as git_proxy_mod
from node_server.git_proxy import build_git_proxy_router

CONTROL_TOKEN = "control-secret"
ORIGIN = "http://127.0.0.1:8003"


def _mint(task_id: str, scope: str = "main", mode: str = "ro") -> str:
    """Mirror ``monkeycode_compat.task_service._git_proxy_token``'s 4-segment form."""
    sig = hmac.new(
        CONTROL_TOKEN.encode(),
        f"git-proxy:{task_id}:{scope}:{mode}".encode(),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"{task_id}.{scope}.{mode}.{sig}"


def _basic_auth(username: str, password: str = "") -> str:
    return "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode("ascii")


# --- stubs ----------------------------------------------------------------

class _FakeConn:
    """asyncpg-like connection returning queued rows in call order."""

    def __init__(self, rows: list[dict | None]):
        self._rows = list(rows)

    async def fetchrow(self, query: str, *params: Any):
        if self._rows:
            return self._rows.pop(0)
        return None


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def acquire(self):
        conn = self._conn

        class _Ctx:
            async def __aenter__(self_inner):
                return conn

            async def __aexit__(self_inner, *exc):
                return False

        return _Ctx()


class _FakeResponse:
    def __init__(self, *, status: int = 200, headers: dict | None = None, body: bytes = b""):
        self.status = status
        self.headers = headers or {"Content-Type": "application/x-git-upload-pack-result"}
        self._body = body
        self.released = False

    @property
    def content(self):
        return self

    async def iter_chunked(self, _n: int):
        if self._body:
            yield self._body

    def release(self):
        self.released = True


class _FakeSession:
    """Stand-in for ``aiohttp.ClientSession``: records the upstream request
    and returns (or raises) a canned response. ``_forward`` constructs it via
    ``aiohttp.ClientSession(timeout=...)``; we monkeypatch that symbol to return
    one of these so no real network is touched."""

    def __init__(self, response: _FakeResponse | Exception):
        self._response = response
        self.calls: list[dict] = []
        self.closed = False

    async def request(self, method, url, data=None, headers=None):
        self.calls.append({"method": method, "url": url, "data": data, "headers": dict(headers or {})})
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    async def close(self):
        self.closed = True


def _make_client(monkeypatch, *, rows, response, control_token=CONTROL_TOKEN):
    conn = _FakeConn(rows)
    monkeypatch.setattr(
        git_proxy_mod, "settings", SimpleNamespace(node_control_token=control_token)
    )
    monkeypatch.setattr("node_server.shared_store._pool", _FakePool(conn))

    fake_session = _FakeSession(response)
    monkeypatch.setattr(git_proxy_mod.aiohttp, "ClientSession", lambda **kw: fake_session)

    app = FastAPI()
    app.include_router(build_git_proxy_router())
    return TestClient(app), fake_session


# --- tests ----------------------------------------------------------------

def test_missing_credentials_returns_401(monkeypatch):
    client, _ = _make_client(monkeypatch, rows=[], response=_FakeResponse())
    r = client.get("/api/v1/public/nodes/git/info/refs?service=git-upload-pack")
    assert r.status_code == 401


def test_tampered_token_returns_403(monkeypatch):
    client, _ = _make_client(monkeypatch, rows=[{"status": "pending", "deleted_at": None}], response=_FakeResponse())
    tid = str(uuid.uuid4())
    bad_token = f"{tid}.main.ro.deadbeef"
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(bad_token)},
    )
    assert r.status_code == 403


def test_legacy_two_segment_token_is_rejected(monkeypatch):
    """The old ``<task_id>.<sig>`` form has no scope/mode under its signature."""
    client, _ = _make_client(monkeypatch, rows=[{"status": "pending", "deleted_at": None}], response=_FakeResponse())
    tid = str(uuid.uuid4())
    legacy_sig = hmac.new(
        CONTROL_TOKEN.encode(), f"git-proxy:{tid}".encode(), hashlib.sha256
    ).hexdigest()[:32]
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(f"{tid}.{legacy_sig}")},
    )
    assert r.status_code == 403


def test_mode_promotion_is_rejected(monkeypatch):
    """Editing ``ro`` → ``rw`` in the clear-text segment must break the HMAC."""
    client, _ = _make_client(monkeypatch, rows=[{"status": "pending", "deleted_at": None}], response=_FakeResponse())
    tid = str(uuid.uuid4())
    ro_token = _mint(tid, "main", "ro")
    forged = ro_token.replace(".ro.", ".rw.", 1)
    r = client.post(
        "/api/v1/public/nodes/git/git-receive-pack",
        headers={"Authorization": _basic_auth(forged)},
        content=b"",
    )
    assert r.status_code == 403
    assert "invalid token" in r.text


def test_push_is_forbidden_for_read_only_token(monkeypatch):
    client, _ = _make_client(monkeypatch, rows=[], response=_FakeResponse())
    tid = str(uuid.uuid4())
    r = client.post(
        "/api/v1/public/nodes/git/git-receive-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "ro"))},
        content=b"",
    )
    assert r.status_code == 403
    assert "read-only" in r.text


def test_push_is_allowed_for_rw_token(monkeypatch):
    tid = str(uuid.uuid4())
    rows = [
        {"status": "processing", "deleted_at": None},
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": uuid.uuid4(), "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse(body=b"unpack ok"))
    r = client.post(
        "/api/v1/public/nodes/git/git-receive-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "rw"))},
        content=b"0000",
    )
    assert r.status_code == 200
    assert session.calls[-1]["url"] == "https://gitea.example.com/o/r.git/git-receive-pack"


def test_info_refs_for_receive_pack_service_is_forbidden(monkeypatch):
    client, _ = _make_client(monkeypatch, rows=[], response=_FakeResponse())
    tid = str(uuid.uuid4())
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-receive-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "ro"))},
    )
    assert r.status_code == 403


def test_info_refs_for_receive_pack_allowed_with_rw(monkeypatch):
    tid = str(uuid.uuid4())
    rows = [
        {"status": "pending", "deleted_at": None},
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": None, "project_id": None},
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse(body=b"refs"))
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-receive-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "rw"))},
    )
    assert r.status_code == 200
    assert session.calls[-1]["url"].endswith("/info/refs?service=git-receive-pack")


# --- association scope ----------------------------------------------------

def test_association_scope_resolves_target_repo(monkeypatch):
    """A scoped token clones the ASSOCIATED project's repo, authenticating with
    the source project's identity."""
    tid = str(uuid.uuid4())
    source_project = uuid.uuid4()
    target_project = uuid.uuid4()
    rows = [
        {"status": "pending", "deleted_at": None},
        # task binding: source project + its own repo
        {"repo_url": "https://git.example.com/src/main.git", "git_identity_id": uuid.uuid4(), "project_id": source_project},
        # association exists
        {"1": 1},
        # target project repo
        {"repo_url": "https://git.example.com/dep/lib.git"},
        # source identity
        {"username": "bot", "access_token": "src-pat"},
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse(body=b"refs"))
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid, str(target_project), "rw"))},
    )
    assert r.status_code == 200
    # Upstream is the TARGET repo, not the task's main repo.
    assert session.calls[-1]["url"].startswith("https://git.example.com/dep/lib.git/")
    # Credential is the SOURCE project's identity.
    assert session.calls[-1]["headers"]["Authorization"] == _basic_auth("bot", "src-pat")


def test_unassociated_scope_is_forbidden(monkeypatch):
    """A signed token pointing at a project that is NOT associated must 403 —
    the signature alone does not authorize an arbitrary project id."""
    tid = str(uuid.uuid4())
    source_project = uuid.uuid4()
    other_project = uuid.uuid4()
    rows = [
        {"status": "pending", "deleted_at": None},
        {"repo_url": "https://git.example.com/src/main.git", "git_identity_id": uuid.uuid4(), "project_id": source_project},
        None,  # association lookup finds nothing
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse())
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid, str(other_project), "rw"))},
    )
    assert r.status_code == 403
    assert "not associated" in r.text
    assert session.calls == []


def test_finished_task_is_revoked(monkeypatch):
    client, _ = _make_client(
        monkeypatch,
        rows=[{"status": "finished", "deleted_at": None}],
        response=_FakeResponse(),
    )
    tid = str(uuid.uuid4())
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )
    assert r.status_code == 403
    assert "no longer active" in r.text


def test_deleted_task_is_revoked(monkeypatch):
    client, _ = _make_client(
        monkeypatch,
        rows=[{"status": "pending", "deleted_at": "2026-01-01T00:00:00+00:00"}],
        response=_FakeResponse(),
    )
    tid = str(uuid.uuid4())
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )
    assert r.status_code == 403


def test_unknown_endpoint_returns_404(monkeypatch):
    client, _ = _make_client(monkeypatch, rows=[{"status": "pending", "deleted_at": None}], response=_FakeResponse())
    tid = str(uuid.uuid4())
    r = client.get(
        "/api/v1/public/nodes/git/objects/abc",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )
    assert r.status_code == 404


def test_active_task_with_identity_forwards_with_basic_auth_and_streams_body(monkeypatch):
    tid = str(uuid.uuid4())
    rows = [
        {"status": "pending", "deleted_at": None},
        {
            "repo_url": "https://gitea.example.com/owner/repo.git",
            "git_identity_id": uuid.uuid4(),
            "project_id": None,
        },
        {"username": "bot", "access_token": "pat-real"},
    ]
    upstream_body = b"PACK" * 1024  # > one chunk threshold; must stream unchanged
    fake_resp = _FakeResponse(status=200, body=upstream_body)
    client, session = _make_client(monkeypatch, rows=rows, response=fake_resp)

    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )

    assert r.status_code == 200
    assert r.content == upstream_body
    # Upstream was called at the repo's info/refs path, query preserved.
    call = session.calls[-1]
    assert call["url"] == "https://gitea.example.com/owner/repo.git/info/refs?service=git-upload-pack"
    # The identity's real PAT is injected as Basic auth (user:pat), NOT the
    # proxy token: the node's Authorization header must not leak upstream.
    assert call["headers"]["Authorization"] == _basic_auth("bot", "pat-real")
    assert "git-proxy" not in call["headers"]["Authorization"]


def test_task_with_no_identity_forwards_without_auth(monkeypatch):
    """A task whose binding has no git identity (public repo) still resolves,
    and the proxy forwards without an Authorization header — no injection."""
    tid = str(uuid.uuid4())
    rows = [
        {"status": "processing", "deleted_at": None},
        {
            "repo_url": "https://example.com/open/repo.git",
            "git_identity_id": None,
            "project_id": None,
        },
    ]
    fake_resp = _FakeResponse(status=200, body=b"refs")
    client, session = _make_client(monkeypatch, rows=rows, response=fake_resp)

    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )
    assert r.status_code == 200
    call = session.calls[-1]
    assert "Authorization" not in call["headers"]


def test_project_identity_fallback(monkeypatch):
    """A binding with no direct git_identity_id falls back to the project's."""
    tid = str(uuid.uuid4())
    project_id = uuid.uuid4()
    rows = [
        {"status": "pending", "deleted_at": None},
        {"repo_url": "https://git.example.com/p/r.git", "git_identity_id": None, "project_id": project_id},
        {"git_identity_id": uuid.uuid4()},  # project row
        {"username": "", "access_token": "fallback-pat"},  # identity row
    ]
    fake_resp = _FakeResponse(status=200, body=b"ok")
    client, session = _make_client(monkeypatch, rows=rows, response=fake_resp)

    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )
    assert r.status_code == 200
    # No username → token-as-username form (pat: empty password).
    assert session.calls[-1]["headers"]["Authorization"] == _basic_auth("fallback-pat", "")


def test_post_upload_pack_body_forwarded_unchanged(monkeypatch):
    tid = str(uuid.uuid4())
    rows = [
        {"status": "pending", "deleted_at": None},
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": uuid.uuid4(), "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    fake_resp = _FakeResponse(status=200, body=b"pack-result")
    client, session = _make_client(monkeypatch, rows=rows, response=fake_resp)

    want_body = b"0032want 000000000000000000000000000000000000000a0000"
    r = client.post(
        "/api/v1/public/nodes/git/git-upload-pack",
        headers={
            "Authorization": _basic_auth(_mint(tid)),
            "Content-Type": "application/x-git-upload-pack-request",
        },
        content=want_body,
    )
    assert r.status_code == 200
    assert r.content == b"pack-result"
    call = session.calls[-1]
    assert call["method"] == "POST"
    assert call["url"] == "https://gitea.example.com/o/r.git/git-upload-pack"
    assert call["data"] == want_body
    assert call["headers"]["content-type"] == "application/x-git-upload-pack-request"


def test_upstream_unreachable_returns_502(monkeypatch):
    tid = str(uuid.uuid4())
    rows = [
        {"status": "pending", "deleted_at": None},
        {"repo_url": "https://down.example.com/r.git", "git_identity_id": uuid.uuid4(), "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    client, session = _make_client(
        monkeypatch, rows=rows, response=aiohttp.ClientError("connection refused")
    )
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )
    assert r.status_code == 502
    assert "upstream unreachable" in r.text


def test_database_unavailable_returns_503(monkeypatch):
    tid = str(uuid.uuid4())
    client, _ = _make_client(monkeypatch, rows=[], response=_FakeResponse())
    # pool present but None-ish: simulate by clearing the pool after setup.
    import node_server.shared_store as shared_store

    monkeypatch.setattr(shared_store, "_pool", None)
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )
    assert r.status_code == 503


def test_missing_control_token_fails_closed(monkeypatch):
    """With no shared control token the HMAC key would be empty — forgeable.

    The proxy must refuse outright rather than validate signatures keyed on "".
    """
    client, _ = _make_client(
        monkeypatch,
        rows=[{"status": "pending", "deleted_at": None}],
        response=_FakeResponse(),
        control_token="",
    )
    tid = str(uuid.uuid4())
    # A token forged with the empty key would verify if the guard were missing.
    forged = f"{tid}.main.ro." + hmac.new(
        b"", f"git-proxy:{tid}:main:ro".encode(), hashlib.sha256
    ).hexdigest()[:32]
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(forged)},
    )
    assert r.status_code == 503
    assert "control token" in r.text


def test_non_http_repo_is_refused(monkeypatch):
    """An ssh remote cannot be proxied over smart HTTP; refuse rather than
    build a nonsense upstream URL."""
    tid = str(uuid.uuid4())
    rows = [
        {"status": "pending", "deleted_at": None},
        {"repo_url": "git@github.com:owner/repo.git", "git_identity_id": uuid.uuid4(), "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse())
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid))},
    )
    assert r.status_code == 502
    assert session.calls == []


def test_inbound_proxy_token_is_not_replayed_upstream(monkeypatch):
    """Hop-by-hop + inbound Authorization must be stripped before forwarding.

    Without this the node's proxy token would travel to the real git host.
    """
    tid = str(uuid.uuid4())
    rows = [
        {"status": "pending", "deleted_at": None},
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": None, "project_id": None},
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse(body=b"refs"))
    token = _mint(tid)
    r = client.get(
        "/api/v1/public/nodes/git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(token), "Connection": "keep-alive"},
    )
    assert r.status_code == 200
    headers = session.calls[-1]["headers"]
    lowered = {k.lower(): v for k, v in headers.items()}
    assert "authorization" not in lowered
    assert "connection" not in lowered
    assert token not in "".join(headers.values())


# --- submodule-aware r/ route -------------------------------------------

def _task_row(*, snapshot=None):
    row = {"status": "pending", "deleted_at": None}
    if snapshot is not None:
        row["config_snapshot"] = snapshot
    return row


def test_main_repo_via_r_form_forwards_to_upstream(monkeypatch):
    """The gateway embeds the real repo path after ``/git/r/``; the main-repo
    fetch now arrives as ``r/o/r.git/info/refs`` and must reach the upstream."""
    tid = str(uuid.uuid4())
    rows = [
        _task_row(),
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": uuid.uuid4(), "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse(body=b"refs"))
    r = client.get(
        "/api/v1/public/nodes/git/r/o/r.git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "ro"))},
    )
    assert r.status_code == 200, r.text
    assert session.calls[-1]["url"] == "https://gitea.example.com/o/r.git/info/refs?service=git-upload-pack"
    assert session.calls[-1]["headers"]["Authorization"] == _basic_auth("bot", "pat-real")


def test_declared_submodule_via_r_form_is_allowed(monkeypatch):
    """A path the repo's ``.gitmodules`` declares fetches that submodule with
    the main repo's identity — no separate association row needed."""
    tid = str(uuid.uuid4())
    rows = [
        _task_row(snapshot={"submodule_paths": ["o/lib.git"]}),
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": uuid.uuid4(), "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse(body=b"refs"))
    r = client.get(
        "/api/v1/public/nodes/git/r/o/lib.git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "ro"))},
    )
    assert r.status_code == 200, r.text
    assert session.calls[-1]["url"].startswith("https://gitea.example.com/o/lib.git/")


def test_undeclared_submodule_path_is_forbidden(monkeypatch):
    """Without an entry in the persisted allowlist, an ``r/`` path must 403 —
    a signed main token cannot reach an arbitrary sibling repo."""
    tid = str(uuid.uuid4())
    rows = [
        _task_row(snapshot={"submodule_paths": ["o/lib.git"]}),
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": None, "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    client, _ = _make_client(monkeypatch, rows=rows, response=_FakeResponse())
    r = client.get(
        "/api/v1/public/nodes/git/r/o/secret.git/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "rw"))},
    )
    assert r.status_code == 403
    assert "declared submodule" in r.text


def test_push_to_submodule_path_is_forbidden_even_with_rw_token(monkeypatch):
    """A submodule fetch is read-only; push targets only the main repo path."""
    tid = str(uuid.uuid4())
    rows = [
        _task_row(snapshot={"submodule_paths": ["o/lib.git"]}),
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": None, "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    client, _ = _make_client(monkeypatch, rows=rows, response=_FakeResponse())
    r = client.post(
        "/api/v1/public/nodes/git/r/o/lib.git/git-receive-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "rw"))},
        content=b"",
    )
    assert r.status_code == 403
    assert "read-only" in r.text


def test_push_to_main_via_r_form_allowed_with_rw(monkeypatch):
    """Pushing the main repo through the ``r/`` form obeys the same rw rule."""
    tid = str(uuid.uuid4())
    rows = [
        _task_row(),
        {"repo_url": "https://gitea.example.com/o/r.git", "git_identity_id": None, "project_id": None},
        {"username": "bot", "access_token": "pat-real"},
    ]
    client, session = _make_client(monkeypatch, rows=rows, response=_FakeResponse(body=b"unpack ok"))
    r = client.post(
        "/api/v1/public/nodes/git/r/o/r.git/git-receive-pack",
        headers={"Authorization": _basic_auth(_mint(tid, "main", "rw"))},
        content=b"0000",
    )
    assert r.status_code == 200, r.text
    assert session.calls[-1]["url"].endswith("/o/r.git/git-receive-pack")


def test_r_form_with_association_scope_is_forbidden(monkeypatch):
    """``r/`` is minted for the main scope only — a dep token must not use it."""
    tid = str(uuid.uuid4())
    target_project = uuid.uuid4()
    rows = [
        _task_row(),
        {"repo_url": "https://git.example.com/src/main.git", "git_identity_id": uuid.uuid4(),
         "project_id": uuid.uuid4()},
    ]
    client, _ = _make_client(monkeypatch, rows=rows, response=_FakeResponse())
    r = client.get(
        "/api/v1/public/nodes/git/r/anything/info/refs?service=git-upload-pack",
        headers={"Authorization": _basic_auth(_mint(tid, str(target_project), "rw"))},
    )
    assert r.status_code == 403
    assert "main-scope" in r.text
