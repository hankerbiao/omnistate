# Workflow HTTP API

基础路径：`/api/v1/work-items`（`app/shared/api/main.py` 挂载）。

统一响应：`{"code": 0, "message": "ok", "data": ...}`。  
错误时 HTTP 状态码与 `code` 一致，`detail` 为错误说明。

## 权限一览

| 权限码 | 用途 |
|--------|------|
| `work_items:read` | 查询、目录、日志、可用流转 |
| `work_items:write` | 创建、改派、删除 |
| `work_items:transition` | 执行状态流转 |

鉴权：JWT + RBAC（`require_permission`）。

## 目录接口（`routes_catalog.py`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/types` | 事项类型列表 |
| GET | `/states` | 全局状态列表（含 `is_end`） |
| GET | `/configs?type_code=` | 指定类型的全部流转配置；无配置时 404 |

## 事项 CRUD 与查询（`routes_items.py`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/` | write | 创建事项，201 |
| GET | `/` | read | 列表，支持 `type_code`、`state`、`owner_id`、`creator_id`、`limit`、`offset` |
| GET | `/sorted` | read | 可排序列表，`order_by`=created_at/updated_at/title，`direction`=asc/desc |
| GET | `/search` | read | 关键词搜索（≥2 字符），同上筛选参数 |
| GET | `/{item_id}` | read | 详情 |

### POST `/` 请求体（`CreateWorkItemRequest`）

| 字段 | 必填 | 说明 |
|------|------|------|
| `type_code` | 是 | 如 `REQUIREMENT`、`TEST_CASE` |
| `title` | 是 | 同类型未删除标题唯一 |
| `content` | 是 | 描述 |
| `parent_item_id` | 否 | 父事项 ID（用例挂需求） |

成功返回 `WorkItemResponse`（含 `item_id`、`current_state=DRAFT` 等）。

列表筛选注意：`owner_id` 与 `creator_id` 同时传入时为 **OR** 语义。

## 流转与审计（`routes_transitions.py`）

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/{item_id}/transition` | transition | 状态流转 |
| POST | `/{item_id}/reassign` | write | 改派，`target_owner_id` Query 必填 |
| DELETE | `/{item_id}` | write | 软删除 |
| GET | `/{item_id}/logs` | read | 流转历史，`limit` 默认 50 |
| GET | `/logs/batch` | read | 批量日志，`item_ids` 逗号分隔 |
| GET | `/{item_id}/transitions` | read | 当前用户可用动作 |

### POST `/{item_id}/transition`

请求体（`TransitionRequest`）：

| 字段 | 说明 |
|------|------|
| `action` | 与配置表 `action` 一致 |
| `form_data` | 对象，须包含配置要求的键 |

成功 `data`（`TransitionResponse`）示例字段：

- `work_item_id`、`from_state`、`to_state`、`action`
- `new_owner_id`
- `work_item`：更新后完整事项

### POST `/{item_id}/reassign`

Query：

- `target_owner_id`（必填）
- `remark`（可选）

不改变 `current_state`，写 `REASSIGN` 日志。

## 层级关系（`routes_relations.py`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/{item_id}/test-cases` | 需求下 `TEST_CASE` 子事项列表；`item_id` 须为 REQUIREMENT |
| GET | `/{item_id}/requirement` | 用例所属需求；无用例父级时 `data` 可为 `null` |

## 错误码

| HTTP | 场景 |
|------|------|
| 400 | 参数错误、非法流转、缺字段、重复标题、批量 logs 非法 ID |
| 403 | 流转/改派/删除权限不足 |
| 404 | 事项或类型配置不存在 |
| 500 | 事务不可用等运行时错误 |

## 与 test_specs 的关系

- 需求/用例的**推荐创建路径**是 `test_specs` API（内部事务双写 workflow + 投影）
- 直接 `POST /work-items` 仅创建 workflow 事项，**不会**自动创建 `TestRequirementDoc` / `TestCaseDoc`
- 经 test_specs 注册的 `WorkflowCommandService` 删除时会触发投影 Hook；纯 workflow 删除无投影副作用

完整业务字段（DDR5、步骤等）见 test_specs 文档与 `docs/后端接口说明.md`。

## 相关文档

- [状态与流转](./state-and-flow.md) — `form_data` 与 `properties`
- [架构与设计](./architecture.md) — 调用链
