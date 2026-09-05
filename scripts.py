"""Install-script rendering for node onboarding (Python port of ``pkg/nodescripts``).

The server hosts the install scripts at ``/api/nodes/scripts/{name}`` and hands
out their URLs at onboard time. The four templates (standalone / systemd /
docker / docker-compose) live alongside this module in ``templates/`` — vendored
verbatim from the Go daemon — and use Go ``text/template`` ``{{.Var}}`` syntax.
We render them with a minimal, fixed variable substitution (no control flow is
used in these templates, so a literal replace is faithful and avoids a Go
template engine dependency).

``script_filename`` / ``parse_script_filename`` mirror the Go helpers so the
role×method URL round-trips (e.g. ``install-execution-systemd.sh``).
"""
from __future__ import annotations

import os

from .store import (
    NODE_ROLE_MANAGEMENT,
    NODE_ROLE_PASSIVE_MANAGEMENT,
    NODE_STARTUP_STANDALONE,
    normalize_node_role,
    normalize_startup_method,
)

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

_METHOD_TEMPLATE = {
    "standalone": "install-standalone.sh.tmpl",
    "systemd": "install-systemd.sh.tmpl",
    "docker": "install-docker.sh.tmpl",
    "docker-compose": "install-docker-compose.sh.tmpl",
}


def supported_methods() -> list[str]:
    return ["standalone", "systemd", "docker", "docker-compose"]


def _role_label(role: str) -> str:
    if normalize_node_role(role) in (NODE_ROLE_MANAGEMENT, NODE_ROLE_PASSIVE_MANAGEMENT):
        return "management"
    return "execution"


def _role_binary_name(role: str) -> str:
    """The on-disk binary name for a role (see ``nodes/build.sh``).

    The old single ``agent-compose-agent`` binary selected its role with a
    ``--role`` flag; the two role-specific binaries are named after their role
    and take no ``--role`` flag.
    """
    if normalize_node_role(role) in (NODE_ROLE_MANAGEMENT, NODE_ROLE_PASSIVE_MANAGEMENT):
        return "agent-compose-node-management"
    return "node-execution"


def render(
    method: str,
    *,
    role: str,
    server_url: str,
    script_url: str,
    agent_image: str = "",
    role_label: str = "",
) -> str:
    """Render the install script for ``method`` with parameters substituted.

    Raises ``ValueError`` on an unknown startup method.
    """
    method = normalize_startup_method(method) or NODE_STARTUP_STANDALONE
    template_name = _METHOD_TEMPLATE.get(method)
    if template_name is None:
        raise ValueError(f"no install script for startup method {method!r}")
    with open(os.path.join(_TEMPLATE_DIR, template_name), "r", encoding="utf-8") as fh:
        raw = fh.read()
    role = normalize_node_role(role)
    if not role_label:
        role_label = _role_label(role)
    # The templates only reference these variables via {{.Name}}; a literal
    # replace is faithful because no template control flow is used.
    substitutions = {
        "{{.Role}}": role,
        "{{.RoleLabel}}": role_label,
        "{{.BinaryName}}": _role_binary_name(role),
        "{{.ServerURL}}": server_url,
        "{{.ScriptURL}}": script_url,
        "{{.AgentImage}}": agent_image,
    }
    for token, value in substitutions.items():
        raw = raw.replace(token, value)
    return raw


def script_filename(role: str, method: str) -> str:
    """Canonical file name for a role×method install script (mirror Go)."""
    role = normalize_node_role(role)
    method = normalize_startup_method(method) or NODE_STARTUP_STANDALONE
    return f"install-{role}-{method}.sh"


def parse_script_filename(name: str) -> tuple[str, str, bool]:
    """Invert :func:`script_filename` → ``(role, method, ok)``.

    ``ok`` is False when the name is not a known ``install-<role>-<method>.sh``.
    """
    name = (name or "").strip()
    if not name.startswith("install-") or not name.endswith(".sh"):
        return "", "", False
    middle = name[len("install-"):-len(".sh")]
    dash = middle.find("-")
    if dash < 0:
        return "", "", False
    role = normalize_node_role(middle[:dash])
    method = normalize_startup_method(middle[dash + 1:])
    if not method:
        return "", "", False
    return role, method, True


def build_scripts_router(service):
    """Build the ``GET /api/nodes/scripts/{name}`` router (mirror the Go daemon's
    ``/api/nodes/scripts/:name`` endpoint).

    The URL name encodes role×method; we parse it, render the matching template
    with the server's own address + configured agent image, and return it as a
    shell script. The script is inert without a valid ``(node_id, secret)`` pair,
    so it is intentionally public (matches the Go daemon's API-token exemption for
    the scripts prefix).
    """
    from fastapi import APIRouter
    from fastapi.responses import PlainTextResponse

    router = APIRouter(tags=["agent-compose-scripts"])

    @router.get("/api/nodes/scripts/{name}")
    async def install_script(name: str):  # noqa: ANN202
        role, method, ok = parse_script_filename(name)
        if not ok:
            return PlainTextResponse(f"unknown install script {name!r}", status_code=404)
        try:
            body = render(
                method,
                role=role,
                server_url=service.server_url,
                script_url=service.script_url(role, method),
                agent_image=getattr(service, "agent_image", "") or "",
            )
        except ValueError as exc:
            return PlainTextResponse(str(exc), status_code=404)
        return PlainTextResponse(body, media_type="application/x-sh")

    return router
