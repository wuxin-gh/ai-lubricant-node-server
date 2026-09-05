"""Bridge node heartbeat tool-run inventories into tunnel runtime reconciliation.

The node-server process and data service are separate, so the heartbeat itself
cannot query ``mc_tunnel_runtimes``. Instead it keeps the latest per-node
inventory in this process and exposes it through the existing JSON unary API;
the data service polls that lightweight endpoint during runtime reconciliation.
"""
from __future__ import annotations

from typing import Any


def node_tool_runs(service, node_id: str) -> list[dict[str, Any]]:
    conn = service.registry.lookup((node_id or "").strip())
    if conn is None or conn.closed:
        return []
    return conn.active_tool_runs()
