# DML V4 Backend

FastAPI 后端，提供测试需求、用例管理、执行编排、权限控制等统一服务。

## 快速开始

```bash
uv sync
python scripts/init/init_mongodb.py
python scripts/init/init_rbac.py
python scripts/init/create_user.py
python -m app.main
```

默认监听 `0.0.0.0:8801`，API 前缀 `/api/v1`。

## MCP 服务

MCP 服务作为独立进程调用现有后端 API，默认只提供测试任务查询工具，不直接访问数据库。

```bash
# 先启动业务后端，然后设置有效的用户 JWT；状态和时间线工具要求 execution_tasks:read 权限
export DML_MCP_BACKEND_URL="http://127.0.0.1:8801"
export DML_MCP_BACKEND_TOKEN="<access-token>"

# 本地 AI 客户端使用 stdio（默认）
uv run python -m app.mcp_server.server

# 或启动 Streamable HTTP，默认地址 http://127.0.0.1:8810/mcp
DML_MCP_TRANSPORT="streamable-http" uv run python -m app.mcp_server.server
```

可用环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DML_MCP_BACKEND_URL` | `http://127.0.0.1:8801` | DML 后端地址 |
| `DML_MCP_BACKEND_TOKEN` | 空 | 调用后端使用的 JWT，不应提交到仓库 |
| `DML_MCP_TRANSPORT` | `stdio` | `stdio` 或 `streamable-http` |
| `DML_MCP_HOST` | `127.0.0.1` | HTTP 监听地址；当前为安全起见只允许本机地址 |
| `DML_MCP_PORT` | `8810` | HTTP 监听端口 |
| `DML_MCP_REQUEST_TIMEOUT` | `15` | 后端请求超时秒数 |

当前工具：`list_my_test_tasks`、`get_test_task_status`、`get_test_task_timeline`。

## 项目结构

```text
app/
├── main.py                  # FastAPI 入口
├── mcp_server/              # 独立 MCP 工具服务
├── modules/                 # 业务模块
└── shared/                  # 基础设施
scripts/                     # 工具脚本
tests/                       # 测试
docs/                        # 文档
```

## 关键文档

| 文档 | 说明 |
|------|------|
| `AGENTS.md` | 开发规范、命令速查 |
| `app/modules/*/README.md` | 各模块详细说明 |
| `docs/test_plan/` | 测试方案与覆盖度报告 |
| `config.yaml.example` | 配置模板 |

## 命令速查

```bash
uv run pytest              # 测试
uv run ruff check app tests # 代码检查
uv run python -m app.main  # 启动
```
