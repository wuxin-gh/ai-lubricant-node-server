"""Tests for the node control service's public binary mirror.

Self-upgrade URLs and the docker one-click install scripts use the control
service's own public origin, so these routes must be mounted there rather than
only on the data service.
"""
from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from node_server import binaries


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(binaries.build_public_binaries_router())
    return TestClient(app)


def test_node_binary_is_served_from_control_plane(tmp_path, monkeypatch):
    binary = tmp_path / "node-execution-windows-amd64.exe"
    binary.write_bytes(b"windows-node-binary")
    monkeypatch.setattr(binaries, "resolve_node_bin_dir", lambda: tmp_path)

    response = _client().get(
        "/api/v1/public/nodes/binaries/node-execution-windows-amd64.exe"
    )

    assert response.status_code == 200
    assert response.content == b"windows-node-binary"
    assert "node-execution-windows-amd64.exe" in response.headers["content-disposition"]


def test_versioned_release_directory_is_selected(tmp_path, monkeypatch):
    older = tmp_path / "20260812-1200"
    newer = tmp_path / "20260813-1138"
    older.mkdir()
    newer.mkdir()
    (older / "node-execution-windows-amd64.exe").write_bytes(b"old")
    (newer / "node-execution-windows-amd64.exe").write_bytes(b"new")
    # Make the selection deterministic without relying on filesystem mtime
    # resolution: the release version is also the lexical order key.
    monkeypatch.setattr(binaries, "_default_candidates", lambda: [tmp_path])

    assert binaries.resolve_node_bin_dir() == newer
    assert binaries.resolve_node_binary("node-execution-windows-amd64.exe") == (
        newer / "node-execution-windows-amd64.exe"
    )
    assert binaries.latest_node_version() == "20260813-1138"


def test_missing_or_non_whitelisted_binary_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(binaries, "resolve_node_bin_dir", lambda: tmp_path)
    client = _client()

    missing = client.get(
        "/api/v1/public/nodes/binaries/node-execution-linux-amd64"
    )
    disallowed = client.get("/api/v1/public/nodes/binaries/config.json")

    assert missing.status_code == 404
    assert disallowed.status_code == 404


def test_binary_path_traversal_is_rejected(tmp_path, monkeypatch):
    outside = tmp_path.parent / ".env"
    outside.write_text("NODE_CONTROL_TOKEN=must-not-leak", encoding="utf-8")
    monkeypatch.setattr(binaries, "resolve_node_bin_dir", lambda: tmp_path)
    client = _client()

    for name in ("../../.env", "%2e%2e%2f%2e%2e%2f.env", "sub/config.json"):
        response = client.get(f"/api/v1/public/nodes/binaries/{name}")
        assert response.status_code == 404, name
        assert "must-not-leak" not in response.text


def test_docker_artifacts_are_served_from_control_plane():
    client = _client()

    dockerfile = client.get("/api/v1/public/nodes/docker/Dockerfile")
    assert dockerfile.status_code == 200
    assert "node-execution" in dockerfile.text
    assert "agent-compose-node-management" in dockerfile.text

    entrypoint = client.get("/api/v1/public/nodes/docker/entrypoint.sh")
    assert entrypoint.status_code == 200
    assert "AGENT_COMPOSE_NODE_ROLE" in entrypoint.text

    # Both artifacts feed `docker build` on a Linux host: a single CR (Windows
    # autocrlf checkout) in the shebang breaks exec inside the image.
    assert "\r" not in dockerfile.text
    assert "\r" not in entrypoint.text


def test_docker_artifacts_are_normalized_to_lf(tmp_path, monkeypatch):
    """A CRLF working tree (Windows checkout of the nodes submodule) must never
    reach the wire: the entrypoint's shebang would become ``#!/bin/sh\\r`` and
    the container dies in a restart loop with "No such file or directory"."""
    (tmp_path / "Dockerfile").write_bytes(b"FROM alpine:3.22\r\nRUN true\r\n")
    (tmp_path / "entrypoint.sh").write_bytes(b"#!/bin/sh\r\nexec /bin/true\r\n")
    monkeypatch.setattr(binaries, "_DOCKER_DIR", tmp_path)
    client = _client()

    for name, expected in (
        ("Dockerfile", "FROM alpine:3.22\nRUN true\n"),
        ("entrypoint.sh", "#!/bin/sh\nexec /bin/true\n"),
    ):
        response = client.get(f"/api/v1/public/nodes/docker/{name}")
        assert response.status_code == 200, name
        assert b"\r" not in response.content, name
        assert response.text == expected, name
        assert f'filename="{name}"' in response.headers["content-disposition"]


def test_non_whitelisted_docker_artifact_is_rejected():
    client = _client()

    response = client.get("/api/v1/public/nodes/docker/config.json")

    assert response.status_code == 404
    assert "not found" in response.text.lower()


# ── ios_host role / node-ios binary ──────────────────────────────────────────
# The iOS host registers as its own role (ios_host) and ships as its own binary
# (node-ios-*). self-upgrade derives the download filename purely from the
# role via binary_name_for, so ios_host MUST map to node-ios-* — falling through
# to node-execution would download the wrong program and clobber the host on
# restart. These guard that mapping and the whitelist/parse paths around it.

def test_binary_name_for_ios_host_maps_to_node_ios():
    assert binaries.binary_name_for("ios_host", "linux", "amd64") == "node-ios-linux-amd64"
    assert binaries.binary_name_for("ios_host", "windows", "amd64") == "node-ios-windows-amd64.exe"
    assert binaries.binary_name_for("ios_host", "darwin", "arm64") == "node-ios-darwin-arm64"


def test_binary_name_for_legacy_roles_unchanged():
    # Regression guard: ios_host must not perturb the existing role → name map.
    assert binaries.binary_name_for("execution", "linux", "amd64") == "node-execution-linux-amd64"
    assert binaries.binary_name_for("management", "windows", "amd64") == (
        "agent-compose-node-management-windows-amd64.exe"
    )
    assert binaries.binary_name_for("passive_management", "linux", "arm64") == (
        "agent-compose-node-management-linux-arm64"
    )
    assert binaries.binary_name_for("", "linux", "amd64") == "node-execution-linux-amd64"


def test_node_ios_binary_is_whitelisted_and_parsed(tmp_path, monkeypatch):
    binary = tmp_path / "node-ios-darwin-arm64"
    binary.write_bytes(b"ios-host-binary")
    monkeypatch.setattr(binaries, "resolve_node_bin_dir", lambda: tmp_path)

    response = _client().get("/api/v1/public/nodes/binaries/node-ios-darwin-arm64")
    assert response.status_code == 200
    assert response.content == b"ios-host-binary"

    # _parse_platform must read os/arch off the node-ios name, not return blank.
    assert binaries._parse_platform("node-ios-darwin-arm64") == ("darwin", "arm64")
    assert binaries._parse_platform("node-ios-windows-amd64.exe") == ("windows", "amd64")

