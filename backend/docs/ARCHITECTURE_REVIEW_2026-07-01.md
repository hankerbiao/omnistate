# DML V4 后端架构设计评审报告

> 评审范围：`app/` 全目录（排除 tests）
> 技术栈：FastAPI + MongoDB(Beanie) + Redis(Sentinel) + Kafka + RabbitMQ + LangChain
> 评审日期：2026-07-01

---

## 一、架构全景

项目采用 **DDD 风格的模块化单体**，14 个业务模块 + shared 基础设施，通过 FastAPI 对外提供 REST API。

```
app/
├── main.py                  # 入口：lifespan 管理 Mongo/Beanie/Kafka/Redis
├── modules/                 # 14 个业务模块
│   ├── workflow/            # 工作流引擎（状态机驱动）
│   ├── test_specs/          # 测试需求/用例/目录（核心业务）
│   ├── execution/           # 执行任务调度
│   ├── execution_plan/      # 执行计划编排
│   ├── auth/                # 用户/角色/权限
│   ├── project/             # 项目管理
│   ├── test_case_collection/# 用例集合
│   ├── attachments/         # 附件（MinIO）
│   ├── search/              # 全局搜索
│   ├── system_config/       # 系统配置
│   ├── ai_analysis/         # AI 分析
│   ├── failure_analysis/    # 失败分析
│   ├── audit/               # 审计日志
│   └── notification/        # 通知
└── shared/                  # 基础设施
    ├── config/              # pydantic settings (YAML + env)
    ├── api/                 # 路由聚合 + 全局错误处理
    ├── auth/                # JWT + RBAC
    ├── core/                # logger / mongo_client
    ├── redis/               # 服务注册 + 心跳 + pub/sub
    ├── kafka/               # 消费者 + 路由分发
    ├── rabbitmq/            # 任务投递（producer-only）
    ├── minio/               # 对象存储
    ├── ai/                  # embedding / LLM client
    ├── infrastructure/      # 定时任务 + 插件注册
    └── service/             # BaseService + SequenceIdService
```

---

## 二、架构评分总览

| 维度 | 评分 | 说明 |
|------|------|------|
| **分层设计** | ★★★☆☆ | 有 DDD 分层意识，但 14 模块分层不一致，3 种模式并存 |
| **模块边界** | ★★☆☆☆ | 跨模块直接 import repository 严重，端口抽象被绕过 |
| **领域模型** | ★★☆☆☆ | domain 层普遍稀薄，存在反向依赖 repository 的违规 |
| **数据访问** | ★★☆☆☆ | 无 Repository 抽象，service 与 Beanie ODM 强耦合 |
| **跨模块通信** | ★★★☆☆ | 有端口+适配器雏形，但仅 2 模块局部尝试；Kafka 仅外部回流 |
| **一致性策略** | ★★★☆☆ | 事务封装有模板，但无 Saga/Outbox，最终一致性靠幂等+归档 |
| **配置管理** | ★★★★☆ | pydantic settings + YAML 分层覆盖，设计规范 |
| **错误处理** | ★★★☆☆ | 统一 AppError 基类 + 全局 handler，但 JWT 绕过体系 |
| **认证授权** | ★★★☆☆ | 手写 JWT（非 PyJWT），RBAC 在 Depends 层，无中间件 |
| **路由装配** | ★★★★☆ | router_registry 自动注册设计好，但模块路径仍硬编码 |
| **可测试性** | ★★☆☆☆ | 无 Repository 抽象 + 跨模块硬编码 import，Mock 困难 |

**综合评分：★★★☆☆（3/5）** — 架构方向正确，但落地一致性不足，存在多个分层穿透和耦合点，可测试性是最大短板。

---

## 三、关键架构问题（按严重程度排序）

### 🔴 P0-1：无 Repository 抽象层，service 与 ODM 强耦合

**现状**：全项目 26 个 service 文件直接调用 Beanie Document 的 `.find()/.find_one()/.insert()/.save()/.aggregate()` 方法。`BaseService` 仅提供 `_doc_to_dict` 工具方法，无数据访问抽象。

**证据**：
```python
# app/modules/auth/service/user_service.py:20,31
await UserDoc.find_one(...)
await doc.insert()

# app/modules/execution_plan/service/execution_plan_service.py:48
docs = await ExecutionPlanDoc.find(*filters).sort("-updated_at").to_list()
```

**影响**：
- 无法在单测中 Mock 数据访问层，核心业务逻辑不可独立测试
- service 同时承担业务逻辑 + 数据持久化双重职责，违反单一职责
- 切换 ODM（如 Motor→Beanie）需改动所有 service

**建议**：不必为每个 Document 建接口（过度设计），但核心模块（test_specs/execution/execution_plan）应抽取 Repository 协议，service 依赖协议而非具体 Document。简单 CRUD 模块可保留现状。

---

### 🔴 P0-2：跨模块直接 import repository 模型（分层穿透）

**现状**：模块间依赖几乎全部通过直接 import 对方的 `repository.models` Document 实现，而非通过端口或应用服务。

**证据**：
| 调用方 | 被依赖模块 | 证据 |
|--------|-----------|------|
| `ai_analysis/service/ai_service.py:6-8` | test_case_collection + test_specs + system_config | 直接 import 3 个模块的 repository/service |
| `execution_plan/service/execution_plan_service.py:14,26` | execution + test_specs + auth | import 3 个模块的 repository.models |
| `project/service/project_service.py:10-11,34` | auth + execution_plan + workflow | import 3 个模块的 repository.models |
| `search/service/search_service.py:6-14` | execution + test_specs | import 多个 repository.models |
| `failure_analysis/api/routes.py:96` | test_specs | **API 层直接 import 跨模块 repository** |
| `notification/service.py:22` | auth | import repository.models.rbac |

**影响**：
- 模块边界形同虚设，任何模块变更可能波及多个调用方
- 无法独立替换或演进单个模块
- 编译期即产生强耦合，无法做模块级隔离测试

**建议**：
1. 短期：API 层（failure_analysis）的跨模块 import 必须下沉到 service/application 层
2. 中期：高频跨模块依赖（execution↔execution_plan、test_specs↔ai_analysis）通过 Port 接口解耦
3. 长期：引入模块间事件机制，将同步调用改为发布订阅

---

### 🔴 P0-3：domain 层反向依赖 repository（违反分层核心原则）

**现状**：`workflow/domain/rules.py` 声称"不依赖 HTTP/数据库"，但实际 import 了 `repository.models.OwnerStrategy`。

**证据**：
```python
# app/modules/workflow/domain/rules.py:5-9
"""
工作流领域规则
只包含业务语义逻辑，不依赖 HTTP/数据库。
"""
from app.modules.workflow.repository.models import OwnerStrategy  # ← 违规
```

**影响**：domain 层失去纯逻辑优势，无法脱离数据库环境测试，注释与代码矛盾。

**建议**：将 `OwnerStrategy` 枚举从 repository 模型文件移到 domain/constants.py，domain 层只依赖自身。同时全局检查其他 domain 文件是否有类似违规。

---

### 🟡 P1-1：端口抽象被适配器绕过

**现状**：`execution_plan/application/ports.py` 定义了 `ExecutionDispatchPort` 和 `PlanNotificationPort`，但 `adapters.py` 的适配器实现仍直接 import 了 4 个外部模块（execution 的 service + repository + schemas，notification 的 service + constants）。

**证据**：
```python
# app/modules/execution_plan/application/adapters.py:10-12,17-22
from app.modules.execution.application.task_command_service import ExecutionTaskCommandService
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.schemas import DispatchCaseItem, DispatchTaskRequest
from app.modules.notification.constants import NotificationTemplates, ...
from app.modules.notification.service import NotificationService
```

**影响**：端口定义了抽象，但适配器实现把所有具体依赖拉了回来，解耦只停留在接口签名层面，实际编译期耦合未减少。

**建议**：适配器应放在被依赖模块内部（execution 模块提供 ExecutionDispatchAdapter 并注册到 execution_plan），而非由 execution_plan 自己 import 对方。或使用运行时动态加载（importlib）消除编译期依赖。

---

### 🟡 P1-2：14 模块分层结构不一致

**现状**：14 个模块存在 5 种分层模式：

| 模式 | 模块数 | 示例 |
|------|--------|------|
| 完整 6 层 (api/application/domain/repository/schemas/service) | 3 | execution_plan, execution, test_specs |
| 有 application 无 service | 1 | workflow（application 替代 service） |
| 有 domain/repository 无 application | 5 | auth, project, system_config, test_case_collection, attachments, audit |
| 仅 api/schemas/service | 3 | ai_analysis, failure_analysis, search |
| 极简（service.py 在模块根） | 1 | notification（无 api/schemas/domain） |

**影响**：新人无法预期一个模块的结构，维护成本高；application 与 service 职责边界模糊。

**建议**：不必强行统一所有模块到 6 层（简单模块不需要 application 层），但需明确规则：
- 简单 CRUD 模块：api → service → repository（3 层）
- 复杂业务模块：api → application(CQRS) → service → domain → repository（5 层）
- notification 的 service.py 应移入 service/ 子目录

---

### 🟡 P1-3：application 与 service 职责重叠

**现状**：`test_specs` 同时有 application 和 service 层，但 query service 多为 service 的薄包装。

**证据**：
```python
# test_specs/api/dependencies.py — query service 内部委托 service
RequirementQueryService(requirement_service)
TestCaseCommandService(test_case_service, ...)
```

**影响**：增加了一层无实质逻辑的转发，代码量膨胀；CQRS 有雏形但未真正分离读写模型。

**建议**：明确 application 层职责 = 跨模块编排 + 事务边界 + DTO 转换；service 层职责 = 单模块业务逻辑 + 数据访问。若 application 层只是委托，应合并到 service。

---

### 🟡 P1-4：shared 基础设施职责越界

**现状**：`shared/redis/api/routes.py` 和 `shared/ai/embedding_routes.py` 在基础设施层暴露 HTTP 路由，通过 router_registry 注册。

**证据**：
```python
# app/shared/api/router_registry.py:30
"app.shared.redis.api",   # ← shared 模块注册业务路由
```

**影响**：基础设施层不应有业务路由，混淆了基础设施与应用层的边界。

**建议**：将 redis 健康检查路由移到 `shared/api/routes.py`（已有的 health_router），将 embedding 路由移到 `ai_analysis` 模块或新建 `ai_gateway` 模块。

---

### 🟢 P2-1：JWT 手写实现

**现状**：`shared/auth/jwt_auth.py` 手写 HS256 签名（`_sign_hs256` + `create_access_token` + `decode_token`），未使用 PyJWT 库。

**影响**：手写加密实现有安全隐患（时序攻击、密钥处理、算法降级等），且缺少 refresh token / 黑名单等标准功能。

**建议**：替换为 PyJWT 或 python-jose，安全审计后迁移。

---

### 🟢 P2-2：JWT 校验绕过 AppError 体系

**现状**：`jwt_auth.py` 中 token 校验失败直接 `raise HTTPException(401)`，而非抛出 `PermissionDeniedError(AppError)`。

**影响**：异常走 `http_exception_handler` 而非 `app_error_handler`，返回格式与业务异常不一致。

**建议**：JWT 校验失败统一抛 `PermissionDeniedError`，由全局 handler 统一格式化。

---

### 🟢 P2-3：无中间件层，认证授权全在 Depends

**现状**：项目无 `app/middleware/` 目录（除日志/审计中间件在 shared/middleware），认证授权完全靠路由 `Depends(get_current_user)` + `Depends(require_permission(...))`。

**影响**：每个路由需手动声明权限依赖，遗漏即无保护；无法做全局请求级统一鉴权。

**建议**：保持 Depends 级别的细粒度权限控制（灵活性好），但增加一个轻量认证中间件做全局 token 校验兜底，避免遗漏。

---

### 🟢 P2-4：无领域事件，模块间无事件解耦

**现状**：Kafka 仅作为"外部执行端→平台"的事件回流通道（`event_ingest_service` 消费执行结果），模块间通信全部同步调用。无领域事件（domain event）概念。

**影响**：跨模块副作用（如用例创建后触发通知、执行完成后更新计划状态）只能同步调用，增加响应延迟和耦合。

**建议**：当前规模下同步调用可接受，但高频跨模块副作用（如 notification、audit）可引入轻量内存事件总线（如 `blinker` 或自建 EventBus）解耦。不必引入 Kafka 做内部事件。

---

## 四、架构亮点

### 1. 路由自动注册机制

`router_registry.py` 通过 `register_router()` + `importlib.import_module` 实现模块路由自动注册，各模块 `api/__init__.py` 自行声明，消除了 main.py 的手动 include_router。设计干净，扩展友好。

### 2. 事务模板封装

`test_specs/service/_service_support.py` 的 `create_with_workflow_transaction` 将"业务实体 + workflow item 原子创建"封装为可复用的事务模板，支持 `redundant_fields` 回填，是很好的抽象。

### 3. 配置管理

`shared/config/settings.py` 的 `@lru_cache` 单例 + pydantic 分层（10 个子配置）+ YAML 深合并覆盖 + 环境变量，配置管理规范，类型安全。

### 4. 全局错误处理

`AppError` 基类 + 模块异常继承 + `setup_exception_handlers` 按优先级注册 + `isinstance` 推断状态码，异常到 HTTP 状态码的映射清晰。

### 5. Kafka 消费路由

`KafkaTopicHandlerRegistry` 做 `topic→schema→handler` 路由分发，配合 dead_letter 队列，消费侧架构成熟。

### 6. 工作流状态机

`workflow` 模块以配置驱动的状态机引擎为核心，业务实体通过 `workflow_item_id` 关联工作项，状态作为"投影"而非实存字段，保证了状态单一真实来源。

---

## 五、架构改进路线图

### 阶段一：止血（1-2 周）— ✅ P0 已完成
1. ✅ **修复 domain 反向依赖**：`OwnerStrategy` 从 `repository/models/enums.py` 迁移到 `domain/enums.py`，repository 层 re-export 保持向后兼容；`domain/rules.py` 改为 import domain 层
2. ✅ **API 层穿透修复**：`failure_analysis/api/routes.py` 的 `TestCaseDoc` 直接查询下沉到 `FailureAnalysisService.fetch_case_for_ai_analysis()`，API 层不再 import 任何跨模块 repository
3. ✅ **核心模块 Repository 协议**：新增 `test_specs/domain/repositories.py`（`TestCaseRepositoryProtocol`）+ `test_specs/repository/test_case_repository.py`（`TestCaseRepository` 实现）；`TestCaseService` 构造器注入协议，`_get_active_case` 通过仓储协议访问数据
4. **待办**：JWT 手写实现替换为 PyJWT
5. **待办**：JWT 异常统一为 `PermissionDeniedError`

### 阶段二：解耦（2-4 周）
5. **高频跨模块依赖通过 Port 解耦**：execution↔execution_plan、test_specs↔ai_analysis
6. **适配器归位**：ExecutionDispatchAdapter 移到 execution 模块，由 execution_plan 通过端口注入
7. **shared 路由归位**：redis/ai 路由移出 shared

### 阶段三：增强可测试性（4-8 周）
8. **核心模块抽取 Repository 协议**：test_specs/execution/execution_plan 的 service 依赖协议而非 Document
9. **分层规则文档化**：明确简单模块 3 层、复杂模块 5 层的标准
10. **application/service 职责边界明确**：合并纯委托的 query service

### 阶段四：演进（长期）
11. **领域事件**：notification/audit 等副作用改为事件订阅
12. **Outbox 模式**：跨模块写操作引入 Outbox 保证最终一致性
13. **模块清单自动化**：router_registry 的 `_API_MODULE_PATHS` 改为自动扫描

---

## 六、结论

DML V4 后端的架构 **方向正确但落地参差**。DDD 分层、端口适配器、CQRS、配置驱动等理念都有体现，但执行不一致：14 模块 5 种分层、端口被绕过、domain 反向依赖、26 个 service 直接操作 ODM。最紧迫的问题是 **可测试性**——无 Repository 抽象 + 跨模块硬编码 import 使得核心业务逻辑几乎无法独立单测。

建议按"止血→解耦→可测试性→演进"四阶段推进，优先修复 P0 的分层违规和耦合问题，2-4 周内即可显著提升架构健康度。

---

*报告基于代码静态分析生成，所有结论附文件路径与行号证据。*
