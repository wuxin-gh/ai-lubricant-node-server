"""Run the standalone node control service with Hypercorn + h2c."""
from __future__ import annotations

import asyncio

from .dotenv_loader import load_project_env

load_project_env()

from .config import settings


async def _serve() -> None:
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    from . import hypercorn_h2_patch
    from .app import app

    hypercorn_h2_patch.apply()
    cfg = Config()
    cfg.bind = [f"{settings.host}:{settings.port}"]
    cfg.alpn_protocols = ["h2", "http/1.1"]
    cfg.keep_alive_timeout = 3600
    await serve(app, cfg)


if __name__ == "__main__":
    asyncio.run(_serve())
