# DMLV4 系统架构规范

## 1. 系统概述

DMLV4（Dual-stack Management and Lab V4）是一个双栈系统，用于服务器测试用例设计和执行管理：

- **后端**：配置驱动的工作流状态机服务（Python + FastAPI + Beanie ODM + MongoDB）
- **前端**：测试用例设计和管理 Web 应用（React + TypeScript + Vite）

### 核心特性

- 配置驱动的工作流引擎（JSON 规则定义）
- 测试需求、测试用例、自动化测试用例管理
- 平台主导的串行 Case 执行模式
- 完整的 RBAC 权限体系
- 资产管理（组件库、DUT）

---

## 2. 技术栈

### 后端

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| ORM | Beanie (MongoDB async) |
| 数据库 | MongoDB |
| 数据验证 | Pydantic |
| 消息队列 | Kafka |
| 认证 | JWT |
| 测试 | pytest |

### 前端

| 组件 | 技术 |
|------|------|
| 框架 | React 19 |
| 语言 | TypeScript |
| 构建工具 | Vite 8 |
| 样式 | Plain CSS |
| HTTP | Fetch API |

---

## 3. 项目结构

```
dmlv4/
├── backend/                      # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py               # FastAPI 入口、生命周期管理
│   │   ├── init_mongodb.py       # MongoDB 初始化脚本
│   │   ├── configs/              # 工作流 JSON 配置
│   │   ├── modules/              # 业务模块
│   │   │   ├── workflow/         # 工作流状态机
│   │   │   ├── test_specs/       # 测试需求/用例
│   │   │   ├── execution/        # 测试执行编排
│   │   │   ├── assets/           # 资产管理
│   │   │   └── auth/             # RBAC 权限
│   │   └── shared/               # 共享基础设施
│   │       ├── api/              # 路由、错误处理
│   │       ├── auth/             # JWT 鉴权
│   │       ├── core/             # 日志、Mongo 客户端
│   │       ├── db/               # 配置加载
│   │       ├── infrastructure/   # Kafka 等基础设施
│   │       ├── kafka/            # Kafka 消费者
│   │       └── service/          # 共享服务
│   ├── scripts/                  # 运维脚本
│   └── tests/                    # pytest 测试
│
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── App.tsx               # 主组件（单文件架构）
│   │   ├── components/           # UI 组件
│   │   ├── services/             # API 服务层
│   │   ├── types/                # TypeScript 类型
│   │   └── assets/               # 静态资源
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                         # 项目文档
└── requirements.txt              # Python 依赖
```

---

## 4. 后端架构详解

### 4.1 分层架构

项目遵循 **API → Service/Application → Repository/Domain** 的分层原则：

```
┌─────────────────────────────────────────────┐
│  API Layer (api/routes)                     │
│  - 接收请求、参数校验                        │
│  - 权限依赖                                 │
│  - 调用 Service                              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Service/Application Layer                  │
│  - 业务逻辑                                  │
│  - 事务管理                                  │
│  - 编排多个 Repository 操作                  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Repository Layer                           │
│  - 数据访问                                  │
│  - Beanie 文档操作                           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Domain Layer                               │
│  - 领域模型                                  │
│  - 业务规则                                  │
└─────────────────────────────────────────────┘
```

**约束**：

- API 层不直接操作数据库
- 业务规则放在 Service/Application 层
- Repository 层只做数据访问

### 4.2 模块说明

#### workflow 模块

配置驱动的状态机模块，是业务流转基础设施。

**职责**：
- 管理 `SysWorkTypeDoc`、`SysWorkflowStateDoc`、`SysWorkflowConfigDoc`
- 创建和流转 `BusWorkItemDoc`
- 记录 `BusFlowLogDoc`

**核心功能**：
- 创建事项（自动进入 DRAFT 状态）
- 状态流转（校验规则、执行转换）
- 改派（修改负责人）
- 日志查询

#### test_specs 模块

测试需求与测试用例管理模块。

**职责**：
- 测试需求 `TestRequirementDoc` CRUD
- 测试用例 `TestCaseDoc` CRUD
- 自动化测试用例 `AutomationTestCaseDoc` 管理

#### execution 模块

测试执行编排模块，采用"平台主导串行 Case 执行"模型。

**设计**：
- 任务可包含多条 Case
- 平台只下发当前 1 条 Case
- 外部执行框架只执行当前 Case 并回报结果
- Case 终态后平台自动推进下一条
- 最后一条 Case 完成后自动收口任务

**核心文档**：
- `ExecutionTaskDoc` - 任务级快照
- `ExecutionTaskCaseDoc` - 单条 Case 执行明细
- `ExecutionTaskRunDoc` - 任务运行记录
- `ExecutionTaskRunCaseDoc` - Case 运行记录
- `ExecutionEventDoc` - 执行事件

#### assets 模块

资产管理模块。

**职责**：
- 组件库管理
- DUT（Device Under Test）资产
- 测试计划与部件关联

#### auth 模块

RBAC 权限模块。

**职责**：
- 用户、角色、权限 CRUD
- 用户角色绑定
- 角色权限绑定
- 导航页面权限控制

### 4.3 配置驱动工作流

工作流规则定义在 `app/configs/*.json` 文件中，运行时初始化到 MongoDB：

```json
{
  "work_types": [["REQUIREMENT", "需求"]],
  "workflow_configs": {
    "REQUIREMENT": [
      {
        "from_state": "DRAFT",
        "action": "SUBMIT",
        "to_state": "PENDING_REVIEW",
        "target_owner_strategy": "TO_SPECIFIC_USER",
        "required_fields": ["target_owner_id", "priority"]
      }
    ]
  }
}
```

**Owner Strategy**：

| 策略 | 说明 |
|------|------|
| `KEEP` | 保持当前负责人 |
| `TO_CREATOR` | 转交给创建者 |
| `TO_SPECIFIC_USER` | 使用 `target_owner_id` |

**新增工作流类型**：
1. 创建 `app/configs/<type>.json`
2. 运行 `python init_mongodb.py` 初始化到 MongoDB

### 4.4 启动流程

1. 连接 MongoDB
2. 初始化 Beanie 文档模型
3. 校验 workflow 配置一致性
4. 初始化应用级基础设施（Kafka 等）
5. 注册 API 路由和异常处理器

### 4.5 数据约束

**软删除**：
- 所有业务数据使用 `is_deleted` 字段
- 查询时必须显式过滤 `is_deleted == False`

**索引**：
- 索引定义在文档模型中
- 不在运行时代码中创建索引

---

## 5. 前端架构

### 5.1 单文件组件架构

前端采用单文件架构，主要逻辑集中在 `src/App.tsx`：

```tsx
// 视图状态管理
const [currentPage, setCurrentPage] = useState<'login' | 'testCases' | 'agents'>('login')
```

### 5.2 视图类型

| 视图 | 说明 |
|------|------|
| `login` | JWT 认证登录 |
| `testCases` | 测试用例管理 |
| `agents` | 执行代理管理 |

### 5.3 API 层

位置：`src/services/api.ts`

- 使用 Fetch API
- JWT Bearer Token 认证
- Token 存储在 localStorage (`jwt_token`)
- 基础 URL: `VITE_API_BASE_URL` 环境变量

---

## 6. 数据库设计

### 6.1 系统配置文档

| 集合 | 说明 |
|------|------|
| `sys_work_types` | 业务类型定义 |
| `sys_workflow_states` | 工作流状态 |
| `sys_workflow_configs` | 状态转换规则 |

### 6.2 业务文档

| 集合 | 说明 |
|------|------|
| `bus_work_items` | 业务事项 |
| `bus_flow_logs` | 流转日志 |
| `test_requirements` | 测试需求 |
| `test_cases` | 测试用例 |
| `automation_test_cases` | 自动化测试用例 |
| `execution_tasks` | 执行任务 |
| `execution_task_cases` | 任务内 Case |
| `execution_task_runs` | 任务运行记录 |
| `execution_task_run_cases` | Case 运行记录 |
| `execution_events` | 执行事件 |
| `users` | 用户 |
| `roles` | 角色 |
| `permissions` | 权限 |
| `navigation_pages` | 导航页面 |

---

## 7. API 设计

### 7.1 路由前缀

所有 API 统一以 `/api/v1` 为前缀。

| 路径 | 模块 |
|------|------|
| `/api/v1/work-items` | workflow |
| `/api/v1/requirements` | 测试需求 |
| `/api/v1/test-cases` | 测试用例 |
| `/api/v1/automation-test-cases` | 自动化测试用例 |
| `/api/v1/execution` | 执行编排 |
| `/api/v1/assets/components` | 组件库 |
| `/api/v1/assets/duts` | DUT 资产 |
| `/api/v1/auth/*` | RBAC |

### 7.2 统一响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

---

## 8. 环境配置

### 8.1 后端配置

位置：`app/shared/db/config.py` + `.env`

| 配置 | 说明 |
|------|------|
| `MONGO_URI` | MongoDB 连接地址 |
| `MONGO_DB_NAME` | 数据库名 |
| `CORS_ORIGINS` | CORS 白名单 |
| Kafka 配置 | 消息队列配置 |
| JWT 配置 | 认证配置 |

### 8.2 前端配置

位置：`.env`

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 9. 开发规范

### 9.1 代码规范

**Python**：
- 最大行长度：110
- 最大复杂度：12
- 使用 flake8 检查

**TypeScript**：
- 使用 ESLint 检查

### 9.2 测试规范

- 单元测试：`tests/unit/`
- 集成测试：`tests/integration/`
- 使用 pytest fixtures
- 使用 fakes 进行 mock

### 9.3 Git 提交规范

提交信息格式：
```
<type>(<scope>): <subject>

<body>
```

Type 类型：
- `feat`: 新功能
- `fix`: 修复
- `refactor`: 重构
- `docs`: 文档
- `test`: 测试

---

## 10. 快速开始

### 10.1 后端启动

```bash
cd backend
python init_mongodb.py              # 初始化工作流配置
python scripts/init_rbac.py         # 初始化 RBAC
python scripts/create_user.py       # 创建管理员
python -m app.main                  # 启动服务 (port 8000)
```

### 10.2 前端启动

```bash
cd frontend
npm install
npm run dev                         # 启动开发服务器 (port 5173)
```

---

## 11. 附录

### 11.1 常用命令

```bash
# 后端测试
cd backend
pytest                              # 全量测试
pytest tests/unit/workflow/         # 指定模块
pytest -v --cov=app                 # 带覆盖率

# 代码检查
cd backend
flake8                              # Python 代码检查
cd frontend
npm run lint                        # TypeScript 检查

# 构建
cd frontend
npm run build                       # 生产构建
```

### 11.2 文档索引

- [后端 README](/Users/libiao/Desktop/github/dmlv4/backend/README.md)
- [执行模块 README](/Users/libiao/Desktop/github/dmlv4/backend/app/modules/execution/README.md)
- [前端 CLAUDE.md](/Users/libiao/Desktop/github/dmlv4/frontend/CLAUDE.md)