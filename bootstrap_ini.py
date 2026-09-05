"""Thin dotenv persistence shim for the node control service.

Historically this read/wrote the root ``env.ini``; it now delegates to the
shared ``dotenv_loader`` so generated secrets are persisted to ``.env``.
"""
from __future__ import annotations

from . import dotenv_loader


def update_ini_section(section: str, values: dict[str, str]) -> None:
    """Persist ``values`` to ``.env``.

    ``section`` is retained for call-site compatibility (the control service
    still passes ``"ai_lubricant"``) but is not used: dotenv stores flat
    ``KEY=VALUE`` pairs with no sections.
    """
    dotenv_loader.update_env_vars(values, path=dotenv_loader.ENV_FILE)
