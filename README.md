# ai-lubricant-node-server

节点控制面：接收 execution/management 节点的 h2c NodeConnect，提供会话调度、
终端、隧道、工具运行、git 代理等控制接口。Python 实现（源自 chaitin/agent-compose
的移植与本项目自有扩展），AGPL-3.0（见 LICENSE/NOTICE）。

与主仓库 ai-lubricant 的关系：两个进程，HTTP 通信（Connect unary + NDJSON follow
流），共享同一 PostgreSQL；互不 import 对方代码。安装进同一 venv 后
`python -m node_server` 启动（:8003，Hypercorn h2c）。

```bash
pip install -e ai-lubricant-node-server
python -m node_server
```

测试：`pytest tests/`
