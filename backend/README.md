# DML V4 Backend

`backend` 是 DML V4 的 FastAPI 后端，当前不只是“Workflow API”，而是一个围绕测试需求、测试用例、执行编排、资产管理和 RBAC 的统一服务。

当前代码的几个核心事实：

- Web 框架是 FastAPI
- 数据层是 MongoDB + Beanie ODM
- API 统一挂在 `/api/v1`
- 工作流规则由 `app/configs/*.json` 初始化到 MongoDB
- 测试执行采用“平台主导串行 case 执行”模型

## 目录概览

```text
backend/
├── app/
│   ├── main.py                    # FastAPI 入口、Mongo/Beanie 初始化、基础设施生命周期
│   ├── init_mongodb.py            # 初始化工作流、状态、RBAC 基础数据
│   ├── configs/                   # 工作流和初始化配置
│   ├── modules/
│   │   ├── workflow/              # 配置驱动工作流
│   │   ├── test_specs/            # 测试需求、测试用例、自动化测试用例
│   │   ├── execution/             # 测试执行编排
│   │   ├── assets/                # 资产与部件管理
│   │   └── auth/                  # 用户、角色、权限、导航
│   └── shared/
│       ├── api/                   # 通用路由、错误处理、响应模型
│       ├── auth/                  # JWT 与权限依赖
│       ├── core/                  # 日志、Mongo client 等基础能力
│       ├── db/                    # 配置加载
│       ├── infrastructure/        # Kafka 等应用级基础设施初始化
│       ├── kafka/                 # Kafka 消费和消息管理
│       └── service/               # 共享服务
├── scripts/                       # 初始化与运维脚本
└── tests/                         # pytest 测试
```

## 模块说明

### workflow

配置驱动的状态机模块，是业务流转基础设施。

职责：

- 管理 `SysWorkTypeDoc`、`SysWorkflowStateDoc`、`SysWorkflowConfigDoc`
- 创建和流转 `BusWorkItemDoc`
- 记录 `BusFlowLogDoc`
- 提供事项创建、查询、流转、改派、日志查询能力

### test_specs

测试需求与测试用例管理模块。

职责：

- 管理测试需求 `TestRequirementDoc`
- 管理测试用例 `TestCaseDoc`
- 管理自动化测试用例 `AutomationTestCaseDoc`
- 与 `workflow` 和 `execution` 形成业务闭环

### execution

测试执行编排模块，不再是“整批测试用例一次下发”的模型。

当前设计：

- 一个任务可以包含多条 case
- 平台只下发当前 1 条 case
- 外部执行框架只执行当前 case 并回报结果
- 平台在 case 终态后推进下一条
- 最后一条 case 完成后平台自动收口任务

详细设计见
[app/modules/execution/README.md](/Users/libiao/Desktop/github/dmlv4/backend/app/modules/execution/README.md)。

### assets

资产管理模块。

职责：

- 管理 Component Library
- 管理 DUT 资产
- 管理测试计划与部件的关联关系

### auth

RBAC 权限模块。

职责：

- 用户、角色、权限 CRUD
- 用户角色绑定
- 角色权限绑定
- 导航页面权限控制
- 为各业务模块提供鉴权基础

## 启动流程

入口是 [app/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/main.py)。

服务启动时会按顺序做这些事：

1. 连接 MongoDB
2. 初始化 Beanie 文档模型
3. 校验 workflow 配置一致性
4. 初始化应用级基础设施
5. 注册统一异常处理器和 API 路由

服务关闭时会：

1. 关闭应用级基础设施
2. 关闭 MongoDB 连接
3. 清理全局 Mongo client

## API 路由

统一注册入口是 [app/shared/api/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/shared/api/main.py)。

当前主要路由前缀如下：

- `/health`
  健康检查
- `/api/v1/work-items`
  workflow 模块
- `/api/v1/assets`
  assets 模块
- `/api/v1/requirements`
  测试需求
- `/api/v1/test-cases`
  测试用例
- `/api/v1/automation-test-cases`
  自动化测试用例
- `/api/v1/execution`
  测试执行编排
- `/api/v1/auth`
  RBAC

统一响应格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## 本地开发

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 初始化基础数据

```bash
cd backend
python app/init_mongodb.py
python scripts/init_rbac.py
python scripts/create_user.py
```

说明：

- `app/init_mongodb.py` 会把 `app/configs/*.json` 中的工作流配置同步到 MongoDB
- `scripts/init_rbac.py` 初始化权限、角色等 RBAC 数据
- `scripts/create_user.py` 用于创建初始管理员

### 3. 启动服务

```bash
cd backend
python -m app.main
```

默认监听 `0.0.0.0:8000`。

## 测试与检查

### pytest

```bash
cd backend

# 全量测试
pytest

# 指定模块
pytest tests/unit/workflow/ -v

# 集成测试
pytest tests/integration/ -v

# 覆盖率
pytest --cov=app
```

### flake8

仓库根目录的 [`.flake8`](/Users/libiao/Desktop/github/dmlv4/.flake8) 当前约束：

- `max-line-length = 110`
- `max-complexity = 12`

运行方式：

```bash
cd backend
flake8
flake8 app/modules/execution/
flake8 --select=E,W,F
```

## 配置说明

运行配置来自 [app/shared/db/config.py](/Users/libiao/Desktop/github/dmlv4/backend/app/shared/db/config.py) 和 `.env`。

重点配置通常包括：

- `MONGO_URI`
- `MONGO_DB_NAME`
- `CORS_ORIGINS`
- Kafka 相关配置
- 执行代理和分发通道相关配置
- JWT 相关配置

不要把真实凭据提交到仓库。

## 数据与架构约束

### 分层约束

项目遵循明确分层：

- API 层：`app/modules/*/api`
- Service/Application 层：`app/modules/*/service` 或 `app/modules/*/application`
- Repository 层：`app/modules/*/repository`
- Domain 层：`app/modules/*/domain`

要求：

- API 不直接操作底层数据库
- 路由层尽量只做参数接收、权限依赖、调用 service、返回响应
- 业务规则放在 service/application/domain，不要散落到路由层

### MongoDB 约束

- 文档模型统一由 Beanie 管理
- 业务数据大量使用软删除字段 `is_deleted`
- 查询时应显式考虑软删除条件
- 索引定义应写在文档模型中，不要把索引逻辑散落到运行时代码

### workflow 约束

workflow 配置必须自洽：

- `type_code` 必须存在
- `from_state` 和 `to_state` 必须存在
- 启动时会执行一致性校验

如果 MongoDB 中没有初始化数据，服务会告警并跳过 workflow 一致性检查；这适合空环境启动，但不代表业务可正常运行。

## execution 模块补充说明

执行模块是当前后端里变化最大的部分，维护时需要特别注意下面几点：

- 平台是任务推进的唯一编排者
- 外部执行框架不应该提前完成整任务
- `ExecutionTaskDoc` 保存任务级快照
- `ExecutionTaskCaseDoc` 保存任务内单条 case 的执行明细
- 推进下一条 case 时依赖任务上的编排锁，避免并发重复下发
- `request_payload` 表示任务完整原始快照，不是最近一次单 case 下发载荷

如果要继续修改执行编排，先阅读
[app/modules/execution/README.md](/Users/libiao/Desktop/github/dmlv4/backend/app/modules/execution/README.md)。

## 常见维护入口

- 修改服务启动与生命周期：
  [app/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/main.py)
- 修改路由注册：
  [app/shared/api/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/shared/api/main.py)
- 修改 Mongo 初始化逻辑：
  [app/init_mongodb.py](/Users/libiao/Desktop/github/dmlv4/backend/app/init_mongodb.py)
- 修改 execution 编排：
  参考模块文档
  [app/modules/execution/README.md](/Users/libiao/Desktop/github/dmlv4/backend/app/modules/execution/README.md)
- 修改统一异常处理：
  参考异常处理入口
  [app/shared/api/errors/handlers.py](/Users/libiao/Desktop/github/dmlv4/backend/app/shared/api/errors/handlers.py)

## 后续建议

- 根 README 和各模块 README 要保持同步，避免出现“根文档还是旧架构、模块文档已经是新实现”的分叉
- 任何新增模块都应在
  [app/shared/api/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/shared/api/main.py)
  和本文件里同步登记
- 如果执行、鉴权或基础设施再发生结构变化，应优先更新文档，再推进接口调整
