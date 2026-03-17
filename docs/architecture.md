# DMLV4 后端架构说明

## 1. 文档范围

本文档只描述当前仓库中已经实现的后端能力，不覆盖 `frontend/` 目录。

当前后端由 FastAPI 提供 HTTP API，使用 MongoDB + Beanie 作为持久化层，围绕以下 4 个模块组织：

- `workflow`：配置驱动工作流与通用业务事项
- `test_specs`：测试需求、测试用例、自动化测试用例库
- `execution`：测试任务编排与执行代理接入
- `auth`：JWT 认证与 RBAC 权限控制

## 2. 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 数据访问 | Beanie ODM |
| 数据库 | MongoDB |
| 配置 | `pydantic-settings` + `.env` |
| 鉴权 | JWT |
| 执行分发 | Kafka 或 HTTP |
| 测试 | pytest |

## 3. 目录结构

```text
dmlv4/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── init_mongodb.py
│   │   ├── configs/
│   │   ├── modules/
│   │   │   ├── workflow/
│   │   │   ├── test_specs/
│   │   │   ├── execution/
│   │   │   └── auth/
│   │   └── shared/
│   │       ├── api/
│   │       ├── auth/
│   │       ├── core/
│   │       ├── db/
│   │       ├── infrastructure/
│   │       ├── kafka/
│   │       └── service/
│   ├── scripts/
│   └── docs/
└── docs/
```

说明：

- `backend/app/modules/assets` 当前不存在，不应作为已交付模块写入公开架构文档。
- `backend/app/shared/api/main.py` 目前仍引用了 `assets_router`，但该实现不在当前仓库中；本文档不将其视为可用后端能力。

## 4. 分层约束

项目整体遵循以下分层：

- API 层：`app/modules/*/api`
- Application/Service 层：`app/modules/*/application`、`app/modules/*/service`
- Repository 层：`app/modules/*/repository`
- Domain 层：`app/modules/*/domain`

约束如下：

- API 层负责参数解析、鉴权依赖、异常到 HTTP 状态码的映射。
- 业务编排放在 application/service 层，不在路由层直接写数据库操作。
- 规则校验和领域异常放在 domain 层。
- 数据模型与查询实现放在 repository 层。

## 5. 启动与生命周期

服务入口是 `backend/app/main.py`。启动时按顺序执行：

1. 连接 MongoDB。
2. 初始化全部 Beanie 文档模型。
3. 校验 workflow 基础配置一致性。
4. 初始化应用级基础设施。
5. 挂载异常处理器和统一 API 路由。

关闭时会：

1. 关闭应用级基础设施。
2. 关闭 MongoDB 连接。
3. 清理全局 Mongo 客户端引用。

补充说明：

- 若 workflow 配置尚未初始化，启动时会告警，但不会直接阻断服务。
- `init_beanie(...)` 会注册文档模型并确保索引。

## 6. 模块说明

### 6.1 workflow

`workflow` 是配置驱动的状态机模块，也是需求、用例等业务对象的流转基础设施。

核心文档模型：

- `SysWorkTypeDoc`
- `SysWorkflowStateDoc`
- `SysWorkflowConfigDoc`
- `BusWorkItemDoc`
- `BusFlowLogDoc`

提供的主要能力：

- 查询事项类型、流程状态、流转配置
- 创建业务事项
- 查询、搜索、排序事项
- 状态流转
- 改派负责人
- 查询单项或批量流转日志

核心路由前缀：

- `/api/v1/work-items`

### 6.2 test_specs

`test_specs` 模块负责测试需求、测试用例及自动化测试用例库管理。

核心文档模型：

- `TestRequirementDoc`
- `TestCaseDoc`
- `AutomationTestCaseDoc`

提供的主要能力：

- 需求 CRUD
- 用例 CRUD
- 自动化测试用例库创建、查询
- 手工用例关联自动化用例

核心路由前缀：

- `/api/v1/requirements`
- `/api/v1/test-cases`
- `/api/v1/automation-test-cases`

### 6.3 execution

`execution` 模块采用“平台主导串行 case 执行”模型，而不是一次性整批下发。

当前模型特点：

- 一个任务可包含多条 case。
- 平台每次只推进当前 1 条 case。
- 外部执行端持续回传事件、case 状态和任务完成结果。
- 同一任务支持重试，并保留独立轮次历史。

核心文档模型：

- `ExecutionAgentDoc`
- `ExecutionTaskDoc`
- `ExecutionTaskCaseDoc`
- `ExecutionTaskRunDoc`
- `ExecutionTaskRunCaseDoc`
- `ExecutionEventDoc`

核心路由前缀：

- `/api/v1/execution`

### 6.4 auth

`auth` 模块负责用户认证、角色权限管理和导航访问控制。

核心文档模型：

- `UserDoc`
- `RoleDoc`
- `PermissionDoc`
- `NavigationPageDoc`

提供的主要能力：

- 用户登录
- 用户、角色、权限 CRUD
- 用户角色绑定
- 角色权限绑定
- 当前用户权限查询
- 导航页面定义管理
- 用户导航可见性管理

核心路由前缀：

- `/api/v1/auth`

## 7. 工作流配置

工作流规则定义在 `backend/app/configs/*.json`，通过 `backend/app/init_mongodb.py` 同步到 MongoDB。

初始化脚本会做几类处理：

- 合并多个配置文件中的 `work_types`
- 合并并校验 `states`
- 合并并校验 `workflow_configs`
- 推导状态是否为终态
- 增量 upsert 到 MongoDB
- 清理配置中已移除的工作流类型和流转规则

新增工作流类型的标准方式：

1. 在 `backend/app/configs/` 下新增或修改 JSON 配置。
2. 运行 `python app/init_mongodb.py`。
3. 重启服务并观察启动期的一致性校验结果。

## 8. API 注册与统一响应

统一路由注册入口在 `backend/app/shared/api/main.py`。

当前后端公开可确认的主要路由：

- `/health`
- `/api/v1/work-items`
- `/api/v1/requirements`
- `/api/v1/test-cases`
- `/api/v1/automation-test-cases`
- `/api/v1/execution`
- `/api/v1/auth`

统一响应封装格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## 9. 配置项

核心配置定义在 `backend/app/shared/db/config.py`。

常用项包括：

- `MONGO_URI`
- `MONGO_DB_NAME`
- `CORS_ORIGINS`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_EXPIRE_MINUTES`
- `JWT_ISSUER`
- `JWT_AUDIENCE`
- `EXECUTION_DISPATCH_MODE`
- `EXECUTION_AGENT_DISPATCH_PATH`
- `EXECUTION_HTTP_TIMEOUT_SEC`
- `EXECUTION_SCHEDULER_INTERVAL_SEC`

说明：

- 默认值中包含开发环境示例，不应直接视为生产配置。
- 真实部署应通过 `backend/.env` 覆盖。

## 10. 数据与约束

通用约束：

- 时间字段统一使用 UTC。
- 多数业务数据使用软删除字段 `is_deleted`。
- 查询逻辑应显式排除软删除数据。
- 索引定义在 Beanie 文档模型中。

执行模块的额外约束：

- `DispatchTaskRequest.cases` 不能为空，且 `case_id` 不能重复。
- `schedule_type` 只允许 `IMMEDIATE` 或 `SCHEDULED`。
- 定时任务修改只允许发生在未触发前。

## 11. 建议阅读顺序

- 初次接手后端：先看本文档
- 理解工作流：看 `docs/guide/test-requirements-cases.md`
- 理解执行链路：看 `docs/guide/test-execution.md`
- 理解鉴权：看 `docs/guide/authentication.md`
