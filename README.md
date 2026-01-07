# Workflow State Machine（配置驱动任务流转引擎）

本项目是一个「**配置驱动的通用任务流转后端**」，前端只是为了演示和测试接口用的简单看板，不是正式业务系统。

- 后端：基于 **FastAPI + MongoDB + Beanie** 实现的工作流状态机服务
- 前端：基于 **React + TypeScript + Vite** 的简易看板，用来验证和体验任务流转能力（非生产业务实现）

---

## 1. 功能概览

后端提供一套通用的「工作流 / 任务流转」能力，支持：

- 通过 JSON 配置定义：
  - 任务类型（如需求、测试用例）
  - 状态枚举（草稿、待审核、已完成等）
  - 状态流转规则（从什么状态，经由什么动作，流转到什么状态）
  - 处理人策略（保持不变、回到创建人、指定用户）
- 提供统一的 API 接口：
  - 创建任务
  - 分页查询任务列表
  - 执行状态流转（含必填字段校验、处理人自动计算）
  - 改派处理人
  - 查询单个 / 批量任务的流转日志
  - 查询当前状态下可用的下一步动作

前端只是一个轻量级 UI：

- 模拟不同用户视角
- 快速创建任务、流转任务、查看日志
- 帮助验证后端的流转规则是否按预期工作

---

## 2. 目录结构

项目根目录结构示意：

```text
.
├── backend/                 # 工作流后端（核心）
│   └── app/
│       ├── api/             # HTTP 接口层（FastAPI 路由、请求/响应模型）
│       ├── configs/         # 工作流配置（JSON），定义类型/状态/流转规则
│       ├── core/            # 日志、Mongo 客户端等基础设施
│       ├── db/              # 配置加载（Mongo 连接等）
│       ├── models/          # Beanie 文档模型（系统配置 + 业务 + 枚举）
│       ├── services/        # 领域服务（工作流核心逻辑）
│       ├── init_mongodb.py  # 初始化 Mongo，导入工作流配置
│       └── main.py          # FastAPI 应用入口
│
├── frontend/                # 前端演示应用（仅用于测试与体验后端能力）
│   ├── src/
│   │   ├── components/      # 简单的任务列表、详情、创建弹窗等
│   │   ├── services/        # 调用后端 API 的封装
│   │   └── context/         # 当前用户上下文（模拟不同处理人）
│   └── README.md            # Vite 模板说明（保留原生文档）
│
├── requirements.txt         # 后端依赖（示例）
└── README.md                # 当前文档
```

更细的后端说明可参考：

- [backend/app/services/workflow.md](file:///Users/libiao/Desktop/github/test/backend/app/services/workflow.md)
- [backend/app/configs/README.md](file:///Users/libiao/Desktop/github/test/backend/app/configs/README.md)

---

## 3. 后端快速开始（核心部分）

> 以下步骤以本地开发为例，默认使用本机 MongoDB。

### 3.1 安装依赖

在项目根目录下，创建虚拟环境并安装依赖（任选其一）：

```bash
cd backend

python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate

pip install -r ../requirements.txt
```

### 3.2 配置数据库

后端配置位于：

- [backend/app/db/config.py](file:///Users/libiao/Desktop/github/test/backend/app/db/config.py)

可以在项目根目录创建 `.env` 文件覆盖默认配置，例如：

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=workflow_db
CORS_ORIGINS=["http://localhost:5173"]
```

### 3.3 初始化工作流配置到 Mongo

初始化脚本：

- [backend/app/init_mongodb.py](file:///Users/libiao/Desktop/github/test/backend/app/init_mongodb.py)

执行：

```bash
cd backend
python -m app.init_mongodb
```

脚本会：

- 初始化 Beanie 文档模型
- 扫描 `app/configs/*.json`
- 将工作流类型、状态、流转规则导入到对应集合（如 `sys_work_types`、`sys_workflow_states`、`sys_workflow_configs`）

### 3.4 启动 FastAPI 服务

```bash
cd backend
uvicorn app.main:app --reload
```

默认访问：

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

健康检查接口见：

- [backend/app/api/routes/health.py](file:///Users/libiao/Desktop/github/test/backend/app/api/routes/health.py)

---

## 4. 前端演示应用（仅用于测试）

前端代码位于 `frontend/`，是一个基于 Vite 模板搭建的简易 React + TS 应用。**它的目的仅是方便验证后端能力，不代表真实业务界面。**

主要特性：

- 任务列表（按当前用户过滤）
- 新建任务弹窗
- 任务详情弹窗（查看和触发流转）
- 用户切换（模拟不同处理人）

### 4.1 安装并启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址： http://127.0.0.1:5173

> 注意：前端的接口地址在 `frontend/src/services/api.ts` 中配置，如果你的后端服务地址或端口有变化，请同步修改。

---

## 5. 核心工作流设计概览

后端的工作流核心由 `AsyncWorkflowService` 实现，详见：

- [backend/app/services/workflow_service.py](file:///Users/libiao/Desktop/github/test/backend/app/services/workflow_service.py)
- [backend/app/services/workflow.md](file:///Users/libiao/Desktop/github/test/backend/app/services/workflow.md)

关键点：

- 任务状态、可执行动作、处理人策略全部由配置文件驱动
- 代码中只实现通用的「流转引擎」：
  - 校验事项存在性和当前状态
  - 按 `type_code + from_state + action` 匹配唯一配置
  - 校验配置中声明的必填字段
  - 按策略计算下一处理人
  - 落库更新任务状态和处理人
  - 写入流转日志

因此：

- **新增一种业务类型**（如缺陷 BUG）时，只需要新增一份 JSON 配置并执行初始化脚本，无需改动核心代码。
- 前端示例只是其中一种可能的展示方式，可以根据自己的系统自由对接。

---

## 6. 适用场景与不做的事情

适用场景：

- 需求管理、测试用例管理、缺陷管理等“任务/事项流转”类系统的工作流核心后端
- 想用配置快速试错、调整流程，而不希望频繁改动后端代码

不做的事情：

- 不包含复杂权限系统（如角色/组织架构等），只关注「谁来处理」这一维度
- 不提供真正的业务 UI，前端只是一个用来测试和演示的看板
- 不关心具体业务字段的含义，只通过配置的 `required_fields` 做通用校验

如果你要在生产环境中使用，可以在此基础上叠加：

- 鉴权 / 多租户
- 更丰富的审计字段
- 真实的业务前端
