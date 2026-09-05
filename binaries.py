"""Node binary lookup helpers copied for the independent control service."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .store import (
    NODE_ROLE_MANAGEMENT,
    NODE_ROLE_PASSIVE_MANAGEMENT,
    NODE_ROLE_IOS_HOST,
    normalize_node_role,
)
from .config import settings

_NODE_BIN_NAME_RE = re.compile(
    r"^(node-execution-(?:linux|darwin|windows)-(?:amd64|arm64)(?:\.exe)?|"
    r"agent-compose-node-management-(?:linux|darwin|windows)-(?:amd64|arm64)(?:\.exe)?|"
    r"node-ios-(?:linux|darwin|windows)-(?:amd64|arm64)(?:\.exe)?|"
    r"agent-compose-runtime-(?:linux|darwin|windows)-(?:amd64|arm64)\.tar\.gz|"
    r"checksums-sha256\.txt|runtime-checksums-sha256\.txt|runtime-VERSION)$"
)


def _default_candidates() -> list[Path]:
    root = Path(__file__).resolve().parent.parent
    return [root / "nodes" / "dist", root / "node-bin", root.parent / "agent-compose" / "dist"]


def _resolve_candidate_root(root: Path) -> Path | None:
    """Resolve a flat bin dir or the newest versioned release subdirectory."""
    if not root.is_dir():
        return None
    if any(entry.is_file() and _NODE_BIN_NAME_RE.match(entry.name) for entry in root.iterdir()):
        return root
    version_dirs = [
        entry
        for entry in root.iterdir()
        if entry.is_dir()
        and any(
            child.is_file() and _NODE_BIN_NAME_RE.match(child.name)
            for child in entry.iterdir()
        )
    ]
    if not version_dirs:
        return None
    return max(version_dirs, key=lambda entry: (entry.stat().st_mtime, entry.name))


def resolve_node_bin_dir() -> Path | None:
    configured = (settings.agent_compose_node_bin_dir or "").strip()
    if configured:
        return _resolve_candidate_root(Path(configured).expanduser())
    for candidate in _default_candidates():
        resolved = _resolve_candidate_root(candidate)
        if resolved is not None:
            return resolved
    return None


def _parse_platform(name: str) -> tuple[str, str]:
    match = re.match(
        r"^(?:node-execution|agent-compose-node-management|node-ios)-(linux|darwin|windows)-(amd64|arm64)(?:\.exe)?$",
        name,
    )
    return (match.group(1), match.group(2)) if match else ("", "")


def list_node_binaries() -> list[dict]:
    root = resolve_node_bin_dir()
    if root is None:
        return []
    out = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if not path.is_file() or not _NODE_BIN_NAME_RE.match(path.name):
            continue
        os_name, arch = _parse_platform(path.name)
        out.append({"name": path.name, "size": path.stat().st_size, "os": os_name, "arch": arch,
                    "url": f"/api/v1/public/nodes/binaries/{path.name}"})
    return out


def resolve_node_binary(name: str) -> Path | None:
    if not name or not _NODE_BIN_NAME_RE.match(name):
        return None
    root = resolve_node_bin_dir()
    if root is None:
        return None
    candidate = (root / Path(name).name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def latest_node_version() -> str:
    root = resolve_node_bin_dir()
    if root is None:
        return ""
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        # pack-release.sh uses dist/<version>/ and stamps that directory name
        # into the binaries instead of writing a VERSION file beside them.
        return root.name if root.name and root.name != "dist" else ""


def _checksum_for(name: str, manifest_name: str) -> str:
    root = resolve_node_bin_dir()
    if root is None or not name:
        return ""
    checksums = root / manifest_name
    try:
        for line in checksums.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[-1].lstrip("*") == name:
                return parts[0].strip()
    except OSError:
        pass
    path = resolve_node_binary(name)
    if path is None:
        return ""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def node_binary_sha256(name: str) -> str:
    return _checksum_for(name, "checksums-sha256.txt")


def runtime_binary_sha256(name: str) -> str:
    return _checksum_for(name, "runtime-checksums-sha256.txt")


def latest_runtime_version() -> str:
    root = resolve_node_bin_dir()
    if root is None:
        return ""
    try:
        return (root / "runtime-VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def runtime_binary_name(os_name: str, arch: str) -> str:
    name = f"agent-compose-runtime-{os_name}-{arch}.tar.gz"
    if not _NODE_BIN_NAME_RE.match(name):
        raise ValueError(f"unsupported runtime platform: {os_name}/{arch}")
    return name


def binary_name_for(role: str, os_name: str, arch: str) -> str:
    role_norm = normalize_node_role(role)
    if role_norm == NODE_ROLE_IOS_HOST:
        # The iOS host is its own binary. Falling through to node-execution here
        # would make self-upgrade download the wrong program and clobber the host
        # on restart, since the legacy upgrade path derives the filename purely
        # from the role (the frontend's upgrade button sends no explicit target).
        base = "node-ios"
    elif role_norm in (NODE_ROLE_MANAGEMENT, NODE_ROLE_PASSIVE_MANAGEMENT):
        base = "agent-compose-node-management"
    else:
        base = "node-execution"
    name = f"{base}-{os_name}-{arch}{'.exe' if os_name == 'windows' else ''}"
    if not _NODE_BIN_NAME_RE.match(name):
        raise ValueError(f"unsupported node platform: {os_name}/{arch}")
    return name


# Node image build artifacts served to the docker/docker-compose one-click
# installer so a fresh host can ``docker build`` the shared node image locally
# (no registry push). Whitelisted filenames only; the directory is fixed.
_DOCKER_DIR = Path(__file__).resolve().parent.parent / "nodes" / "docker"
_DOCKER_FILES = frozenset({"Dockerfile", "entrypoint.sh"})


def resolve_docker_artifact(file: str) -> Path | None:
    """Resolve one whitelisted node-image build artifact, or ``None``.

    Mirrors :func:`resolve_node_binary`'s safety shape: an exact-name whitelist
    plus a ``relative_to`` re-check so a crafted name cannot walk out of the
    fixed docker directory even if the whitelist were later widened.
    """
    name = (file or "").strip()
    if name not in _DOCKER_FILES:
        return None
    candidate = (_DOCKER_DIR / name).resolve()
    try:
        candidate.relative_to(_DOCKER_DIR.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def build_public_binaries_router():
    """Build the public ``/api/v1/public/nodes/{binaries,docker}/*`` router.

    These must be served by the *control* service because that is the origin a
    node is already connected to: ``NodeService.self_upgrade_node`` hands the
    node ``{server_url}/api/v1/public/nodes/binaries/{name}`` (see
    ``service.py``), and the rendered install scripts curl the same prefix off
    their ``ServerURL``. Without this router those URLs 404 and every
    self-upgrade / docker one-click install fails.

    Public (no token) for the same reason the install scripts are: a node
    machine has no admin session. Safety comes from the basename whitelists and
    directory-escape re-checks in the resolvers, not from auth.
    """
    from fastapi import APIRouter
    from fastapi.responses import FileResponse, PlainTextResponse

    router = APIRouter(prefix="/api/v1/public/nodes", tags=["node-control-public"])

    @router.get("/binaries/{name}")
    async def download_node_binary(name: str):  # noqa: ANN202
        """Stream one role binary (or the checksums file) by basename."""
        path = resolve_node_binary(name)
        if path is None:
            return PlainTextResponse("node binary not found\n", status_code=404)
        return FileResponse(
            path,
            filename=path.name,
            media_type="application/octet-stream",
            content_disposition_type="attachment",
        )

    @router.get("/docker/{file}")
    async def download_node_docker_file(file: str):  # noqa: ANN202
        """Stream one node-image build artifact (Dockerfile / entrypoint.sh)."""
        path = resolve_docker_artifact(file)
        if path is None:
            return PlainTextResponse("node docker artifact not found\n", status_code=404)
        return FileResponse(
            path,
            filename=path.name,
            media_type="application/octet-stream",
            content_disposition_type="attachment",
        )

    return router
