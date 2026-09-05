"""Standalone node control service.

Self-contained package: owns NodeConnect (h2c), the live Registry, terminals,
tunnels, session streams, node proxy, and the token-gated internal control RPCs.
It must not import the data service (``monkeycode_compat``, ``shared_init``,
root ``config`` / ``db`` / ``rd``, ``providers``). Run with ``python -m node_server``.
"""
