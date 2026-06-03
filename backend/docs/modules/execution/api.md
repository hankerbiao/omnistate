# Execution HTTP API

基础路径：`/api/v1/execution`（由 `app/shared/api/main.py` 挂载）。

统一响应格式：`{"code": 0, "message": "ok", "data": ...}`。  
错误时 `code` 为 HTTP 状态码，`data` 含 `error` / `detail`。

响应头（全站中间件）：`X-Request-ID`、`X-Trace-ID`，排障时与日志 `request_id` 关联。

## 任务管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/tasks/dispatch` | `execution_tasks:write` | 创建任务；立即执行则下发第一条 case |
| POST | `/tasks/{task_id}/rerun` | `execution_tasks:write` | 基于快照创建新任务（新 `task_id`） |
| DELETE | `/tasks/{task_id}` | `execution_tasks:write` | 逻辑删除 |
| POST | `/tasks/{task_id}/cancel` | `execution_tasks:write` | 取消未触发的定时任务 |
| POST | `/tasks/{task_id}/stop` | `execution_tasks:write` | 当前 case 结束后停止 |

## 任务查询

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/tasks` | `execution_tasks:read` | 任务列表（含 cases 当前态） |
| GET | `/tasks/{task_id}/status` | `execution_tasks:read` | 任务详情（含 `request_payload`、下发错误等） |
| GET | `/tasks/{task_id}/biz-logs` | `execution_tasks:read` | 平台业务轨迹（`limit` 默认 200） |

## POST /tasks/dispatch 请求体（摘要）

Pydantic 模型：`DispatchTaskRequest`（`schemas/execution.py`）

| 字段 | 必填 | 说明 |
|------|------|------|
| `cases` | 是 | `auto_case_id` + `config` + `parameters`，按数组顺序串行执行 |
| `dispatch_channel` | 否 | 已废弃，固定 RABBITMQ，传入值会被忽略 |
| `agent_id` | 否 | 执行端标识（可选，写入任务文档） |
| `schedule_type` | 否 | `IMMEDIATE`（默认）或 `SCHEDULED` |
| `planned_at` | 定时必填 | UTC |
| `framework` | 否 | 默认 pytest |
| `category`、`project_tag`、`repo_url`、`branch` | 否 | 任务元数据 |
| `pytest_options`、`timeout` | 否 | 执行参数 |

**注意**：脚本路径、`case_id` 由后端根据 `auto_case_id` 查 `automation_test_cases` 解析，前端勿透传脚本字段。

## 成功创建响应（摘要）

`DispatchTaskResponse` / `data` 中常见字段：

- `task_id`
- `dispatch_status`、`overall_status`
- `case_count`
- `current_case_id`、`current_case_index`

## 错误码

| HTTP | 场景 |
|------|------|
| 400 | 参数校验、去重冲突、身份校验 |
| 404 | `auto_case_id` 或任务不存在 |
| 403 | 无 RBAC 权限 |
| 500 | 未预期异常（日志含 `request_id`） |

更完整的请求示例与下发 payload 见仓库根目录 [测试执行编排](../../../../docs/guide/test-execution.md)。
