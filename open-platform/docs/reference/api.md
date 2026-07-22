# API 参考

开放平台后端暴露两类 API：

| 类型 | 前缀 | 鉴权方式 |
| --- | --- | --- |
| 开放 API | `/api/v1/open` | `Authorization: Bearer <API Key>` |
| 控制台 API | `/api/v1/open-platform` | `X-Console-Token` 或 `Authorization: Bearer <console_token>` |

## 响应格式

成功：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

失败：

```json
{
  "code": 403,
  "message": "Permission denied",
  "data": {
    "error": "PERMISSION_DENIED",
    "detail": "missing scope"
  }
}
```

## 已注册开放能力

| 能力 ID | 方法 | 路径 | Scope | Handler |
| --- | --- | --- | --- | --- |
| `cap_list_tasks` | GET | `/api/v1/open/execution/tasks/my` | `execution_tasks:read` | `proxy` |
| `cap_task_status` | GET | `/api/v1/open/execution/tasks/{task_id}/status` | `execution_tasks:read` | `proxy` |
| `cap_task_timeline` | GET | `/api/v1/open/execution/tasks/{task_id}/timeline` | `execution_tasks:read` | `proxy` |
| `cap_dispatch_task` | POST | `/api/v1/open/execution/tasks/dispatch` | `execution_tasks:write` | `proxy` |
| `cap_rerun_task` | POST | `/api/v1/open/execution/tasks/{task_id}/rerun` | `execution_tasks:write` | `proxy` |
| `cap_task_biz_logs` | GET | `/api/v1/open/execution/tasks/{task_id}/biz-logs` | `execution_tasks:read` | `proxy` |
| `cap_list_specs` | GET | `/api/v1/open/test-specs/cases` | `test_cases:read` | `proxy` |
| `cap_get_case` | GET | `/api/v1/open/test-specs/cases/{case_id}` | `test_cases:read` | `proxy` |
| `cap_case_change_logs` | GET | `/api/v1/open/test-specs/cases/{case_id}/change-logs` | `test_cases:read` | `proxy` |
| `cap_list_requirements` | GET | `/api/v1/open/test-specs/requirements` | `requirements:read` | `proxy` |
| `cap_get_requirement` | GET | `/api/v1/open/test-specs/requirements/{req_id}` | `requirements:read` | `proxy` |
| `cap_list_projects` | GET | `/api/v1/open/projects` | `projects:read` | `proxy` |
| `cap_get_project` | GET | `/api/v1/open/projects/{project_id}` | `projects:read` | `proxy` |
| `cap_project_stats` | GET | `/api/v1/open/projects/{project_id}/stats` | `projects:read` | `proxy` |
| `cap_project_blockers` | GET | `/api/v1/open/projects/{project_id}/blockers` | `projects:read` | `proxy` |
| `cap_project_activities` | GET | `/api/v1/open/projects/{project_id}/activities` | `projects:read` | `proxy` |
| `cap_report` | GET | `/api/v1/open/reports/{task_id}` | `execution_tasks:read` | `aggregate` |
| `cap_webhook` | POST | `/api/v1/open/webhooks` | `execution_tasks:write` | `local` |

## 开放 API 示例

### 查询我的测试任务

```bash
curl "http://127.0.0.1:8820/api/v1/open/execution/tasks/my?limit=5" \
  -H "Authorization: Bearer dml_test_demo_local"
```

### 查询任务状态

```bash
curl "http://127.0.0.1:8820/api/v1/open/execution/tasks/ET-2026-000128/status" \
  -H "Authorization: Bearer dml_test_demo_local"
```

### 查询任务时间线

```bash
curl "http://127.0.0.1:8820/api/v1/open/execution/tasks/ET-2026-000128/timeline?limit=100" \
  -H "Authorization: Bearer dml_test_demo_local"
```

## 控制台 API

控制台请求头：

```text
X-Console-Token: dev-console-token
X-Console-User-Id: user_admin
```

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/overview` | 概览统计 |
| POST | `/login` | 控制台登录 |
| GET | `/users` | 用户列表 |
| POST | `/users` | 创建用户 |
| GET | `/me/capabilities` | 当前用户已授权能力和接口参数详情 |
| PUT | `/users/{id}/permissions` | 更新用户能力授权 |
| PUT | `/users/{id}/quota` | 更新用户配额 |
| GET | `/keys` | API Key 列表 |
| POST | `/keys` | 创建 API Key |
| POST | `/keys/{id}/revoke` | 撤销 API Key |
| DELETE | `/keys/{id}` | 删除 API Key |
| GET | `/capabilities` | 能力目录 |
| GET | `/logs` | 调用日志 |
| POST | `/debug` | 在线调试 |

### 当前用户能力

```bash
curl http://127.0.0.1:8820/api/v1/open-platform/me/capabilities \
  -H "X-Console-Token: dev-console-token" \
  -H "X-Console-User-Id: user_developer"
```

响应中的 `capabilities` 会按当前用户权限过滤。管理员返回全部能力，普通用户只返回已授权能力。每个能力包含 `method`、`path`、`scope`、`summary`、`description`、`params` 和 `sampleResponse`。

## 内置本地密钥

| Key ID | 明文 Token | 状态 |
| --- | --- | --- |
| `key_01` | `dml_live_demo_ci` | active |
| `key_02` | `dml_live_demo_dashboard` | active |
| `key_03` | `dml_test_demo_local` | active |
| `key_04` | `dml_live_demo_revoked` | revoked |
