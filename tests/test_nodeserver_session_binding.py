"""``NodeStore.bind_session_to_node`` upsert semantics.

This method is the last write of a successful dispatch: the node has already
accepted the session by the time it runs, so any exception here surfaces to the
user as 任务派发失败 while the node keeps a live session. It had no coverage,
which is how a ``NameError`` for an unimported symbol reached production.

The cases below pin the three properties the dispatch path depends on: a first
bind writes every field, a partial re-bind keeps what it does not carry, and
concurrent binds on the same ``session_id`` collapse into one row instead of
tripping the primary key.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db():
    from tortoise import Tortoise

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"node_server": ["node_server.store"]},
        use_tz=False,
    )
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()


def _binding(**overrides):
    from node_server.store import NodeSessionBinding

    base = dict(
        session_id="sess-1",
        node_id="node-a",
        project_id="proj-1",
        task_id="task-1",
        editor_id="editor-1",
        editor_session_id="editor-sess-1",
        provider="claude",
        model="claude-opus-4-8",
        mode="agent",
        status="running",
        applied_revision=3,
        effective_revision=4,
    )
    base.update(overrides)
    return NodeSessionBinding(**base)


@pytest.mark.asyncio
async def test_first_bind_persists_every_field(db):
    from node_server.store import node_store

    await node_store.bind_session_to_node(_binding())

    row = await node_store.get_session_node("sess-1")
    assert row is not None
    assert row.node_id == "node-a"
    assert row.project_id == "proj-1"
    assert row.task_id == "task-1"
    assert row.editor_id == "editor-1"
    assert row.editor_session_id == "editor-sess-1"
    assert row.provider == "claude"
    assert row.model == "claude-opus-4-8"
    assert row.mode == "agent"
    assert row.status == "running"
    assert row.applied_revision == 3
    assert row.effective_revision == 4


@pytest.mark.asyncio
async def test_rebind_updates_placement_and_keeps_absent_fields(db):
    from node_server.store import node_store

    await node_store.bind_session_to_node(_binding())
    # The idempotent adoption path re-binds with only placement data, so the
    # runtime descriptors must survive rather than being blanked.
    await node_store.bind_session_to_node(
        _binding(
            node_id="node-b",
            project_id="proj-2",
            task_id="task-2",
            provider="",
            model="",
            mode="",
            status="",
            applied_revision=9,
            effective_revision=10,
        )
    )

    row = await node_store.get_session_node("sess-1")
    assert row is not None
    assert row.node_id == "node-b"
    assert row.project_id == "proj-2"
    assert row.task_id == "task-2"
    assert row.applied_revision == 9
    assert row.effective_revision == 10
    assert row.provider == "claude"
    assert row.model == "claude-opus-4-8"
    assert row.mode == "agent"
    assert row.status == "running"


@pytest.mark.asyncio
async def test_rebind_overwrites_fields_that_are_present(db):
    from node_server.store import node_store

    await node_store.bind_session_to_node(_binding())
    await node_store.bind_session_to_node(_binding(status="stopped", mode="plan"))

    row = await node_store.get_session_node("sess-1")
    assert row is not None
    assert row.status == "stopped"
    assert row.mode == "plan"


@pytest.mark.asyncio
async def test_concurrent_binds_collapse_into_one_row(db):
    from node_server.store import ACNodeSession, node_store

    results = await asyncio.gather(
        *(node_store.bind_session_to_node(_binding(node_id=f"node-{i}")) for i in range(4)),
        return_exceptions=True,
    )

    assert [r for r in results if isinstance(r, BaseException)] == []
    assert await ACNodeSession.filter(session_id="sess-1").count() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("overrides", [{"session_id": ""}, {"node_id": ""}, {"session_id": "  "}])
async def test_bind_requires_session_and_node(db, overrides):
    from node_server.store import node_store

    with pytest.raises(ValueError):
        await node_store.bind_session_to_node(_binding(**overrides))
