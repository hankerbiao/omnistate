# DML V4 — Test Management Platform

DML V4 是一个面向测试管理场景的全栈平台，后端基于 FastAPI + MongoDB，前端基于 React + TypeScript + Vite。

系统围绕测试需求管理、测试用例管理、执行编排、权限治理四大主线组织，覆盖从"定义测试对象"到"推动测试执行"的完整闭环。

## 系统定位

后端围绕 4 条主线组织：

1. **测试需求管理** — 沉淀测试需求、维护需求状态，作为后续测试设计和执行的业务源头
2. **测试用例管理** — 维护手工测试用例和自动化测试用例，以及与需求之间的关联关系
3. **配置驱动工作流** — 用统一状态机描述业务事项的状态流转，并记录完整流转日志
4. **执行编排与权限治理** — 调度测试执行，通过 JWT + RBAC 控制访问权限

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI |
| 数据存储 | MongoDB |
| ODM | Beanie |
| 认证方式 | JWT |
| 权限模型 | RBAC |
| 消息队列 | RabbitMQ / Kafka |
| 前端框架 | React 19 + TypeScript |
| 前端构建 | Vite |

## 目录结构

```text
dmlv4/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── init_mongodb.py      # 初始化工作流配置、RBAC 基础数据
│   │   ├── configs/             # 工作流配置（JSON）
│   │   ├── modules/
│   │   │   ├── workflow/        # 配置驱动工作流引擎
│   │   │   ├── test_specs/      # 测试需求与测试用例
│   │   │   ├── execution/       # 测试执行编排（串行 case）
│   │   │   ├── execution_plan/  # 执行计划管理
│   │   │   ├── search/          # 全局搜索
│   │   │   ├── auth/            # RBAC 认证授权
│   │   │   ├── attachments/     # 文件附件
│   │   │   ├── system_config/   # 系统配置与 AI 工具
│   │   │   ├── ai_analysis/     # AI 分析
│   │   │   ├── terminal/        # 终端管理
│   │   │   ├── test_case_collection/ # 预制用例集
│   │   │   └── failure_analysis/     # 失败分析
│   │   └── shared/
│   │       ├── api/             # 统一路由、错误处理、响应模型
│   │       ├── auth/            # JWT 与权限依赖
│   │       ├── core/            # 日志、Mongo client
│   │       ├── db/              # 配置加载
│   │       ├── kafka/           # Kafka 消费与消息管理
│   │       ├── rabbitmq/        # RabbitMQ 消息管理
│   │       └── infrastructure/  # 应用级基础设施初始化
│   ├── scripts/
│   │   ├── init/                # 初始化脚本（RBAC、用户创建）
│   │   ├── auth/                # Token 生成
│   │   ├── mock/                # 模拟数据与服务
│   │   └── maintenance/         # 维护脚本
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/          # UI 组件
│       ├── pages/               # 页面级组件
│       ├── services/            # API 客户端
│       ├── providers/           # 全局状态（Auth、Navigation）
│       ├── config/              # 导航配置
│       └── types/               # TypeScript 类型定义
└── docs/
```

## 后端模块

### 1. `workflow` — 工作流引擎

配置驱动的状态机模块，是整套系统的流转基础设施。

- 管理事项类型、状态定义、流转规则
- 创建和流转业务事项 `BusWorkItemDoc`
- 记录流转日志 `BusFlowLogDoc`
- 校验必填字段、动作合法性和目标状态

### 2. `test_specs` — 测试规格

测试需求与测试用例管理模块。

- 管理测试需求 `TestRequirementDoc`
- 管理测试用例 `TestCaseDoc`
- 管理自动化测试用例 `AutomationTestCaseDoc`
- 维护需求和用例的关联关系

### 3. `execution` — 执行编排

测试执行编排模块，采用平台主导的串行 case 执行模型。

- 一个任务包含多条 case，平台逐条下发
- 外部执行端回报 case 状态，推进下一条
- 全部 case 完成后自动收口

### 4. `execution_plan` — 执行计划

管理手工执行计划和任务，支持计划创建、条目分发、结果回填和归档。

- 计划 CRUD、用例关联、指派人分配
- 条目分发（单条/批量）、结果回填
- 归档与取消归档

### 5. `search` — 全局搜索

跨模块全文搜索，支持按类型筛选。

- 搜索需求、用例、自动化用例、执行任务、评论
- 类型过滤、高亮显示

### 6. `auth` — 认证授权

RBAC 认证授权模块。

- 用户、角色、权限 CRUD
- 用户角色绑定、角色权限绑定
- JWT 登录认证
- 导航页面权限控制

### 7. `attachments` — 附件管理

文件附件上传与管理。

### 8. `system_config` — 系统配置

全局配置管理与 AI 工具接口。

- 配置项增删改查、历史追溯
- AI 连接测试、文本润色

### 9. `ai_analysis` — AI 分析

AI 驱动的用例集质量分析。

- 用例质量评分、冗余检测、覆盖分析

### 10. `terminal` — 终端管理

执行代理终端管理。

### 11. `test_case_collection` — 预制用例集

预制测试用例集合管理。

### 12. `failure_analysis` — 失败分析

测试执行失败分析模块。

## API 路由

统一前缀：`/api/v1`

| 路由 | 标签 | 说明 |
|------|------|------|
| `GET /health` | Health | 健康检查 |
| `POST /api/v1/auth/login` | Auth | 登录 |
| `GET/PUT /api/v1/auth/users/me` | Auth | 当前用户 |
| `GET /api/v1/auth/users/me/permissions` | Auth | 当前用户权限 |
| `GET/POST /api/v1/work-items` | WorkItems | 工作事项 |
| `GET/POST /api/v1/requirements` | Requirements | 测试需求 |
| `GET/POST /api/v1/test-cases` | TestCases | 测试用例 |
| `GET/POST /api/v1/automation-test-cases` | AutomationTestCases | 自动化用例 |
| `GET/POST /api/v1/execution/tasks` | Execution | 执行任务 |
| `GET/POST /api/v1/execution-plans/plans` | ExecutionPlans | 执行计划 |
| `GET /api/v1/search` | Search | 全局搜索 |
| `GET /api/v1/collections` | TestCaseCollection | 预制用例集 |
| `GET/PUT /api/v1/system-configs` | SystemConfig | 系统配置 |
| `POST /api/v1/ai/polish` | AITools | AI 文本润色 |
| `POST /api/v1/ai-analyze` | AIAnalysis | AI 用例分析 |

统一响应格式：

```json
{ "code": 0, "message": "ok", "data": {} }
```

## 启动指南

### 环境要求

- Python 3.10+
- MongoDB 6.0+
- Node.js 18+

### 后端

```bash
cd backend
pip install -r requirements.txt
python app/init_mongodb.py
python scripts/init/init_rbac.py
python -m app.main
```

初始化账号：

```bash
cd backend
python scripts/init/create_user.py \
  --user-id admin \
  --username "系统管理员" \
  --password 'Admin@123' \
  --roles ADMIN \
  --email admin@example.com \
  --upsert
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 推荐阅读顺序

1. [backend/README.md](backend/README.md)
2. [backend/app/shared/api/main.py](backend/app/shared/api/main.py)
3. [backend/app/configs/README.md](backend/app/configs/README.md)
4. [backend/app/modules/workflow/README.md](backend/app/modules/workflow/README.md)
5. [backend/app/modules/test_specs/README.md](backend/app/modules/test_specs/README.md)
6. [backend/app/modules/execution/README.md](backend/app/modules/execution/README.md)
7. [backend/app/modules/execution_plan/README.md](backend/app/modules/execution_plan/README.md)
8. [backend/app/modules/search/README.md](backend/app/modules/search/README.md)
9. [backend/app/modules/auth/README.md](backend/app/modules/auth/README.md)
10. [docs/项目架构规范.md](docs/项目架构规范.md)
11. [docs/后端接口说明.md](docs/后端接口说明.md)
12. [docs/认证与登录指南.md](docs/认证与登录指南.md)

## 相关文档

- [后端 README](backend/README.md)
- [前端 README](frontend/README.md)
- [项目配置说明](backend/app/configs/README.md)
- [脚本工具说明](backend/scripts/README.md)
- [docs/](docs/) — 架构规范、接口说明、认证指南等
