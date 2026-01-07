# 配置驱动工作流后端（MongoDB 版本）

基于 **FastAPI + MongoDB (PyMongo Async + Beanie)** 的通用工作流后台服务，支持：

- 通过 JSON 配置驱动工作流类型、状态与流转规则，无需改动代码即可新增业务流程
- 提供统一的事项 CRUD、状态流转、改派、流转日志查询等接口
- 适合作为「需求管理」「测试用例管理」「缺陷管理」等系统的工作流核心后端

---

## 1. 技术栈与架构概览

- 编程语言：Python 3.12
- Web 框架：FastAPI
- 数据库：MongoDB
- Mongo 客户端：PyMongo Async (`AsyncMongoClient`)
- ODM：Beanie（基于 Pydantic 的异步 ODM）
- 配置管理：`pydantic-settings` + `.env`

整体架构：

- FastAPI 负责 HTTP 接入层和路由定义（见 [app/api](file:///Users/libiao/Desktop/github/test/backend/app/api)）
- `AsyncWorkflowService` 封装工作流业务规则（见 [workflow_service.py](file:///Users/libiao/Desktop/github/test/backend/app/services/workflow_service.py)）
- Beanie 文档模型封装 MongoDB 持久化（见 [models](file:///Users/libiao/Desktop/github/test/backend/app/models)）
- `configs/*.json` 配置文件驱动业务类型、状态及流转规则（见 [configs/README.md](file:///Users/libiao/Desktop/github/test/backend/app/configs/README.md)）

---

## 2. 目录结构

核心目录结构如下：

```text
backend/
├── app/
│   ├── api/                # HTTP 接口层
│   │   ├── main.py         # 路由聚合入口
│   │   ├── errors/         # 全局异常处理
│   │   ├── routes/
│   │   │   ├── health.py   # 健康检查接口
│   │   │   └── work_items.py  # 业务事项 CRUD & 流转接口
│   │   └── schemas/        # Pydantic 请求/响应模型
│   ├── configs/            # 工作流配置（JSON）及说明
│   │   ├── README.md
│   │   ├── global_config.json
│   │   ├── requirement.json
│   │   └── test_case.json
│   ├── core/
│   │   ├── logger.py       # 日志封装
│   │   └── mongo_client.py # 全局 AsyncMongoClient 管理
│   ├── db/
│   │   └── config.py       # Settings（Mongo 连接、CORS 等）
│   ├── models/             # Beanie 文档模型 + Pydantic 模型
│   ├── services/
│   │   ├── exceptions.py   # 业务异常定义
│   │   └── workflow_service.py  # 工作流领域服务
│   ├── init_mongodb.py     # 独立运行的 Mongo 初始化脚本
│   └── main.py             # FastAPI 应用入口（Mongo/Beanie 初始化）
└── README.md
```

---

## 3. 环境准备

### 3.1 必要环境

- Python：建议 3.10 或以上
- MongoDB：建议 4.4 或以上

### 3.2 Python 依赖（示例）

项目本身未固定提供 `requirements.txt`，可以根据实际需要创建，典型依赖包括：

```bash
pip install \
  fastapi \
  "uvicorn[standard]" \
  beanie \
  "pymongo[srv]" \
  pydantic \
  pydantic-settings
```

如果你有自己的依赖管理方式（如 Poetry、pip-tools），可以按上述包名自行整理。

---

## 4. 配置说明

配置入口位于 [app/db/config.py](file:///Users/libiao/Desktop/github/test/backend/app/db/config.py#L1-L18)，通过 Pydantic Settings 从环境变量 / `.env` 读取：

```python
class Settings(BaseSettings):
    # MongoDB 配置
    MONGO_URI: str = "mongodb://10.17.154.252:27018"
    MONGO_DB_NAME: str = "workflow_db"

    # CORS 配置
    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

推荐在项目根目录创建 `.env` 文件覆盖默认值，例如：

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=workflow_db
CORS_ORIGINS=["http://localhost:3000"]
```

> 提示：`DATABASE_URL`（PostgreSQL）字段已保留但当前实现中未使用，可忽略。

更多关于 JSON 配置文件的字段含义与扩展方法，请参考：
[configs/README.md](file:///Users/libiao/Desktop/github/test/backend/app/configs/README.md#L1-L79)。

---

## 5. 数据库初始化（导入配置驱动工作流）

初始化脚本见 [init_mongodb.py](file:///Users/libiao/Desktop/github/test/backend/app/init_mongodb.py#L1-L148)，主要功能：

- 连接 MongoDB 并初始化 Beanie
- 扫描 `app/configs/` 目录下所有 `.json`
- 整合：
  - `work_types`：业务类型
  - `states`：全局状态（部分在代码中内置）
  - `workflow_configs`：状态流转规则
- 以「插入或更新（upsert）」方式写入以下集合：
  - `sys_work_types`
  - `sys_workflow_states`
  - `sys_workflow_configs`

### 5.1 执行初始化

在项目根目录下运行：

```bash
# 建议使用模块方式运行，确保 import 前缀正确
python -m app.init_mongodb
```

或：

```bash
python app/init_mongodb.py
```

看到类似日志（MongoDB 连接成功 / Beanie 初始化完成 / 基础数据初始化完成）即表示初始化成功。

---

## 6. 启动 FastAPI 服务

FastAPI 应用入口位于 [app/main.py](file:///Users/libiao/Desktop/github/test/backend/app/main.py#L1-L86)，其中：

- 使用 `AsyncMongoClient` 连接 MongoDB 并做 `ping` 健康检查
- 初始化 Beanie 并注册所有文档模型
- 注入全局 Mongo 客户端（供低层事务或原生操作使用）

### 6.1 开发模式启动

在项目根目录执行：

```bash
uvicorn app.main:app --reload
```

默认监听：`http://127.0.0.1:8000`

你也可以直接运行：

```bash
python -m app.main
```

### 6.2 健康检查

- 根路径健康检查：`GET /`
- API 健康路由（见 [health.py](file:///Users/libiao/Desktop/github/test/backend/app/api/routes/health.py#L1-L26)）：
  - `GET /health`       — 简单健康检查
  - `GET /health/ready` — 就绪检查
  - `GET /health/live`  — 存活检查

### 6.3 文档界面

FastAPI 自动提供 Swagger 文档：

- Swagger UI：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

---

## 7. 主要接口说明（业务事项 / 工作流）

所有业务接口均挂载在 `/api/v1` 前缀下，对应路由见：
[work_items.py](file:///Users/libiao/Desktop/github/test/backend/app/api/routes/work_items.py#L1-L319)。

### 7.1 工作流元数据

前缀：`/api/v1/work-items`

- `GET /api/v1/work-items/types`
  - 功能：获取所有事项类型（如 REQUIREMENT、TEST_CASE）
  - 返回：`List[WorkTypeResponse]`

- `GET /api/v1/work-items/states`
  - 功能：获取系统支持的所有状态（如 DRAFT、PENDING_AUDIT、DONE 等）
  - 返回：`List[WorkflowStateResponse]`

- `GET /api/v1/work-items/configs?type_code=REQUIREMENT`
  - 功能：获取指定事项类型的所有流转配置规则
  - 返回：`List[WorkflowConfigResponse]`
  - 若类型不存在：返回 404

### 7.2 事项 CRUD

- `POST /api/v1/work-items`
  - 功能：创建业务事项，初始状态通常为 `DRAFT`
  - 请求体：`CreateWorkItemRequest`
  - 返回：`WorkItemResponse`

- `GET /api/v1/work-items`
  - 功能：分页查询事项列表
  - 支持筛选：
    - `type_code`：按类型筛选
    - `state`：按当前状态筛选
    - `owner_id`：按当前处理人筛选
    - `creator_id`：按创建人筛选
  - 特别说明：同时传入 `owner_id` 和 `creator_id` 时为「或」逻辑

- `GET /api/v1/work-items/{item_id}`
  - 功能：获取单个事项详情

- `DELETE /api/v1/work-items/{item_id}`
  - 功能：删除事项及其流转日志
  - 当前实现为真实删除，实际业务中建议使用软删除（`is_deleted` 字段）

### 7.3 状态流转与改派

- `POST /api/v1/work-items/{item_id}/transition`
  - 功能：根据配置执行状态流转
  - 请求体：`TransitionRequest`
  - 业务规则：
    - 校验当前状态是否允许执行该 `action`
    - 校验必填字段 `required_fields`
    - 根据 `target_owner_strategy` 决定下一处理人
    - 记录流转日志

- `POST /api/v1/work-items/{item_id}/reassign`
  - 功能：改派任务给其他处理人（不改变状态）
  - 查询参数：
    - `operator_id`：操作人 ID
    - `target_owner_id`：目标处理人 ID

### 7.4 流转历史与可用操作

- `GET /api/v1/work-items/{item_id}/logs`
  - 功能：查询指定事项的流转日志

- `GET /api/v1/work-items/logs/batch?item_ids=id1,id2,...`
  - 功能：批量查询多个事项的流转日志
  - 用途：看板场景下一次性拉取多个任务的状态时间线

- `GET /api/v1/work-items/{item_id}/transitions`
  - 功能：获取当前状态下可执行的所有下一步流转动作
  - 返回字段示例：
    - `item_id`
    - `current_state`
    - `available_transitions`: 某状态下允许的所有动作列表

---

## 8. 工作流配置驱动模型

配置文件位于 [app/configs](file:///Users/libiao/Desktop/github/test/backend/app/configs)，示例：

- `global_config.json`：全局状态等公共配置
- `requirement.json`：需求业务（REQUIREMENT）的工作流配置
- `test_case.json`：测试用例业务（TEST_CASE）的工作流配置

字段说明及新增业务流程示例详见：
[configs/README.md](file:///Users/libiao/Desktop/github/test/backend/app/configs/README.md#L1-L79)。

典型字段：

- `work_types`：业务类型列表，如 `["REQUIREMENT", "需求"]`
- `states`：状态枚举，如 `["DRAFT", "草稿"]`
- `workflow_configs`：状态迁移配置，定义 `from_state` / `action` / `to_state` / `target_owner_strategy` / `required_fields` 等

> 核心设计：**所有工作流规则只写在配置中；代码中的 `AsyncWorkflowService` 只负责执行这些规则。**

---

## 9. 核心代码模块速览

- [app/services/workflow_service.py](file:///Users/libiao/Desktop/github/test/backend/app/services/workflow_service.py)
  - `AsyncWorkflowService`：工作流领域服务
  - 负责：
    - 创建 / 查询 / 删除事项
    - 按配置执行状态流转
    - 记录流转日志
    - 计算可用下一步流转动作

- [app/models/system.py](file:///Users/libiao/Desktop/github/test/backend/app/models/system.py)
  - `SysWorkTypeDoc` / `SysWorkflowStateDoc` / `SysWorkflowConfigDoc`
  - 存储配置驱动的工作流元数据

- [app/models/business.py](file:///Users/libiao/Desktop/github/test/backend/app/models/business.py)
  - `BusWorkItemDoc`：业务事项文档
  - `BusFlowLogDoc`：流转日志文档
  - 对应 API 层的响应模型 `BusWorkItemModel` / `BusFlowLogModel`

- [app/core/mongo_client.py](file:///Users/libiao/Desktop/github/test/backend/app/core/mongo_client.py#L1-L24)
  - 全局 `AsyncMongoClient` 存取工具
  - 可用于需要底层事务或原生 Mongo 操作的场景

- [app/api/errors/handlers.py](file:///Users/libiao/Desktop/github/test/backend/app/api/errors/handlers.py)
  - 全局异常处理，将业务异常统一映射为结构化错误响应

---

## 10. 本地开发建议流程

1. 克隆代码并进入 `backend` 目录
2. 创建并激活虚拟环境（任选其一）
   - `python -m venv .venv && source .venv/bin/activate`（Linux/macOS）
3. 安装依赖（参考第 3 节）
4. 配置 `.env`（配置 Mongo 连接、CORS 等）
5. 确保本地 MongoDB 已启动
6. 运行数据库初始化脚本：
   - `python -m app.init_mongodb`
7. 启动 FastAPI 服务：
   - `uvicorn app.main:app --reload`
8. 打开 `http://127.0.0.1:8000/docs` 进行接口调试

---

## 11. 后续扩展方向（建议）

以下是一些自然的扩展点，便于将来继续演进本项目：

- 增加鉴权与多租户支持（在现有路由和 Service 上增加用户/租户隔离）
- 引入软删除策略（统一用 `is_deleted` 标记替代物理删除）
- 增加审计字段（如最后操作人、最后操作时间）
- 为核心业务逻辑补充单元测试和集成测试
- 提供前端 SDK 或 API 调用示例，方便业务系统集成

如你有具体的扩展需求，后续可以在此 README 的基础上继续细化。
