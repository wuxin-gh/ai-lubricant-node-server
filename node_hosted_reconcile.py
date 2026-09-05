"""Mark a node's hosted MCP services offline when its connection drops.

node_hosted（形态 C）MCP 的进程跑在节点上：节点掉线即该 MCP 不可用。控制面把
``mcp_services.host_status`` 打成 ``dead``、``install_state`` 打成 ``error``，
agent 侧的就绪门据此挡住它，避免拿到一个连不上的 MCP 才在 call_tool 处炸。

为什么不复用 ``mcp_runtime.node_hosted.reconcile_node``
--------------------------------------------------------
那个模块顶层 import 数据服务的 ``mcp_plugin_store``（平铺 import），而独立控制面
入口（``python -m node_server``）不把 ``server/`` 注入 sys.path —— 在控制面进程里
直接 ``ModuleNotFoundError``，掉线对账从未真正生效。更根本的是 ``shared_store``
的自包含约束：控制面不 import 数据服务代码。所以这里照 ``task_finalize`` 的模式
经共享池直接发 raw SQL，语义与数据服务 ``mark_host_state`` + ``mark_install_state``
的掉线分支对齐：只改 host_status / install_state / install_step / install_error，
不动 host_node_id / host_port / host_pid（节点回来后对账重拉要靠它们找回进程）；
error 状态不打 install 时间戳列（数据服务 ``_INSTALL_STATE_STAMPS`` 无 error 映射）。

Best-effort：任何失败只记日志、绝不向上抛——掉线对账不能阻断连接拆除。
"""
from __future__ import annotations

from loguru import logger

# 与数据服务 mark_install_state 的截断上限一致（install_step VARCHAR(200)、
# install_error TEXT）。这里的文本是固定形状，正常远达不到上限，纯防御。
_STEP_MAX = 200
_ERROR_MAX = 4000


async def mark_node_hosted_offline(node_id: str) -> None:
    """把 ``node_id`` 上所有 node_hosted 形态的 MCP 服务标记为不可用。"""
    node_id = (node_id or "").strip()
    if not node_id:
        return
    try:
        from .shared_store import pool

        if pool() is None:
            return
        async with pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM mcp_services "
                "WHERE deploy_scope='node_hosted' AND host_node_id=$1",
                node_id,
            )
            for row in rows:
                await conn.execute(
                    "UPDATE mcp_services SET host_status='dead', "
                    "install_state='error', install_step=$2, install_error=$3, "
                    "updated_at=now() WHERE id=$1",
                    int(row["id"]),
                    "托管节点离线"[:_STEP_MAX],
                    f"node {node_id} offline"[:_ERROR_MAX],
                )
    except Exception:
        logger.exception(
            "[nodeserver] mark node-hosted mcp offline failed for {}", node_id,
        )
