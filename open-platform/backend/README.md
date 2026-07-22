# DML V4 开放平台 · MCP 后端

> 本目录现在包含两个独立服务：`gateway_service` 是开放平台 API 网关，`mcp_server` 是 MCP 工具服务。两者都通过 HTTP 调用现有 DML 主后端，不直接访问数据库。

## 开放平台网关服务

网关覆盖开放 API 的核心运行能力：路由转发、请求过滤、轮询负载均衡、API Key 鉴权、scope 权限校验、RPM/并发/月度限流、上游熔断、结构化日志和调用审计。

```bash
# 安装依赖
uv sync --extra dev
# 或 pip install -e ".[dev]"

# 启动网关，默认监听 http://127.0.0.1:8820
DML_GATEWAY_UPSTREAMS="http://127.0.0.1:8801" uv run python -m gateway_service
```

### 前端对接

前端默认仍可使用 Mock 数据；配置下面变量后会优先请求网关控制台 API，失败时自动回退 Mock：

```bash
VITE_OPEN_PLATFORM_API_BASE_URL=http://127.0.0.1:8820
VITE_OPEN_PLATFORM_CONSOLE_TOKEN=dev-console-token
```

控制台 API 前缀为 `/api/v1/open-platform`：

- `GET /overview`：概览统计
- `GET/POST /keys`：密钥列表与创建
- `POST /keys/{key_id}/revoke`、`DELETE /keys/{key_id}`：密钥停用与删除
- `GET /capabilities`：开放能力目录
- `GET /logs`：调用日志
- `POST /debug`：在线调试请求

开放 API 前缀为 `/api/v1/open`，例如：

```bash
curl http://127.0.0.1:8820/api/v1/open/execution/tasks/my \
  -H "Authorization: Bearer dml_test_demo_local"
```

网关会把开放路径转发到主后端对应的 `/api/v1/...` 路径，并透传 `X-Request-ID`、`X-Open-Platform-Key-Id`、`X-Open-Platform-User-Id` 便于主后端审计。

### 网关环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DML_GATEWAY_HOST` | `127.0.0.1` | 监听地址 |
| `DML_GATEWAY_PORT` | `8820` | 监听端口 |
| `DML_GATEWAY_UPSTREAMS` | `http://127.0.0.1:8801` | 逗号分隔的上游 DML 主后端地址 |
| `DML_GATEWAY_CONSOLE_TOKEN` | `dev-console-token` | 控制台 API 访问令牌 |
| `DML_GATEWAY_UPSTREAM_AUTH_SECRET` | `dev-open-platform-gateway-secret-change-me` | 调用 DML 后端的内部 JWT 签名密钥，必须与 DML `open_platform_gateway_jwt.secret_key` 一致 |
| `DML_GATEWAY_UPSTREAM_AUTH_ISSUER` | `dml-open-platform` | 内部 JWT issuer，必须与 DML 配置一致 |
| `DML_GATEWAY_UPSTREAM_AUTH_AUDIENCE` | `dml-backend` | 内部 JWT audience，必须与 DML 配置一致 |
| `DML_GATEWAY_UPSTREAM_AUTH_TTL_SECONDS` | `300` | 内部 JWT 有效期（秒） |
| `DML_GATEWAY_DEFAULT_RPM` | `120` | 单密钥默认每分钟请求数 |
| `DML_GATEWAY_DEFAULT_CONCURRENCY` | `10` | 单密钥默认并发数 |
| `DML_GATEWAY_DEFAULT_MONTHLY_LIMIT` | `100000` | 单密钥默认月度调用上限 |
| `DML_GATEWAY_CIRCUIT_FAILURE_THRESHOLD` | `5` | 上游连续失败熔断阈值 |
| `DML_GATEWAY_CIRCUIT_RECOVERY_SECONDS` | `30` | 熔断恢复探测时间 |
| `DML_GATEWAY_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:8808,http://127.0.0.1:8808,http://localhost:8809,http://127.0.0.1:8809` | 允许的前端来源 |

### 测试

```bash
uv run pytest tests -v
uv run ruff check gateway_service mcp_server tests
```

## MCP 服务

`mcp_server` 是开放平台的独立 MCP 入口，复用 `gateway_service` 的能力目录、API Key 鉴权、SQLite 仓储、上游转发、内部 JWT 和能力执行器。MCP 工具默认只开放只读能力。

### 启动

```bash
# stdio，适合本地 MCP 客户端
DML_MCP_API_KEY=dml_test_demo_local uv run python -m mcp_server.server

# Streamable HTTP，默认 http://127.0.0.1:8810/mcp
DML_MCP_TRANSPORT=streamable-http \
DML_MCP_API_KEY=dml_test_demo_local \
uv run python -m mcp_server.server
```

### 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DML_MCP_TRANSPORT` | `stdio` | `stdio` 或 `streamable-http` |
| `DML_MCP_API_KEY` | 空 | MCP 默认使用的开放平台 API Key |
| `DML_MCP_HOST` | `127.0.0.1` | HTTP 监听地址 |
| `DML_MCP_PORT` | `8810` | HTTP 监听端口 |
| `DML_MCP_PATH` | `/mcp` | Streamable HTTP MCP 路径 |
| `DML_MCP_ENABLE_WRITE_TOOLS` | `false` | 预留开关，v1 默认不注册写工具 |

MCP 服务同时复用 `DML_GATEWAY_DB_PATH`、`DML_GATEWAY_UPSTREAMS` 和 `DML_GATEWAY_UPSTREAM_AUTH_*` 配置。

### 工具

- `list_my_open_capabilities`：列出当前 API Key 可访问的只读开放能力及参数说明。
- `list_my_test_tasks`：查询测试任务列表。
- `list_test_cases`：查询测试用例列表，支持 `project_id`、`status`、`limit` 过滤。
- `get_test_task_status`：查询单个测试任务状态。
- `get_test_task_timeline`：查询测试任务时间线。
- `get_execution_report`：读取执行报告与失败分析摘要。

## 命令速查

```bash
uv run pytest                 # 运行单测
uv run ruff check gateway_service mcp_server tests  # 代码检查
uv run python -m mcp_server.server  # 启动服务
```

## 目录结构

```text
backend/
├── mcp_server/              # 独立 MCP 工具服务
│   ├── server.py            # FastMCP 入口与工具定义
│   ├── config.py            # MCPSettings（环境变量驱动）
│   ├── adapter.py           # MCP 请求适配
│   └── tools.py             # 工具服务
├── tests/                   # 单测
├── pyproject.toml           # 依赖与运行配置
└── README.md
```
