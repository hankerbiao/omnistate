# Workflow API (MongoDB)

配置驱动的工作流状态机服务，基于 FastAPI + Beanie ODM + MongoDB。

## 快速开始

```bash
# 安装依赖
pip install fastapi beanie pymongo pydantic-settings uvicorn

# 初始化 MongoDB 数据（从 JSON 配置导入工作流规则）
cd backend && python init_mongodb.py

# 启动服务
cd backend && python -m app.main
```

服务启动后访问 http://localhost:8000

## 项目结构

```
backend/
├── app/
│   ├── main.py                      # FastAPI 应用入口
│   ├── init_mongodb.py              # MongoDB 初始化脚本
│   ├── configs/                     # 工作流配置文件
│   │   ├── global_config.json
│   │   ├── requirement.json         # 需求工作流配置
│   │   └── test_case.json           # 测试用例工作流配置
│   ├── shared/                      # 共享模块
│   │   ├── core/                    # 核心工具
│   │   │   ├── logger.py            # 日志工具
│   │   │   └── mongo_client.py      # MongoDB 客户端
│   │   ├── db/                      # 数据库配置
│   │   │   └── config.py            # Settings 配置
│   │   ├── api/                     # API 基础设施
│   │   │   ├── main.py              # 路由汇总
│   │   │   ├── schemas/             # 通用 Schema
│   │   │   ├── errors/              # 错误处理
│   │   │   └── routes/              # 健康检查等通用路由
│   │   └── service/                 # 通用服务
│   │       └── base.py
│   └── modules/                     # 业务模块
│       ├── workflow/                # 工作流核心模块
│       ├── assets/                  # 资产管理模块
│       ├── test_specs/              # 测试需求与用例模块
│       └── auth/                    # RBAC 权限模块
└── tests/                           # 测试代码
```

## 核心概念

### 1. 工作流配置驱动

工作流规则通过 JSON 文件定义，存储在 `app/configs/` 目录：

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

**Owner Strategy**:
- `KEEP` - 保持当前处理人
- `TO_CREATOR` - 转移给创建人
- `TO_SPECIFIC_USER` - 使用 `target_owner_id` 指定处理人

### 2. 数据模型

**系统配置文档**:
- `SysWorkTypeDoc` - 事项类型 (REQUIREMENT, TEST_CASE 等)
- `SysWorkflowStateDoc` - 流程状态 (含 `is_end` 标记终点状态)
- `SysWorkflowConfigDoc` - 状态流转规则

**业务文档**:
- `BusWorkItemDoc` - 业务事项（含状态、当前处理人、创建人）
- `BusFlowLogDoc` - 流转日志（审计跟踪）

### 3. 领域服务

`AsyncWorkflowService` 是核心业务服务，提供：
- `create_item()` - 创建事项（初始状态为 DRAFT）
- `handle_transition()` - 执行状态流转
- `list_items()` - 查询事项列表（支持多条件筛选）
- `get_item_with_transitions()` - 获取事项及可用流转动作

## API 端点

所有 API 统一返回格式：
```json
{
  "code": 0,
  "message": "ok",
  "data": {...}
}
```

### 工作流模块 `/api/v1/work-items`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/types` | 获取事项类型列表 |
| GET | `/states` | 获取流程状态列表 |
| GET | `/configs?type_code=xxx` | 获取指定类型的流转配置 |
| POST | `` | 创建业务事项 |
| GET | `` | 查询事项列表 |
| GET | `/sorted` | 获取排序后的事项列表 |
| GET | `/search` | 模糊搜索事项 |
| GET | `/{item_id}` | 获取事项详情 |
| DELETE | `/{item_id}` | 逻辑删除事项 |
| POST | `/{item_id}/transition` | 执行状态流转 |
| POST | `/{item_id}/reassign` | 改派任务 |
| GET | `/{item_id}/logs` | 获取流转历史 |
| GET | `/{item_id}/transitions` | 获取可用流转动作 |
| GET | `/{item_id}/test-cases` | 获取需求下的测试用例 |
| GET | `/{item_id}/requirement` | 获取测试用例所属需求 |

### 资产管理模块 `/api/v1/assets`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/components` | 创建部件字典项 |
| GET | `/components/{part_number}` | 获取部件详情 |
| GET | `/components` | 查询部件列表 |
| PUT | `/components/{part_number}` | 更新部件信息 |
| DELETE | `/components/{part_number}` | 删除部件 |
| POST | `/duts` | 创建设备资产 |
| GET | `/duts/{asset_id}` | 获取设备资产详情 |
| GET | `/duts` | 查询设备资产列表 |
| PUT | `/duts/{asset_id}` | 更新设备资产 |
| DELETE | `/duts/{asset_id}` | 删除设备资产 |
| POST | `/plan-components` | 创建测试计划关联部件 |
| GET | `/plan-components` | 查询测试计划关联部件 |
| DELETE | `/plan-components` | 删除测试计划关联部件 |

### 测试需求模块 `/api/v1/requirements`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `` | 创建测试需求 |
| GET | `/{req_id}` | 获取测试需求详情 |
| GET | `` | 查询测试需求列表 |
| PUT | `/{req_id}` | 更新测试需求 |
| DELETE | `/{req_id}` | 删除测试需求 |

### 测试用例模块 `/api/v1/test-cases`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `` | 创建测试用例 |
| GET | `/{case_id}` | 获取测试用例详情 |
| GET | `` | 查询测试用例列表 |
| PUT | `/{case_id}` | 更新测试用例 |
| DELETE | `/{case_id}` | 删除测试用例 |

### RBAC 权限模块 `/api/v1/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/users` | 创建用户 |
| GET | `/users/{user_id}` | 获取用户详情 |
| GET | `/users` | 查询用户列表 |
| PUT | `/users/{user_id}` | 更新用户信息 |
| PATCH | `/users/{user_id}/roles` | 更新用户角色 |
| POST | `/roles` | 创建角色 |
| GET | `/roles/{role_id}` | 获取角色详情 |
| GET | `/roles` | 查询角色列表 |
| PUT | `/roles/{role_id}` | 更新角色信息 |
| PATCH | `/roles/{role_id}/permissions` | 更新角色权限 |
| POST | `/permissions` | 创建权限 |
| GET | `/permissions/{perm_id}` | 获取权限详情 |
| GET | `/permissions` | 查询权限列表 |
| PUT | `/permissions/{perm_id}` | 更新权限 |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 服务健康检查 |

## 配置说明

### 数据库配置

在 `app/shared/db/config.py` 中配置：

```python
class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://10.17.154.252:27018"
    MONGO_DB_NAME: str = "workflow_db"
    CORS_ORIGINS: list[str] = ["*"]
```

可通过 `.env` 文件覆盖默认配置。

### 工作流规则配置

在 `app/configs/` 目录下添加 JSON 配置文件，然后运行：

```bash
python init_mongodb.py
```

这会将 JSON 配置导入 MongoDB。

## 模块详解

### Workflow 模块

工作流核心模块，负责：
- 事项的创建、查询、逻辑删除
- 状态流转的校验与执行
- 流转历史的记录与查询
- 父子事项关系的维护（需求-测试用例）

代码组织：
- `repository/models/` - MongoDB 文档模型
- `domain/` - 领域规则（字段校验、Owner 策略计算）
- `service/` - 业务服务
- `api/` - HTTP 路由
- `schemas/` - 请求/响应 Schema

### Assets 模块

资产管理模块，管理：
- Component Library（部件字典）
- DUT（被测设备资产）
- Test Plan Components（测试计划关联部件）

### Test Specs 模块

测试需求与测试用例管理模块，与 Workflow 模块联动。

### Auth 模块

RBAC 权限模块，提供用户、角色、权限的 CRUD 管理。

## 开发指南

### 添加新的业务模块

1. 在 `app/modules/` 下创建模块目录
2. 参照现有模块结构创建：
   - `repository/models/` - 文档模型
   - `schemas/` - Schema
   - `service/` - 业务服务
   - `api/routes.py` - 路由
3. 在 `app/shared/api/main.py` 中注册路由
4. 在 `app/main.py` 的 `document_models` 列表中注册文档模型

### 添加新的工作流类型

1. 在 `app/configs/` 创建新的 JSON 配置文件
2. 定义 `work_types` 和 `workflow_configs`
3. 运行 `python init_mongodb.py` 初始化数据
4. 前端即可使用新的事项类型

## 测试

```bash
# 运行所有测试
cd backend && pytest

# 运行特定测试
cd backend && pytest tests/unit/workflow/
```
