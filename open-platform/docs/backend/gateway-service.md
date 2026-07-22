# 后端网关

`backend/gateway_service` 是开放平台的后端服务。它通过 FastAPI 暴露控制台 API 和开放 API，并通过 HTTP 调用 DML 主后端。

## 目录结构

```text
gateway_service/
├── __main__.py                 # uvicorn 启动入口
├── app.py                      # FastAPI 应用装配
├── config.py                   # GatewaySettings
├── api/
│   ├── console.py              # 控制台 API
│   └── gateway.py              # 开放 API
├── common/
│   ├── container.py            # 依赖注入组合根
│   ├── logging_utils.py        # 日志工具
│   └── responses.py            # 响应构造
├── core/
│   ├── catalog.py              # 能力注册表
│   ├── internal_token.py       # 上游内部 JWT
│   ├── load_balancer.py        # 负载均衡
│   ├── matching.py             # 路由匹配
│   ├── pipeline.py             # 请求管线
│   └── security.py             # 鉴权与权限
├── domain/
│   ├── enums.py
│   ├── errors.py
│   └── models.py
└── infrastructure/
    ├── database.py
    ├── debug_probe.py
    ├── repository.py
    ├── seed_data.py
    ├── sqlite_repository.py
    └── upstream.py
```

## 启动入口

```bash
cd backend
uv run python -m gateway_service
```

也可以直接使用 Python 环境：

```bash
python -m gateway_service
```

## 核心对象

| 对象 | 位置 | 说明 |
| --- | --- | --- |
| `GatewaySettings` | `config.py` | 从环境变量读取运行时配置 |
| `GatewayContainer` | `common/container.py` | 创建并连接全部服务对象 |
| `GatewayPipeline` | `core/pipeline.py` | 开放 API 请求主流程 |
| `CapabilityMatcher` | `core/matching.py` | 方法和路径匹配 |
| `GatewayAuth` | `core/security.py` | API Key、Scope 和用户权限校验 |
| `RoundRobinLoadBalancer` | `core/load_balancer.py` | 多上游轮询 |
| `UpstreamClient` | `infrastructure/upstream.py` | HTTP 转发 |
| `SQLiteGatewayRepository` | `infrastructure/sqlite_repository.py` | SQLite 持久化 |

## 数据存储

默认使用 SQLite：

```text
backend/gateway_service/gateway.db
```

可通过 `DML_GATEWAY_DB_PATH` 修改位置。当前仓储保存用户、API Key、配额、能力授权和调用日志。

## 种子数据

本地开发时会使用 `infrastructure/seed_data.py` 初始化测试用户和 API Key。内置密钥仅用于本地联调，不应作为生产凭证。

## 测试

```bash
cd backend
uv run pytest tests -v
```

当前测试覆盖控制台鉴权、上游认证和能力执行相关逻辑。
