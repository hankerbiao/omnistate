# 网关服务（gateway_service）工程结构与扩展设计

---

## 1. 架构总览

```
gateway_service/                      # 开放平台网关服务
│
├── __init__.py                       # 包入口，导出 create_app
├── __main__.py                       # CLI 启动入口（uvicorn）
├── app.py                            # FastAPI 应用装配（不含业务）
├── config.py                         # 运行时配置（GatewaySettings）
├── pyproject.toml                    # 独立项目元信息与依赖声明
│
├── domain/                           # ===== 领域层 =====
│   ├── __init__.py
│   ├── enums.py                      # 枚举与字面量类型
│   ├── errors.py                     # 统一异常 GatewayError
│   └── models.py                     # Pydantic 数据模型
│
├── api/                              # ===== API 路由层（薄适配器） =====
│   ├── __init__.py
│   ├── console.py                    # 控制台路由（参数校验 + 编排）
│   └── gateway.py                    # 开放 API 网关路由（调用 pipeline）
│
├── core/                             # ===== 核心能力层 =====
│   ├── __init__.py
│   ├── catalog.py                    # 开放能力目录 CAPABILITIES
│   ├── matching.py                   # 路由匹配 CapabilityMatcher
│   ├── security.py                   # 认证鉴权 GatewayAuth
│   ├── limits.py                     # 限流控制 RateLimiter
│   ├── circuit_breaker.py            # 熔断保护 CircuitBreaker
│   ├── load_balancer.py              # 负载均衡 LoadBalancer（含协议）
│   └── pipeline.py                   # 请求处理管线 GatewayPipeline
│
├── infrastructure/                   # ===== 基础设施层 =====
│   ├── __init__.py
│   ├── repository.py                 # 数据仓库 Repository（协议 + 内存实现）
│   ├── seed_data.py                  # 种子数据工厂
│   ├── upstream.py                   # 上游 HTTP 转发 UpstreamClient
│   └── debug_probe.py                # 调试探针
│
├── common/                           # ===== 公共工具层 =====
│   ├── __init__.py
│   ├── container.py                  # 依赖注入组合根 GatewayContainer
│   ├── logging_utils.py              # 结构化日志与调用日志构造
│   └── responses.py                  # 统一 HTTP 响应与错误码映射
│
└── ARCHITECTURE.md                   # 本文件
```

**分层原则**
- `app.py` / `common/container.py` 是唯一知道「如何把东西拼起来」的地方（组合根），其余模块只声明依赖（通过协议）。
- `core/`、`infrastructure/` 中的可替换组件通过协议对外暴露（`Repository` / `LoadBalancer`），便于替换实现。
- `api/` 只做「参数解析 + 编排」，不含业务算法；算法在 `core/` 中。
- `domain/` 不依赖任何项目内模块（标准库 + Pydantic 除外）。
- `infrastructure/` 中的外部通信、存储、调试工具可以被 `core/` 和 `api/` 调用。

---

## 2. 架构约束

代码通过模块职责分离锁定了以下关键规则：

- 错误响应统一收敛到 `common/responses.py`（`build_gateway_error_response`），路由不得内联错误码/诊断映射；
- 控制台 debug 必须委托 `infrastructure/debug_probe.run_debug_probe`，不得内联 httpx 探测；
- `infrastructure/seed_data.py` 不得依赖 `fastapi` / `httpx` / `app` / `routes`；
- `infrastructure/repository.py` 不含种子数据字面量。

---

## 3. 关键扩展机制

### 3.1 依赖注入容器（可扩展性支点）
所有服务对象在 `GatewayContainer.build()` 中一次性装配。新增横切组件（如 `Tracer`）：
```python
# common/container.py
tracer = Tracer(settings)
pipeline = GatewayPipeline(..., tracer=tracer)
```
路由与管线通过 `container.tracer` 取用，无需改动任何函数签名。

### 3.2 请求管线（可读 + 可插拔）
`GatewayPipeline` 的阶段是独立方法。要新增阶段（如请求改写、响应缓存），
新增开放能力时优先扩展 capability handler；管线只保留匹配、鉴权、按需选上游和审计：
```python
Capability(
    id="cap_new_feature",
    handler="proxy",
    upstreamPath="/api/v1/internal/new-feature",
    ...
)
```
错误统一以 `GatewayError` 抛出，由路由层用 `build_gateway_error_response` 封装，
错误码/诊断映射仍集中在 `common/responses.py`。

### 3.3 协议化依赖（可替换实现）
- `Repository` 协议：`GatewayRepository`（内存）可替换为 DB/Redis 实现，调用方无感。
- `LoadBalancer` 协议：`RoundRobinLoadBalancer` 可替换为一致性哈希 / 权重 / 服务发现。

### 3.4 能力注册表（`core/catalog.py`）
新增开放能力 = 在 `CAPABILITIES` 增加一条 `Capability`，匹配、控制台展示、调试探针自动生效。

### 3.5 配置分层（`config.py`）
所有运行参数通过 `GatewaySettings` + 环境变量注入，便于多环境（dev/test/prod）切换。

---

## 4. 扩展配方速查

| 需求 | 改动位置 |
| --- | --- |
| 新增一个开放能力 | `core/catalog.py` 增加 `Capability` |
| 新增代理阶段（改写/缓存/追踪） | `core/pipeline.py` 增加 `_stage` 方法并插入 `handle()` |
| 新增网关路由分组 | 新建 `api/xxx.py` + `container` 传入 + `app.py` `include_router` |
| 新增控制台接口 | `api/console.py` 增加 handler |
| 换存储为 DB/Redis | 实现 `Repository` 协议，`common/container.py` 中用其替换 `GatewayRepository` |
| 换负载均衡策略 | 实现 `LoadBalancer` 协议，`common/container.py` 替换 |
| 新增限流/熔断策略 | 实现同形接口，`common/container.py` 替换 |
| 新增横切组件 | `common/container.py` 注册，`container.xxx` 取用 |
