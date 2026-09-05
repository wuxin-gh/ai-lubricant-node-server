"""Independent Tortoise bootstrap for the node control ledger."""
from __future__ import annotations

from loguru import logger

from .config import settings

APP_LABEL = "node_server"


async def init_database() -> None:
    """Connect and create/reconcile only mc_ac_nodes + mc_ac_node_sessions."""
    from tortoise import Tortoise

    config = {
        "connections": {APP_LABEL: settings.database_url},
        "apps": {APP_LABEL: {"models": ["node_server.store"], "default_connection": APP_LABEL}},
    }
    await Tortoise.init(config=config, use_tz=False, _enable_global_fallback=True)
    # Existing tables may predate fields that are also used by newly declared
    # indexes. PostgreSQL evaluates CREATE INDEX IF NOT EXISTS even when the table
    # already exists, so generate_schemas would fail before the old post-generate
    # reconciliation got a chance to add the column (for example task_id on
    # mc_ac_node_sessions). Reconcile existing tables first; missing tables are
    # skipped and then created normally by generate_schemas.
    await _ensure_additive_columns()
    await Tortoise.generate_schemas(safe=True)
    # Keep the post-pass for a newly created table/race and as an idempotent guard.
    await _ensure_additive_columns()
    logger.info("[node-server] node ledger database ready")


async def _ensure_additive_columns() -> None:
    from tortoise import Tortoise

    conn = Tortoise.get_connection(APP_LABEL)
    models = {}
    for label, model_map in Tortoise.apps.items():
        if label == APP_LABEL:
            models = model_map
            break
    for model in models.values():
        meta = model._meta
        rows = await conn.execute_query_dict(
            "SELECT column_name FROM information_schema.columns WHERE table_name = $1",
            [meta.db_table],
        )
        if not rows:
            continue
        existing = {row["column_name"] for row in rows}
        for field_name, column in meta.fields_db_projection.items():
            if column in existing:
                continue
            field = meta.fields_map[field_name]
            sql_type = getattr(field, "SQL_TYPE", None)
            if not sql_type:
                continue
            await conn.execute_script(
                f'ALTER TABLE "{meta.db_table}" ADD COLUMN "{column}" {sql_type} NULL;'
            )
            logger.info("[node-server] added missing column {}.{} ({})", meta.db_table, column, sql_type)


async def close_database() -> None:
    from tortoise import Tortoise

    await Tortoise.close_connections()
