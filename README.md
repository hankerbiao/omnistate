# DML V4 Backend

DML V4 是一个面向测试管理场景的后端服务，核心关注点不是页面展示，而是把测试需求、测试用例、工作流流转、执行编排和权限控制组织成一套可落库、可审计、可扩展的业务系统。

当前仓库虽然包含 `frontend` 目录，但本文档只介绍后端业务、架构和开发方式。

## 系统定位

后端围绕 4 条主线组织：

1. 测试需求管理
   负责沉淀测试需求、维护需求状态，并作为后续测试设计和执行的业务源头。
2. 测试用例管理
   负责维护手工测试用例和自动化测试用例，以及它们与需求之间的关联关系。
3. 配置驱动工作流
   用统一状态机描述业务事项如何从一个状态流转到另一个状态，并记录完整流转日志。
4. 执行编排与权限治理
   用平台驱动方式串行调度测试执行，同时通过 JWT + RBAC 控制谁能查看、编辑、流转和触发执行。

整体上，它更像一个“测试业务中台”后端，而不是单一的 CRUD 服务。

## 核心业务闭环

系统的典型闭环如下：

1. 初始化工作流配置和 RBAC 基础数据。
2. 创建测试需求，描述要验证的对象、范围和目标。
3. 基于需求设计测试用例，并维护与需求的关联。
4. 通过工作流推进事项状态，比如草稿、评审、执行中、完成等。
5. 将测试用例编排成执行任务，由平台按 case 串行下发给外部执行端。
6. 接收执行进度、case 状态和结果回传，沉淀任务当前态与历史轮次。
7. 通过 RBAC 控制不同角色对需求、用例、执行任务和管理能力的访问范围。

这套闭环把“定义测试对象”与“推动测试执行”连在一起，中间通过 workflow 和 execution 两个模块承接状态推进与运行编排。

## 技术栈

- Web 框架：FastAPI
- 数据存储：MongoDB
- ODM：Beanie
- 认证方式：JWT
- 权限模型：RBAC
- API 风格：统一 `/api/v1` 前缀 + Envelope 响应结构

统一响应格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## 后端模块

### 1. `workflow`

配置驱动的工作流引擎，是整套系统的流转基础设施。

主要职责：

- 管理事项类型、状态定义、流转规则
- 创建业务事项 `BusWorkItemDoc`
- 按规则执行状态流转
- 记录流转日志 `BusFlowLogDoc`
- 校验必填字段、动作合法性和目标状态

关键特点：

- 工作流规则来自 `backend/app/configs/*.json`
- 启动阶段会做一致性校验，避免脏配置进入运行期
- 流转日志可用于审计和排障

### 2. `test_specs`

测试规格管理模块，负责沉淀“测什么”和“怎么测”。

主要职责：

- 管理测试需求 `TestRequirementDoc`
- 管理测试用例 `TestCaseDoc`
- 管理自动化测试用例库 `AutomationTestCaseDoc`
- 维护需求和用例的关联关系

当前关系模型：

- 一个需求可以关联多个测试用例
- 一个测试用例归属一个需求
- 自动化测试用例作为独立库维护，可与测试用例建立关联

### 3. `execution`

测试执行编排模块，负责把测试任务从“待执行”推进到“已完成”。

当前模型不是一次性整批下发所有 case，而是平台主导的串行执行：

- 一个任务可以包含多条 case
- 平台当前只下发 1 条 case
- 外部执行端执行后回报该 case 的状态
- 当当前 case 进入终态后，平台再推进下一条
- 全部 case 完成后，平台自动收口任务

执行数据分为两层：

- 当前态：任务现在执行到哪里，用于编排和实时展示
- 历史态：某个任务第 N 次执行的完整记录，用于追溯和分析

这使系统既能做在线调度，也能保留完整执行历史。

### 4. `auth`

认证授权模块，负责登录、鉴权和菜单/导航访问控制。

主要职责：

- 用户、角色、权限 CRUD
- 用户和角色绑定
- 角色和权限绑定
- JWT 登录认证
- 当前用户权限查询
- 导航页面权限控制

默认角色包括：

- `ADMIN`
- `TPM`
- `TESTER`
- `AUTOMATION`

### 5. `assets`

API 汇总入口中已挂载 `assets` 路由前缀，但当前仓库内未提供完整模块文档。根目录 README 不展开描述其内部实现，建议以实际代码或后续模块文档为准。

## 目录结构

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
│   ├── scripts/
│   └── tests/
├── docs/
└── README.md
```

几个重要入口：

- [backend/app/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/main.py)：FastAPI 入口与生命周期管理
- [backend/app/init_mongodb.py](/Users/libiao/Desktop/github/dmlv4/backend/app/init_mongodb.py)：初始化工作流配置、权限和导航基础数据
- [backend/app/shared/api/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/shared/api/main.py)：统一 API 路由注册入口
- [backend/scripts/init_rbac.py](/Users/libiao/Desktop/github/dmlv4/backend/scripts/init_rbac.py)：初始化默认权限与角色
- [backend/scripts/create_user.py](/Users/libiao/Desktop/github/dmlv4/backend/scripts/create_user.py)：创建本地用户

## 启动时会发生什么

服务入口在 [backend/app/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/main.py)。

启动阶段主要做这些事：

1. 连接 MongoDB。
2. 初始化 Beanie 文档模型。
3. 校验 workflow 配置一致性。
4. 初始化应用级基础设施。
5. 注册异常处理、健康检查和业务路由。

关闭阶段会：

1. 关闭应用级基础设施。
2. 关闭 MongoDB 连接。
3. 清理全局 Mongo client。

## API 边界

统一业务前缀：`/api/v1`

当前主要路由如下：

- `/health`
- `/api/v1/work-items`
- `/api/v1/requirements`
- `/api/v1/test-cases`
- `/api/v1/automation-test-cases`
- `/api/v1/execution`
- `/api/v1/auth`
- `/api/v1/assets`

其中最关键的几类业务接口是：

- 工作事项与状态流转
- 测试需求与测试用例管理
- 自动化测试用例维护
- 执行任务创建、查询、事件回调、重试与调度
- 用户登录、权限查询、角色权限管理

## 本地开发

### 环境要求

- Python 3.10+
- MongoDB 6.0+

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 配置环境变量

在 `backend/.env` 中至少配置：

```env
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB_NAME=workflow_db
CORS_ORIGINS=["http://localhost:3000"]

JWT_SECRET_KEY=PLEASE_CHANGE_ME
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
JWT_ISSUER=tcm-backend
JWT_AUDIENCE=tcm-frontend
```

### 初始化基础数据

```bash
cd backend
python app/init_mongodb.py
python scripts/init_rbac.py
```

如果需要创建管理员或演示账号：

```bash
cd backend
python scripts/create_user.py --user-id admin001 --username "系统管理员" --password 'Admin@123' --roles ADMIN --email admin@example.com --upsert
```

说明：

- `app/init_mongodb.py` 会同步 workflow 配置，并初始化权限、角色和导航基础数据
- `scripts/init_rbac.py` 可单独幂等初始化默认 RBAC 数据
- `scripts/create_user.py` 会校验角色是否存在，并对密码做哈希存储

### 启动服务

```bash
cd backend
python -m app.main
```

默认访问地址：

- Swagger：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`
- Health：`http://localhost:8000/health`

## 测试与检查

### pytest

```bash
cd backend
pytest
pytest tests/unit/workflow/test_workflow_service.py -v
pytest tests/integration/ -v
pytest --cov=app
```

### flake8

```bash
cd backend
flake8
flake8 app/modules/workflow/service/
flake8 --select=E,W,F
```

当前约束：

- `max-line-length = 110`
- `max-complexity = 12`

## 推荐阅读顺序

如果你第一次接手这个后端，建议按这个顺序看代码：

1. [backend/app/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/main.py)
2. [backend/app/shared/api/main.py](/Users/libiao/Desktop/github/dmlv4/backend/app/shared/api/main.py)
3. [backend/app/modules/workflow/README.md](/Users/libiao/Desktop/github/dmlv4/backend/app/modules/workflow/README.md)
4. [backend/app/modules/test_specs/README.md](/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_specs/README.md)
5. [backend/app/modules/execution/README.md](/Users/libiao/Desktop/github/dmlv4/backend/app/modules/execution/README.md)
6. [backend/app/modules/auth/README.md](/Users/libiao/Desktop/github/dmlv4/backend/app/modules/auth/README.md)

## 相关文档

- [backend/README.md](/Users/libiao/Desktop/github/dmlv4/backend/README.md)
- [docs/项目架构规范.md](/Users/libiao/Desktop/github/dmlv4/docs/项目架构规范.md)
- [docs/后端接口说明.md](/Users/libiao/Desktop/github/dmlv4/docs/后端接口说明.md)
- [docs/认证与登录指南.md](/Users/libiao/Desktop/github/dmlv4/docs/认证与登录指南.md)
- [docs/测试字段文档总览.md](/Users/libiao/Desktop/github/dmlv4/docs/测试字段文档总览.md)
