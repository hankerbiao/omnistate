# DML V4 开放平台网关服务

开放平台网关服务，为 DML V4 的开放 API 提供统一入口，覆盖路由转发、请求过滤、负载均衡、鉴权认证、熔断与审计日志等全链路能力。

---

## 架构

### 五层模块结构

```
gateway_service/
│
├── domain/               # 领域层 — 枚举、模型、异常（零项目内依赖）
├── api/                  # 路由层 — 薄适配器，仅做参数校验与编排
├── core/                 # 核心层 — 鉴权、熔断、负载均衡、匹配、管线
├── infrastructure/       # 基础设施 — 仓储、种子数据、上游转发、调试探针
└── common/               # 公共工具 — DI 容器、日志、响应构造
```

### 请求处理流程

```
客户端请求
    │
    ▼
  api/gateway.py     → 路由层（薄适配器）
    │
    ▼
  core/pipeline.py   → 请求处理管线
    ├── 1. _match()          能力匹配（CapabilityMatcher）
    ├── 2. _authenticate()   鉴权认证（GatewayAuth）
    ├── 3. _choose_upstream()按需上游选择（仅 proxy/aggregate）
    ├── 4. _execute_capability() 能力执行（CapabilityExecutor → Handler）
    └── 5. _record()         审计日志
```

### 关键设计

| 机制 | 说明 |
|------|------|
| **依赖注入** | `GatewayContainer.build()` 一次性装配所有服务，新增组件无需改动函数签名 |
| **协议化替换** | `Repository` / `LoadBalancer` 通过 Protocol 声明，可切换内存/DB/Redis 实现 |
| **能力执行层** | `CapabilityExecutor` 按能力分发到 proxy/local/aggregate handler |
| **统一错误** | 管线抛出 `GatewayError`，路由层统一构造错误响应，错误码映射集中在 `common/responses.py` |

---

## 快速开始

### 前置要求

- Python >= 3.11

### 安装依赖

```bash
pip install fastapi uvicorn[standard] httpx pydantic
```

### 启动服务

```bash
# 默认配置启动（监听 127.0.0.1:8820）
python -m gateway_service

# 指定上游地址
DML_GATEWAY_UPSTREAMS=http://127.0.0.1:8801,http://127.0.0.1:8802 \
DML_GATEWAY_PORT=8820 \
  python -m gateway_service
```

启动后访问 http://127.0.0.1:8820/docs 查看 Swagger 文档。

### 验证服务

```bash
# 健康检查
curl http://127.0.0.1:8820/health

# 调用开放 API（需先获取 API Key）
curl http://127.0.0.1:8820/api/v1/open/execution/tasks/my \
  -H "Authorization: Bearer dml_live_demo_ci"
```

---

## 配置

所有配置通过环境变量注入，前缀 `DML_GATEWAY_`：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DML_GATEWAY_HOST` | `127.0.0.1` | 监听地址 |
| `DML_GATEWAY_PORT` | `8820` | 监听端口（1-65535） |
| `DML_GATEWAY_UPSTREAMS` | `http://127.0.0.1:8801` | 上游服务地址列表，逗号分隔 |
| `DML_GATEWAY_REQUEST_TIMEOUT` | `15` | 请求超时（秒） |
| `DML_GATEWAY_CONNECT_TIMEOUT` | `3` | 连接超时（秒） |
| `DML_GATEWAY_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | CORS 允许来源，逗号分隔 |
| `DML_GATEWAY_CONSOLE_TOKEN` | `dev-console-token` | 控制台 API 鉴权 Token |
| `DML_GATEWAY_UPSTREAM_AUTH_SECRET` | `dev-open-platform-gateway-secret-change-me` | 调用 DML 后端的内部 JWT 签名密钥，必须与 DML `open_platform_gateway_jwt.secret_key` 一致 |
| `DML_GATEWAY_UPSTREAM_AUTH_ISSUER` | `dml-open-platform` | 内部 JWT issuer，必须与 DML 配置一致 |
| `DML_GATEWAY_UPSTREAM_AUTH_AUDIENCE` | `dml-backend` | 内部 JWT audience，必须与 DML 配置一致 |
| `DML_GATEWAY_UPSTREAM_AUTH_TTL_SECONDS` | `300` | 内部 JWT 有效期（秒） |
| `DML_GATEWAY_LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `DML_GATEWAY_LOG_FILE` | _(空)_ | 日志文件路径，设置后启用文件输出（10MB 轮转，保留 5 份） |
| `DML_GATEWAY_DB_PATH` | `gateway_service/gateway.db` | SQLite 数据库文件路径 |

---

## API 文档

### 开放 API（能力服务）

前缀 `GET/POST/PUT/DELETE /api/v1/open/{path}`

请求需携带 `Authorization: Bearer <API Key>` 头。

#### 已注册的开放能力

| 能力 ID | 名称 | 方法 | 路径 | Scope | 执行模式 |
|---------|------|------|------|-------|----------|
| `cap_list_tasks` | 查询我的测试任务 | GET | `/api/v1/open/execution/tasks/my` | `execution_tasks:read` | proxy |
| `cap_task_status` | 查询任务状态 | GET | `/api/v1/open/execution/tasks/{task_id}/status` | `execution_tasks:read` | proxy |
| `cap_task_timeline` | 查询任务时间线 | GET | `/api/v1/open/execution/tasks/{task_id}/timeline` | `execution_tasks:read` | proxy |
| `cap_list_specs` | 读取测试用例 | GET | `/api/v1/open/test-specs/cases` | `test_cases:read` | proxy 到 `/api/v1/test-cases` |
| `cap_report` | 读取执行报告 | GET | `/api/v1/open/reports/{task_id}` | `execution_tasks:read` | aggregate |
| `cap_webhook` | 注册结果回调 | POST | `/api/v1/open/webhooks` | `execution_tasks:write` | local |

开放 API 路径是 Open Platform 的稳定契约，不要求与 DML 后端路由一一同名。
`proxy` 能力通过 `upstreamPath` 调用 DML；`aggregate` 能力可组合多个内部接口；`local` 能力由
Open Platform 自己处理与落库。

#### 调用示例

```bash
# 查询任务列表
curl -H "Authorization: Bearer dml_live_demo_ci" \
  "http://127.0.0.1:8820/api/v1/open/execution/tasks/my?limit=5"

# 查询任务状态
curl -H "Authorization: Bearer dml_live_demo_ci" \
  "http://127.0.0.1:8820/api/v1/open/execution/tasks/ET-2026-000128/status"
```

#### 响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... }
}
```

错误时返回：

```json
{
  "code": 401,
  "message": "Invalid or revoked API key",
  "data": { "error": "AUTHENTICATION_FAILED" }
}
```

| 错误码 | 说明 |
|--------|------|
| 401 | 认证失败（API Key 无效/已撤销） |
| 403 | 权限不足（缺少 Scope） |
| 404 | 路由未匹配 |
| 503 | 上游服务不可用 |

### 控制台 API

前缀 `/api/v1/open-platform`，需携带 `x-console-token` 或 `Authorization: Bearer <console_token>` 头。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/overview` | 概览统计 |
| GET | `/keys` | 列出 API Key |
| POST | `/keys` | 创建 API Key |
| POST | `/keys/{id}/revoke` | 撤销 API Key |
| DELETE | `/keys/{id}` | 删除 API Key |
| GET | `/users` | 列出用户 |
| PUT | `/users/{id}/permissions` | 更新用户权限 |
| PUT | `/users/{id}/quota` | 更新用户配额 |
| GET | `/capabilities` | 能力目录 |
| GET | `/logs` | 调用日志 |
| POST | `/debug` | 调试探测 |

### 内置测试账号

| 用户 | 角色 | 说明 |
|------|------|------|
| `user_admin` | admin | 平台管理员，拥有全部权限 |
| `user_developer` | developer | 开发者 |
| `user_zhaolei` | developer | 开发者 |

内置 API Key：

| Key ID | 名称 | 环境 | 明文 Token |
|--------|------|------|------------|
| `key_01` | CI 流水线集成 | live | `dml_live_demo_ci` |
| `key_02` | 数据看板同步 | live | `dml_live_demo_dashboard` |
| `key_03` | 本地联调 | test | `dml_test_demo_local` |
| `key_04` | 旧版报表脚本 | live | `dml_live_demo_revoked`（已撤销） |

---

## 开发

### 添加一个开放能力

在 `core/catalog.py` 的 `CAPABILITIES` 列表中增加一条 `Capability` 记录即可，路由匹配、控制台展示、调试探针自动生效。

```python
Capability(
    id="cap_new_feature",
    name="新功能",
    category="新分类",
    method="POST",
    path="/api/v1/open/new-feature",
    summary="新功能简要描述",
    description="新功能的详细描述。",
    scope="new_feature:write",
    params=[...],
    sampleResponse="""{"code": 0, "data": {}}""",
)
```

### 添加一个开放能力实现

代理能力只需要在能力目录中显式配置 `handler="proxy"` 和 `upstreamPath`。
本地或聚合能力在 `CapabilityExecutor` 的 handler registry 中注册对应处理器。

```python
Capability(
    id="cap_new_feature",
    method="GET",
    path="/api/v1/open/new-feature",
    scope="new_feature:read",
    handler="proxy",
    upstreamPath="/api/v1/internal/new-feature",
    ...
)
```

### 替换存储实现

1. 实现 `infrastructure/repository.py` 中定义的 `Repository` Protocol
2. 在 `common/container.py` 中用新实现替换 `GatewayRepository`

### 替换负载均衡策略

1. 实现 `core/load_balancer.py` 中定义的 `LoadBalancer` Protocol
2. 在 `common/container.py` 中用新策略替换 `RoundRobinLoadBalancer`

### 调试探测

控制台的调试功能通过 `POST /api/v1/open-platform/debug` 调用，选择一个开放能力和 API Key，输入参数后向实际上游发送探测请求并返回结果。

---

## 项目目录

```
gateway_service/
├── app.py                    # FastAPI 应用装配
├── config.py                 # 运行时配置
├── __main__.py               # CLI 启动入口
├── pyproject.toml            # 项目元信息与依赖
│
├── domain/
│   ├── enums.py              # 枚举与字面量类型
│   ├── errors.py             # 统一异常
│   └── models.py             # Pydantic 数据模型
│
├── api/
│   ├── console.py            # 控制台路由
│   └── gateway.py            # 开放 API 网关路由
│
├── core/
│   ├── catalog.py            # 开放能力目录
│   ├── matching.py           # 路由匹配
│   ├── security.py           # 认证鉴权
│   ├── circuit_breaker.py    # 熔断保护
│   ├── load_balancer.py      # 负载均衡
│   └── pipeline.py           # 请求处理管线
│
├── infrastructure/
│   ├── repository.py         # 数据仓库
│   ├── seed_data.py          # 种子数据
│   ├── upstream.py           # 上游转发
│   └── debug_probe.py        # 调试探针
│
├── common/
│   ├── container.py          # 依赖注入容器
│   ├── logging_utils.py      # 日志工具
│   └── responses.py          # 响应构造
│
├── ARCHITECTURE.md           # 架构文档
└── README.md                 # 本文件
```
