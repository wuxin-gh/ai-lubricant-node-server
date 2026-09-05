"""FastAPI application and lifecycle for the standalone node control service."""
from __future__ import annotations

from contextlib import asynccontextmanager

from loguru import logger

from fastapi import FastAPI

from .database import close_database, init_database
from .wiring import get_service, mount, start_reaper, stop_reaper


async def _init_shared_config_store() -> None:
    """Initialize the shared PostgreSQL pool for task/config-domain rows.

    The node control service runs as its own process with a Tortoise-only
    ledger (``init_database``). But its onboarding / proxy-binding handlers and
    its task-stage/finalize writers reach the data service's domain rows
    (``mc_tasks``, ``app_config``, ``mc_notify_outbox``, …) over raw SQL. This
    pool is that reach; it lives in :mod:`.shared_store` and imports nothing
    from the data service.
    """
    from . import shared_store
    from .config import settings

    try:
        await shared_store.init(settings.database_url)
    except Exception:
        logger.exception(
            "[node-server] shared postgres pool init failed; "
            "onboarding/upgrading with a proxy_config_id will fail"
        )
    try:
        from . import task_message_store
        await task_message_store.init(
            settings.clickhouse_addr,
            database=settings.clickhouse_database,
            username=settings.clickhouse_username,
            password=settings.clickhouse_password,
        )
    except Exception:
        logger.exception(
            "[node-server] task_messages clickhouse init failed; "
            "conversation content falls back to postgres"
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_database()
    await _init_shared_config_store()
    await start_reaper()
    try:
        yield
    finally:
        await stop_reaper()
        try:
            from . import shared_store

            await shared_store.close()
        except Exception:
            logger.debug("[node-server] shared postgres pool close failed", exc_info=True)
        try:
            from . import task_message_store

            await task_message_store.close()
        except Exception:
            logger.debug("[node-server] task_messages clickhouse close failed", exc_info=True)
        await close_database()


app = FastAPI(title="Ai Lubricant Node Control Plane", lifespan=lifespan)
mount(app)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, object]:
    service = get_service()
    registry = getattr(service, "registry", None)
    return {
        "ok": service is not None,
        "service": "node-control",
        "connected_nodes": len(registry.list()) if registry is not None else 0,
    }
