# 后端代码结构评审报告 & 优化方案

> 生成日期：2026-06-18
> 评审范围：backend/app 全部模块
> 目标：高可读性、高可扩展性、简化代码配置

---

## 目录

- [一、架构总览](#一架构总览)
- [二、核心问题与风险](#二核心问题与风险)
- [三、模块化架构一致性](#三模块化架构一致性)
- [四、配置系统评审](#四配置系统评审)
- [五、依赖注入与耦合](#五依赖注入与耦合)
- [六、数据库模型与重复代码](#六数据库模型与重复代码)
- [七、异常处理与日志](#七异常处理与日志)
- [八、认证与RBAC](#八认证与rbac)
- [九、具体优化方案](#九具体优化方案)
- [十、实施优先级建议](#十实施优先级建议)

---

## 一、架构总览

### 1.1 项目结构

```
backend/app/
├── main.py                    # FastAPI 入口 + lifespan
├── modules/                   # 16 个业务模块（架构不一致）
│   ├── workflow               # 完整分层（api/application/domain/repo/service）
│   ├── test_specs             # 完整分层 + application 层
│   ├── execution              # 完整分层 + 庞大 application 层（18 文件）
│   ├── execution_plan         # 传统分层（api/service/domain/repo）
│   ├── auth                   # 传统分层（api/service/repo）
│   ├── project                # 传统分层（api/service/domain/repo）
│   ├── system_config          # 传统分层
│   ├── test_case_collection   # 传统分层（缺 domain）
│   ├── attachments            # 传统分层（缺 domain）
│   ├── ai_analysis            # 薄模块（api/service/schemas）
│   ├── failure_analysis       # 薄模块（api/service/schemas）
│   ├── search                 # 薄模块（api/service/schemas）
│   ├── redis                  # 薄模块（含 domain — 异常）
│   └── notification           # 空模块（无实质内容）
├── shared/                    # 横切关注点
│   ├── api/                   # 路由汇总、中间件、错误处理
│   ├── auth/                  # JWT、密码
│   ├── config/                # 配置系统（YAML + Pydantic）
│   ├── core/                  # 日志、Mongo 客户端、Mixin（未使用）
│   ├── db/                    # 数据库连接
│   ├── domain/                # 共享异常基类
│   ├── enums/                 # 枚举汇总（跨模块导入）
│   ├── infrastructure/        # 启动流程、基础设施注册表
│   ├── kafka/                 # Kafka 生产/消费
│   ├── minio/                 # 对象存储
│   ├── rabbitmq/              # 消息队列
│   └── service/               # BaseService、SequenceIdService
└── workers/                   # 后台 Worker（Kafka Worker）
```

### 1.2 模块架构矩阵

| 模块 | api | service | application | domain | repository | schemas | 状态 |
|------|-----|---------|-------------|--------|------------|---------|------|
| workflow | ✅ | ❌(空) | ✅ | ✅ | ✅ | ✅ | 异常：service 目录为空 |
| test_specs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 正常 |
| execution | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 正常 |
| execution_plan | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 正常 |
| project | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 正常 |
| auth | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | 缺 domain |
| system_config | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 正常 |
| test_case_collection | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | 缺 domain |
| attachments | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | 缺 domain |
| ai_analysis | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | 缺 repo/domain |
| failure_analysis | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | 缺 repo/domain |
| search | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | 缺 repo/domain |
| redis | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 异常：redis 不应该有 domain |
| notification | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 空模块 |

**结论**：16 个模块中仅 3 个（workflow, test_specs, execution）拥有完整的 application 层，其余模块要么没有，要么架构不完整。notification 模块完全为空。

---

## 二、核心问题与风险

### 2.1 🔴 严重：模块架构不一致（可扩展性阻碍）

**问题**：同一项目内存在 3 种不同的架构风格：
- **CQRS 风格**（workflow）：application/ 下有 mutation_service.py + query_service.py + commands.py + ports.py
- **混合风格**（test_specs, execution）：既有 application/ 层又有传统 service/ 层
- **传统风格**（project, auth, execution_plan）：只有 api → service → repository

**影响**：
- 新开发者无法判断新模块应该使用哪种架构
- 同一模块内的业务逻辑分散在 service/ 和 application/ 两层，职责边界模糊
- workflow 的 service/ 目录为空，但 application/ 下有 8 个服务文件，命名混乱

### 2.2 🔴 严重：共享层反向依赖业务模块（架构耦合）

**问题**：`app/shared/` 作为底层横切关注点，却反向导入 `app/modules/` 中的业务代码。

**具体实例**（12 处）：

| shared 文件 | 导入的模块 | 问题 |
|-------------|-----------|------|
| `shared/auth/jwt_auth.py` | `app.modules.auth.repository.models` | 认证基类依赖业务模型 |
| `shared/api/errors/handlers.py` | `workflow, test_specs, execution_plan` 的 domain exceptions | 错误处理耦合所有模块 |
| `shared/infrastructure/bootstrap.py` | **所有模块**的 `DOCUMENT_MODELS` | 启动流程硬编码所有模块 |
| `shared/infrastructure/registry.py` | `app.modules.execution.service.task_scheduler` | 基础设施依赖执行模块 |
| `shared/enums/api.py` | `execution, execution_plan, test_specs, workflow` | 枚举 API 反向汇总模块枚举 |
| `shared/kafka/health.py` | `execution.application.worker_presence` | Kafka 健康检查依赖执行模块 |

**影响**：
- 任何模块的重构都可能影响 shared 层，导致牵一发动全身
- 无法独立测试 shared 层（必须加载所有模块）
- 破坏了分层架构的基本原则：上层依赖下层，下层不依赖上层

### 2.3 🟡 中：Mixin 定义但未使用（大量重复代码）

**问题**：`app/shared/core/document_mixins.py` 中定义了 `TimestampedDocumentMixin` 和 `SoftDeleteDocumentMixin`，但所有 25+ 个 Beanie Document 模型都手动实现了这些字段。

**统计**：
- `created_at` / `updated_at` 字段：重复 25 次
- `@before_event([Save, Insert])` 更新时间戳：重复 25 次
- `is_deleted: bool = False`：重复 25 次
- `IndexModel("is_deleted")`：重复 15 次
- `project_ids` 字段：重复 10 次

**修复收益**：使用 Mixin 可减少每模型约 15 行重复代码，总计约 400 行。

### 2.4 🟡 中：手动 JWT 实现（安全可维护性）

**问题**：`app/shared/auth/jwt_auth.py` 使用 `hmac` + `json` + `base64` 手动实现 JWT，而非标准库（python-jose / PyJWT）。

**风险**：
- 手写 JWT 实现容易出现边界情况漏洞（padding、base64url 转码等）
- 缺少标准库的标准化测试覆盖
- 代码维护成本高，每次 JWT 规范更新都需要手动调整

### 2.5 🟡 中：路由注册手动维护（可扩展性）

**问题**：`app/shared/api/main.py` 中手动 import 并注册 19 个模块的路由：

```python
from app.modules.workflow.api import router as workflow_router
from app.modules.test_specs.api import ...
# ... 共 19 个 import
api_router.include_router(workflow_router, prefix="/api/v1", tags=["WorkItems"])
# ... 共 19 行注册
```

**影响**：每次新增模块都需要修改此文件，容易遗漏，违反了开闭原则。

### 2.6 🟡 中：配置文件中硬编码敏感信息

**问题**：`config.yaml` 中硬编码了密码、JWT 密钥、MongoDB URI 等敏感信息：
- `jwt.secret_key: "CHANGE_ME"`（虽然叫 CHANGE_ME 但已经提交）
- MongoDB URI 可能包含生产环境地址
- RabbitMQ 密码明文存储

### 2.7 🟡 中：异常处理不一致

**问题**：三种不同的异常处理模式并存：
1. **全局异常处理器**（`app/shared/api/errors/handlers.py`）——捕获 AppError 子类
2. **路由层手动 try/except**（多数 routes.py 中）——`except ValueError: raise HTTPException(400, ...)`
3. **Service 层抛 ValueError**——无类型化异常

**具体影响**：
- 路由层和全局处理器同时处理同一类异常，存在重复逻辑
- 大量路由中的 `try/except ValueError` 模式淹没了业务逻辑
- 没有统一的异常转换策略

### 2.8 🟡 中：BaseService 继承不一致

**统计**：
- 继承 `BaseService` 的：TestCaseService, RequirementService, ExecutionPlanService, ProjectService, NavigationPageService, AutomationTestCaseService
- 不继承 `BaseService` 的：AuthServiceSupport（继承 BaseService），SearchService, AIService, FailureAnalysisService, CollectionService, AttachmentService, CatalogService, LabService, RoleService, PermissionService

**问题**：`BaseService` 仅提供 `_doc_to_dict`、`_filter_updates`、`_apply_updates` 三个方法，但 50% 的服务类没有使用它。这意味着：
- 要么 `BaseService` 的功能不够通用，要么
- 要么服务类没有遵循统一的更新/转换模式

### 2.9 🟡 中：日志使用不一致

**统计**：
- 13 个文件使用 `from app.shared.core.logger import log as logger`
- 但还有许多模块未使用共享 logger（如 ai_analysis、search、failure_analysis 可能使用 print 或标准 logging）
- 日志消息中混杂中英文，没有统一规范

### 2.10 🟢 低：通知模块为空

`app/modules/notification/` 目录下只有一个 `service.py`（仅包含 `NotificationService` 的骨架调用），没有任何 API 路由、模型、schemas。

**建议**：要么实现完整功能，要么删除该模块。

---

## 三、模块化架构一致性

### 3.1 问题：application 层职责不清

**现状**：
- **workflow** 的 `application/` 包含：commands.py, mutation_service.py, query_service.py, ports.py（CQRS 模式）
- **test_specs** 的 `application/` 包含：test_case_command_service.py, requirement_command_service.py, query_services.py（命令/查询分离）
- **execution** 的 `application/` 包含：task_command_service.py, task_dispatch_service.py, event_ingest_service.py, agent_service.py 等 18 个文件

**问题**：
- `application/` 和 `service/` 的边界在哪里？为什么 test_specs 既有 `service/test_case_service.py` 又有 `application/test_case_command_service.py`？
- 一个业务操作（如创建测试用例）需要调用 3 个不同的 service（TestCaseService + TestCaseCommandService + WorkflowCommandService），层级混乱

### 3.2 优化方案：统一架构模式

**推荐方案 A**：所有模块统一为 **API → Application → Service → Repository** 四层

```
module/
├── api/                    # FastAPI 路由 + 参数校验
│   ├── routes.py           # 路由定义
│   ├── dependencies.py     # 依赖注入工厂
│   └── exception_handler.py # 模块级异常处理（可选）
├── application/            # 用例编排（复杂业务流程）
│   ├── commands.py         # 命令对象（简单模块可省略）
│   └── ...                 # 仅当业务需要跨模块协调时使用
├── service/                # 领域逻辑 + 数据操作
│   └── xxx_service.py      # 每个聚合根一个服务
├── domain/                 # 领域规则 + 异常 + 常量
│   ├── exceptions.py
│   ├── constants.py
│   └── policies.py         # 业务规则（可选）
├── repository/             # 数据模型
│   └── models/
│       └── xxx.py
└── schemas/                # Pydantic 请求/响应模型
    └── xxx.py
```

**规则**：
- **简单 CRUD**（project, attachments, test_case_collection）：无需 application/ 层，API 直接调用 Service
- **复杂业务**（workflow, execution）：需要 application/ 层协调多个 Service 和跨模块调用
- **当前有 service/ 也有 application/ 的模块**（test_specs, execution）：明确职责边界——application/ 负责编排，service/ 负责原子操作
- **domain/ 为空或仅含异常文件**：如果 domain 只有 `exceptions.py`，可以合并到 service/ 或统一在 `shared/domain/exceptions.py` 中定义

**推荐方案 B**：如果不需要 application/ 层的区分，直接删除所有模块的 `application/` 目录，统一为 `API → Service → Repository` 三层（当前 80% 的模块已使用此模式）

**推荐**：选择方案 A（保留 application/ 但明确职责），并删除 test_specs 的 `service/` 中那些与 `application/` 重复的文件。

---

## 四、配置系统评审

### 4.1 优点

- 使用 Pydantic 模型进行类型校验
- 支持 `config.yaml` + `config_dev.yaml` + 环境变量三级覆盖
- 单例模式通过 `@lru_cache` 实现
- 子配置按功能分组清晰（App, MongoDB, Kafka, JWT 等）

### 4.2 问题

| # | 问题 | 影响 | 优化方案 |
|---|------|------|----------|
| 1 | `config.yaml` 含硬编码敏感信息 | 安全风险 | 将敏感值改为 `${ENV_VAR}` 占位符，使用 `pydantic-settings` 或环境变量覆盖 |
| 2 | `get_config_path()` 遍历 3 层 parent 查找 `requirements.txt` | 脆弱 | 改用 `PROJECT_ROOT` 环境变量或固定路径 |
| 3 | `config.yaml.example` 与 `config.yaml` 同步问题 | 维护成本 | 使用 `config.yaml` 作为模板，实际敏感值从 `.env` 加载 |
| 4 | 环境变量覆盖仅支持 `DML_APP_PORT` | 不灵活 | 支持 `DML_` 前缀的环境变量自动映射到配置树（如 `DML_MONGODB_URI`） |
| 5 | 无配置变更热重载 | 需重启服务 | 对调试场景，提供 `reload` 端点刷新配置缓存 |

### 4.3 优化方案：敏感信息脱敏

```yaml
# config.yaml（脱敏后的模板）
app:
  host: "0.0.0.0"
  port: 8801
  dev_bypass_auth: ${DML_DEV_BYPASS_AUTH:-false}

mongodb:
  uri: ${DML_MONGODB_URI:-mongodb://localhost:27017}
  db_name: ${DML_MONGODB_DB:-workflow_db}

jwt:
  secret_key: ${DML_JWT_SECRET:-}  # 空值则启动时报错，强制配置
```

使用 `pydantic-settings` 或 `string.Template` 实现环境变量替换。

---

## 五、依赖注入与耦合

### 5.1 问题：shared 层反向依赖 modules

**核心原则违反**：`app/shared/` 不应该导入 `app/modules/` 的任何内容。

**修复方案**：将模块特定的依赖从 shared 中抽离

| 文件 | 当前依赖 | 修复方案 |
|------|----------|----------|
| `shared/auth/jwt_auth.py` | `UserDoc, RoleDoc, PermissionDoc` | 定义 `UserDoc` 的 Protocol/Interface，或把 JWT 逻辑移到 `modules/auth/service/jwt_service.py` |
| `shared/api/errors/handlers.py` | 各模块的 domain exceptions | 所有模块异常统一继承 `AppError`，handlers 只依赖 `AppError` 基类 |
| `shared/infrastructure/bootstrap.py` | 所有模块的 `DOCUMENT_MODELS` | 使用 **自动发现**（注册表模式）替代硬编码 import |
| `shared/enums/api.py` | 各模块的枚举 | 将枚举定义移到各自模块，shared 只提供路由框架，枚举由模块注册 |
| `shared/kafka/health.py` | `execution` 模块 | 使用回调/事件机制解耦，execution 注册健康检查回调 |

### 5.2 优化方案：自动注册 Beanie 模型

**当前**（`bootstrap.py`）：
```python
from app.modules.workflow.repository.models import DOCUMENT_MODELS as WORKFLOW_DOCUMENT_MODELS
from app.modules.test_specs.repository.models import DOCUMENT_MODELS as TEST_SPECS_DOCUMENT_MODELS
# ... 13 个硬编码 import

def get_document_models():
    return [
        *WORKFLOW_DOCUMENT_MODELS,
        *TEST_SPECS_DOCUMENT_MODELS,
        # ...
    ]
```

**优化后**（注册表模式）：
```python
# app/shared/infrastructure/document_registry.py
_document_registry: list[type] = []

def register_document_model(model_cls: type) -> type:
    _document_registry.append(model_cls)
    return model_cls

def get_document_models() -> list[type]:
    return list(_document_registry)

# 在各模块的 repository/models/__init__.py 中使用
document_models = [ModelA, ModelB]
for model in document_models:
    register_document_model(model)
```

这样 `bootstrap.py` 不再需要知道任何模块的存在。

### 5.3 优化方案：枚举路由自动注册

**当前**（`shared/enums/api.py`）：
```python
from app.modules.execution.application.constants import AgentStatus, ...
from app.modules.execution_plan.domain.constants import PlanItemStatus, ...
from app.modules.test_specs.repository.models import REQUIREMENT_CATEGORY_CHOICES, ...
from app.modules.workflow.repository.models.enums import ...
```

**优化后**：
```python
# 各模块在启动时注册自己的枚举
enum_registry: dict[str, list[str]] = {}

def register_enum(name: str, values: list[str]) -> None:
    enum_registry[name] = values

# 在 app/shared/api/main.py 中初始化时调用各模块
# 或通过依赖注入的注册机制
```

---

## 六、数据库模型与重复代码

### 6.1 核心优化：使用 Mixin 消除重复

**当前模式**（重复 25 次）：
```python
class SomeDoc(Document):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = Field(default=False)

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        indexes = [IndexModel("is_deleted")]
```

**优化后**（使用现有 Mixin）：
```python
# app/shared/core/document_mixins.py（已存在，需完善）
class TimestampedDocumentMixin:
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

class SoftDeleteDocumentMixin:
    is_deleted: bool = Field(default=False)

# 使用方式
class SomeDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    # ... 业务字段
    class Settings:
        indexes = [
            IndexModel("is_deleted"),
            # ... 其他索引
        ]
```

**收益**：每模型减少 8-12 行重复代码，总计约 300 行。

### 6.2 优化：project_ids 字段标准化

**当前**：10 个模型各自定义 `project_ids: List[str] = Field(default_factory=list, description="关联的项目 ID 列表")`

**优化**：创建 `ProjectRelatedMixin`：
```python
class ProjectRelatedMixin:
    project_ids: List[str] = Field(default_factory=list, description="关联的项目 ID 列表")

    class Settings:
        indexes = [IndexModel("project_ids")]
```

### 6.3 优化：索引配置 DRY

**当前**：每个模型重复 `IndexModel("is_deleted")` 和 `IndexModel("project_ids")`

**优化**：Mixin 的 `Settings.indexes` 通过 metaclass 或 Beanie 的 `Document` 子类自动合并。

---

## 七、异常处理与日志

### 7.1 统一异常处理策略

**当前三层异常处理**：
1. 路由层 `try/except ValueError → HTTPException(400)`
2. 全局 handlers `AppError → 对应 HTTP 状态码`
3. Service 层随意抛出 `ValueError` / `RuntimeError`

**优化方案**：

```python
# 1. 定义模块级异常（继承 AppError）
class ProjectNotFoundError(NotFoundError):
    """项目不存在。"""

class DuplicateKeyError(ConflictError):
    """标识重复。"""

# 2. Service 层只抛模块异常
async def update_project(...) -> ProjectDoc:
    doc = await ProjectDoc.find_one(...)
    if not doc:
        raise ProjectNotFoundError(f"项目不存在: {project_id}")
    # ...

# 3. 路由层不再手动 catch
@router.put("/{project_id}")
async def update_project(...):
    # 无需 try/except，全局 handler 自动转换
    doc = await service.update_project(...)
    return APIResponse(data=...)
```

**需要删除的路由级异常处理**：
- `project/api/routes.py` 中所有 `try/except ValueError`
- `test_specs/api/*.py` 中所有 `try/except ValueError`
- `execution_plan/api/routes.py` 中所有 `try/except ...`

**保留**全局 handlers 的 `AppError` 映射，这是唯一需要的异常处理层。

### 7.2 日志统一

**当前问题**：
- 中文日志和英文日志混合（"Project created" vs "项目已创建"）
- 部分模块未使用 `app.shared.core.logger`

**优化方案**：
1. 统一使用结构化日志 `from app.shared.core.logger import log`
2. 统一中文日志（因为项目是中国团队开发）
3. 所有 service 层操作都记录 `logger.info("操作描述", 关键参数)`

---

## 八、认证与 RBAC

### 8.1 JWT 实现替换

**当前**：手动实现 JWT（`hmac` + `json` + `base64`）

**优化**：使用 `python-jose` 或 PyJWT：

```python
from jose import jwt, JWTError

SECRET = get_settings().jwt.secret_key
ALGORITHM = get_settings().jwt.algorithm

def create_token(data: dict) -> str:
    return jwt.encode(data, SECRET, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise AuthenticationError("无效的 token")
```

**收益**：
- 减少 60 行手写代码
- 获得标准的安全审计和测试覆盖
- 支持更多算法（RS256 等）

### 8.2 权限检查优化

**当前**：`require_permission()` 使用全局查询，每次请求都查数据库

**优化**：在 JWT 中嵌入权限列表（空间换时间）：

```python
# 登录时计算权限并写入 token
permissions = await get_user_permissions(user_id)
token_data = {
    "sub": user_id,
    "permissions": permissions,  # 缓存权限
    # ...
}

# 校验时直接读 token，不查数据库
def require_permission(code: str):
    def checker(current_user=Depends(get_current_user)):
        if code not in current_user.get("permissions", []):
            raise PermissionDeniedError()
    return checker
```

---

## 九、具体优化方案

### 9.1 方案 1：修复共享层反向依赖（优先级：高）

**目标**：让 `app/shared/` 不再依赖 `app/modules/`

**步骤**：
1. 将 `shared/auth/jwt_auth.py` 中的 `UserDoc` 查询移到 `modules/auth/service/jwt_service.py`
2. 将 `shared/api/errors/handlers.py` 中的模块异常处理改为基于 `AppError` 基类的统一处理
3. 将 `shared/infrastructure/bootstrap.py` 改为注册表模式，使用 `register_document_model()`
4. 将 `shared/enums/api.py` 改为枚举注册表模式
5. 将 `shared/kafka/health.py` 中的执行模块依赖改为回调注册

**预计改动**：15-20 个文件，约 300 行代码变更。

### 9.2 方案 2：统一 Mixin 使用（优先级：高）

**目标**：消除所有模型的重复字段和重复更新时间戳方法。

**步骤**：
1. 完善 `app/shared/core/document_mixins.py`：
   - 添加 `IndexModel` 到 Mixin 的 `Settings`
   - 确保 Beanie 支持 Mixin 的 `Settings` 合并
2. 批量修改所有 25+ 个 Document 模型：
   - 添加 `TimestampedDocumentMixin` + `SoftDeleteDocumentMixin`
   - 删除手动定义的 `created_at`, `updated_at`, `is_deleted`
   - 删除 `@before_event` 方法
3. 添加 `ProjectRelatedMixin` 给需要 `project_ids` 的模型

**预计改动**：30+ 个文件，但主要是删减，净减少约 400 行代码。

### 9.3 方案 3：统一模块架构（优先级：中）

**目标**：所有模块遵循一致的分层架构。

**步骤**：
1. **workflow 模块**：
   - 将 `application/` 下所有文件移动到 `service/`（因为 service/ 为空，且 application/ 实际上就是服务层）
   - 或：明确 `application/` 只保留命令编排，`service/` 保留原子操作
2. **test_specs 模块**：
   - 合并 `application/` 和 `service/` 中重复职责的文件
   - 例如：`test_case_command_service.py` 和 `test_case_service.py` 职责重叠，应合并为一个
3. **空模块处理**：
   - 删除或完善 `notification` 模块
4. **redis 模块**：
   - 删除 `domain/` 目录（redis 是基础设施，不应有业务领域）

**预计改动**：20 个文件，涉及文件移动和合并。

### 9.4 方案 4：路由自动注册（优先级：中）

**目标**：新增模块无需修改 `app/shared/api/main.py`。

**步骤**：
1. 定义 `RouterRegistry`：
```python
# app/shared/api/router_registry.py
_api_routers: list[tuple[APIRouter, str, str]] = []

def register_router(router: APIRouter, prefix: str = "/api/v1", tags: list[str] | None = None):
    _api_routers.append((router, prefix, tags or []))

def get_registered_routers() -> list[tuple[APIRouter, str, str]]:
    return list(_api_routers)
```
2. 在各模块的 `api/__init__.py` 中调用注册：
```python
from app.shared.api.router_registry import register_router
from .routes import router

register_router(router, prefix="/api/v1", tags=["Projects"])
```
3. 在 `app/main.py` 中遍历注册的路由：
```python
from app.shared.api.router_registry import get_registered_routers
for router, prefix, tags in get_registered_routers():
    api_router.include_router(router, prefix=prefix, tags=tags)
```

**预计改动**：5-10 个文件。

### 9.5 方案 5：配置系统脱敏（优先级：高）

**目标**：敏感信息从配置文件中移除。

**步骤**：
1. 修改 `config.yaml`：所有密码、密钥改为 `${ENV_VAR}` 占位符
2. 添加 `.env.example` 文件说明环境变量
3. 修改 `settings.py`：支持 `pydantic-settings` 或 `string.Template` 替换
4. 启动时校验：如果 JWT secret 为空，报错并退出

**预计改动**：5 个文件。

### 9.6 方案 6：异常处理统一（优先级：中）

**目标**：删除路由层的手动异常处理，统一由全局 handler 处理。

**步骤**：
1. 为每个模块定义 `domain/exceptions.py`，继承 `AppError`
2. 删除所有路由文件中的 `try/except ValueError` 块
3. 在全局 handler 中增加常见异常的映射：
```python
exception_map = {
    NotFoundError: (404, "资源不存在"),
    ConflictError: (409, "资源冲突"),
    ValidationError: (400, "参数校验失败"),
    PermissionDeniedError: (403, "权限不足"),
    # ...
}
```

**预计改动**：15-20 个路由文件。

### 9.7 方案 7：JWT 替换（优先级：低）

**目标**：使用标准 JWT 库。

**步骤**：
1. 添加 `python-jose` 到 `pyproject.toml`
2. 重写 `app/shared/auth/jwt_auth.py` 中的编码/解码逻辑
3. 保留现有接口（`create_token`, `decode_token`, `get_current_user`）不变

**预计改动**：2 个文件，减少约 60 行代码。

---

## 十、实施优先级建议

### 优先级矩阵

| 优先级 | 方案 | 影响 | 工作量 | 风险 |
|--------|------|------|--------|------|
| 🔴 P0 | 5. 配置脱敏 | 安全 | 小 | 低 |
| 🔴 P0 | 2. Mixin 使用 | 可维护 | 中 | 低（纯删减） |
| 🔴 P0 | 1. 共享层反向依赖 | 架构 | 大 | 中（需测试） |
| 🟡 P1 | 6. 异常统一 | 可读性 | 中 | 低 |
| 🟡 P1 | 4. 路由自动注册 | 可扩展 | 小 | 低 |
| 🟡 P1 | 3. 统一架构 | 可维护 | 大 | 中（涉及文件移动） |
| 🟢 P2 | 7. JWT 替换 | 安全 | 小 | 低 |
| 🟢 P2 | 删除空模块 | 整洁 | 小 | 低 |

### 推荐实施顺序

1. **阶段 1**（1-2 天）：配置脱敏 + Mixin 使用（纯删减，安全）
2. **阶段 2**（2-3 天）：共享层反向依赖修复（需要仔细测试）
3. **阶段 3**（2-3 天）：异常统一 + 路由自动注册（低风险）
4. **阶段 4**（3-5 天）：统一模块架构（文件移动和合并）
5. **阶段 5**（1 天）：JWT 替换 + 清理空模块

---

## 附录：问题清单（供修复者使用）

### 文件级问题清单

| 文件路径 | 问题 | 修复建议 |
|----------|------|----------|
| `app/shared/auth/jwt_auth.py` | 导入 `app.modules.auth.repository.models` | 提取 UserDoc 接口，或将 JWT 逻辑移到 auth 模块 |
| `app/shared/api/errors/handlers.py` | 导入各模块的 domain exceptions | 统一基于 `AppError` 基类处理 |
| `app/shared/infrastructure/bootstrap.py` | 硬编码 13 个模块的 DOCUMENT_MODELS import | 改为注册表模式 |
| `app/shared/enums/api.py` | 导入 4 个模块的枚举 | 改为枚举注册表 |
| `app/shared/kafka/health.py` | 导入 execution 模块 | 使用回调注册机制 |
| `app/shared/core/document_mixins.py` | 定义了但未被使用 | 批量应用到所有 Document 模型 |
| `app/shared/api/main.py` | 手动 import 19 个路由 | 改为自动注册 |
| `app/modules/notification/` | 空模块 | 删除或实现 |
| `app/modules/redis/domain/` | 基础设施模块不应有 domain | 删除 domain 目录 |
| `app/modules/workflow/service/` | 空目录 | 将 application/ 文件移入，或删除 service/ |
| `app/modules/*/repository/models/*.py` | 重复 `created_at`, `updated_at`, `is_deleted`, `@before_event` | 使用 Mixin |
| `app/modules/*/api/routes.py` | 大量 `try/except ValueError` | 删除，改用全局异常处理 |
| `config.yaml` | 硬编码密码和密钥 | 改为环境变量占位符 |
| `pyproject.toml` | 缺少 `python-jose`（如替换 JWT） | 按需添加 |

### 代码重复统计

| 重复模式 | 出现次数 | 涉及文件数 | 优化后节省行数 |
|----------|----------|------------|----------------|
| `created_at` + `updated_at` 字段 | 25 | 25 | ~75 行 |
| `@before_event` 更新方法 | 25 | 25 | ~250 行 |
| `is_deleted` 字段 | 25 | 25 | ~25 行 |
| `IndexModel("is_deleted")` | 15 | 15 | ~15 行 |
| `project_ids` 字段 | 10 | 10 | ~10 行 |
| `IndexModel("project_ids")` | 10 | 10 | ~10 行 |
| **合计** | **110** | **~30** | **~385 行** |
