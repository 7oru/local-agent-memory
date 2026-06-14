# local-agent-memory

中文 | [English](README.md)

面向个人 Agent 的本地优先记忆管理器。

`local-agent-memory` 是一个轻量、可审计的 Agent memory 层，默认运行在你自己的机器上。它把同一个本地记忆库暴露给 CLI、HTTP、MCP 和一个最小 Web UI，让你可以添加、查看、固定、修正、删除、导出 Agent 记住的内容。

这个仓库定位为个人试验性 MVP。它适合本地开发、轻量级自托管和 Agent 集成实验；它不是多用户 SaaS、云同步服务，也不应该被当作密钥存储系统。

## 它能做什么

- 使用本地 SQLite 数据库存储 memory。
- 支持 `global`、`project:<name>`、`agent:<name>`、`session:<id>` 等作用域。
- 区分 pinned memory 和 searchable memory。
- 保留规范化 memory envelope，包括 provenance、subject/entity 线索、salience、
  privacy、retention、置信度、状态、创建/更新时间等字段。
- 提供 add、search、list、pin、unpin、update、delete、serve、export、mcp 等 CLI 命令。
- 提供本地 HTTP API 和最小记忆审查 UI。
- 通过 MCP tools 给兼容的 Agent 使用。

## MVP 状态

当前 MVP 的目标是跑通一个紧凑的本地闭环：

```bash
./scripts/dev-up.sh
uv run lam add "用户偏好：个人 wiki 笔记默认写中文" --scope global --kind preference --pin
uv run lam search "wiki 笔记"
uv run lam serve
uv run lam mcp
```

更多范围、架构和任务状态见 [docs/mvp.md](docs/mvp.md)、[docs/architecture.md](docs/architecture.md)、[docs/tasks.md](docs/tasks.md)。

## 环境要求

- macOS、Linux，或其他支持 Python 3.11+ 的环境
- [`uv`](https://docs.astral.sh/uv/) 在 `PATH` 中可用
- 支持 FTS5 的 SQLite；多数开发机器上的 Python 标准 SQLite 构建已经包含

如果还没有安装 `uv`：

```bash
python3 -m pip install uv
```

## 本地开发

从新 clone 开始：

```bash
git clone <repo-url>
cd local-agent-memory
./scripts/dev-up.sh
```

这个 setup 命令会通过 `uv` 安装依赖、创建虚拟环境，并初始化 SQLite 数据库。

常用开发命令：

```bash
./scripts/dev-up.sh            # 安装依赖并初始化数据库
./scripts/dev-up.sh serve      # 启动 HTTP API 和 Web UI
./scripts/dev-up.sh test       # 初始化并运行测试
./scripts/test.sh              # 运行 unittest 测试集
./scripts/format.sh            # 运行格式化/检查脚本
```

直接使用 CLI：

```bash
uv run lam init
uv run lam add "项目决策：默认后端继续使用 SQLite" --scope project:local-agent-memory --kind decision
uv run lam add "用户偏好：先给简洁摘要" --scope global --kind preference --pin
uv run lam list --scope global --status pinned
uv run lam search "SQLite 后端" --scope project:local-agent-memory
uv run lam export --format json > local-agent-memory-export.json
```

外部评审或导入结果可以保留真实来源，同时补充规范化语义字段：

```bash
uv run lam add "Kimi reviewer verdict: practical MVP ready" \
  --scope project:local-agent-memory \
  --kind task_state \
  --title "Kimi MVP review" \
  --subject local-agent-memory \
  --entity Kimi \
  --entity local-agent-memory \
  --relation-json '{"subject":"Kimi","predicate":"reviewed","object":"local-agent-memory"}' \
  --salience 0.8 \
  --retention long_term \
  --source-kind import \
  --source-ref "kimi-api:moonshot-v1-128k" \
  --metadata model=moonshot-v1-128k \
  --metadata rounds=5
```

## 规范化 Memory Schema

数据库会保留 `content` 作为人可读的 canonical memory 文本，同时把外围记录整理成更接近工业界常见 Agent memory 的 envelope：

| 区域 | 字段 |
| --- | --- |
| Identity | `id`、`schema_version`、`kind`、`scope`，以及可选 `user_id`、`agent_id`、`app_id`、`run_id` |
| Meaning | `content`，以及可选 `title`、`summary`、`subject`、`entities`、`relations`、`tags`、`metadata` |
| Retrieval | `status`、`confidence`、`salience`、`privacy`、`retention` |
| Provenance | `source_kind`、`source_ref`、`valid_from`、`valid_to`、`supersedes_id`、`created_at`、`updated_at` |

完整、未改动的聊天记录更适合作为 source artifact 或 import metadata 保留；真正进入 durable memory 的条目，建议是从聊天记录中抽取出来的较小 assertion、preference、decision、procedure 或 task state。

## 轻量级本地部署

默认部署目标是单用户、绑定 loopback 的本地服务。

```bash
LAM_HOST=127.0.0.1 \
LAM_PORT=18790 \
LAM_DB_PATH="$HOME/.local-agent-memory/memory.db" \
./scripts/dev-up.sh serve
```

启动后访问：

- Web UI：`http://127.0.0.1:18790/`
- 健康检查：`http://127.0.0.1:18790/health`
- 导出接口：`http://127.0.0.1:18790/export`

API 启动时会自动初始化数据库。除非你已经额外配置了网络边界、认证和备份方案，否则建议保持绑定在 `127.0.0.1`。

### 本地部署 Guidelines

- 个人使用时保持默认 loopback host：`LAM_HOST=127.0.0.1`。
- 用 `LAM_DB_PATH` 选择稳定的数据库路径；默认是 `~/.local-agent-memory/memory.db`。
- 实验前备份 SQLite 文件，或定期导出 JSON：
  `uv run lam export --format json > backup.json`。
- 不要把 API keys、密码、tokens、助记词、恢复码或其他 secrets 写进 memory。
- pinned memory 只放少量、稳定、应该总是注入的偏好或操作规则。
- 项目事实优先使用带作用域的 memory，例如 `project:<repo-or-system-name>`。
- 只有当前台命令在你的机器上稳定工作后，再考虑用简单的进程管理器托管。
- 启动后、修改环境变量后，都检查 `/health`。
- 重置测试数据库时，删除 SQLite 文件后重新运行 `uv run lam init`。

重置示例：

```bash
rm -f ~/.local-agent-memory/memory.db
uv run lam init
```

## HTTP API

启动 API：

```bash
./scripts/dev-up.sh serve
```

主要端点：

```text
GET    /
GET    /health
GET    /memories
POST   /memories
GET    /memories/{id}
PATCH  /memories/{id}
DELETE /memories/{id}
POST   /search
GET    /pinned
GET    /export
```

搜索请求示例：

```bash
curl -s http://127.0.0.1:18790/search \
  -H 'content-type: application/json' \
  -d '{"query":"SQLite 后端","scope":"project:local-agent-memory","limit":5}'
```

## MCP 集成

对于支持 stdio servers 的 MCP 客户端，把它指向本地 CLI 命令即可。

```json
{
  "mcpServers": {
    "local-agent-memory": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/local-agent-memory",
        "run",
        "lam",
        "mcp"
      ],
      "env": {
        "LAM_DB_PATH": "~/.local-agent-memory/memory.db"
      }
    }
  }
}
```

当前 MCP tools：

```text
memory_get_pinned
memory_search
memory_add
memory_update
memory_delete
```

对于 command-based 的 OpenClaw MCP 配置，可以使用同样的 command、args 和 env：

```json
{
  "name": "local-agent-memory",
  "transport": "stdio",
  "command": "uv",
  "args": ["--directory", "/path/to/local-agent-memory", "run", "lam", "mcp"],
  "env": {
    "LAM_DB_PATH": "~/.local-agent-memory/memory.db"
  }
}
```

## 数据归属

默认数据文件：

```text
~/.local-agent-memory/memory.db
```

可以使用 `LAM_DB_PATH` 或 CLI 的 `--db` 参数指定其他 SQLite 文件：

```bash
LAM_DB_PATH=/tmp/lam-demo.db uv run lam add "临时测试 memory" --scope global
uv run lam --db /tmp/lam-demo.db list
```

导出结果是 JSON，包含 memory records 和 audit events：

```bash
uv run lam export --format json > local-agent-memory-export.json
```

## 开发说明

这个 MVP 借鉴了三个产品方向：

- Mem0：把 memory 暴露成小而通用的 API，而不是隐藏在框架内部。
- Graphiti：保留时间状态、冲突和 supersession 元数据。
- Letta：区分 hot/pinned memory 和 cold/searchable memory。

当前实现把 SQLite 相关逻辑收在 storage/service 层里，让 CLI、HTTP、UI、MCP 共享同一套核心行为。
