# 授权设计（Authorization Design）

更新时间：2026-02-28

## 1. 设计目标

- 统一全项目 API 的鉴权与授权行为。
- 权限粒度明确到 `资源:动作`，避免“登录即全能”。
- 业务路由默认受保护，未授权请求可预测、可测试。
- 设计与代码实现保持可追踪映射。

## 2. 适用范围

- 生效模块：
  - `workflow`
  - `assets`
  - `test_specs`（`requirements`、`test_cases`）
  - `execution`
  - `auth`（用户/角色/权限管理）
- 非业务接口：
  - 健康检查接口（`/health`）不要求授权。

## 3. 权限模型

采用标准 RBAC（三层）：

- `User`：登录主体，绑定多个角色（`role_ids`）。
- `Role`：权限集合，绑定多个权限（`permission_ids`）。
- `Permission`：最小授权单元，编码为 `资源:动作`。

权限编码规范示例：

- `work_items:read`
- `work_items:write`
- `work_items:transition`
- `assets:read`
- `assets:write`
- `requirements:read`
- `requirements:write`
- `test_cases:read`
- `test_cases:write`
- `execution_tasks:read`
- `execution_tasks:write`
- `execution_agents:read`
- `users:read` / `users:write`
- `roles:read` / `roles:write`
- `permissions:read` / `permissions:write`
- `navigation:read` / `navigation:write`

## 4. 授权链路

实现文件：`app/shared/auth/jwt_auth.py`

请求进入 API 后，链路如下：

1. `HTTPBearer(auto_error=True)` 解析请求头。
2. 无 token 或格式错误：返回 `401`。
3. `decode_token()` 校验签名、过期时间、`iss`、`aud`。
4. `get_current_user()` 校验用户存在且 `status == ACTIVE`。
5. `require_permission(code)` 查询用户有效权限并判断包含关系。
6. 无权限：返回 `403`（`permission denied`）。

## 5. 错误语义（当前实现）

统一错误封装由 `app/shared/api/errors/handlers.py` 提供：

- 未认证：`401`，`detail` 常见值为 `Not authenticated` 或 `invalid token`。
- 已认证但权限不足：`403`，`detail=permission denied`。
- 响应结构统一为 `APIResponse` envelope。

## 6. 路由权限矩阵（当前生效）

说明：本章节是后端接口权限矩阵的唯一维护入口。

### 6.1 Workflow（`/api/v1/work-items`）

- `work_items:read`
  - `GET /types`
  - `GET /states`
  - `GET /configs`
  - `GET /`
  - `GET /sorted`
  - `GET /search`
  - `GET /{item_id}`
  - `GET /{item_id}/test-cases`
  - `GET /{item_id}/requirement`
  - `GET /{item_id}/logs`
  - `GET /logs/batch`
  - `GET /{item_id}/transitions`
- `work_items:write`
  - `POST /`
  - `DELETE /{item_id}`
  - `POST /{item_id}/reassign`
- `work_items:transition`
  - `POST /{item_id}/transition`

### 6.2 Assets（`/api/v1/assets`）

- `assets:read`
  - `GET /components`
  - `GET /components/{part_number}`
  - `GET /duts`
  - `GET /duts/{asset_id}`
  - `GET /plan-components`
- `assets:write`
  - `POST /components`
  - `PUT /components/{part_number}`
  - `DELETE /components/{part_number}`
  - `POST /duts`
  - `PUT /duts/{asset_id}`
  - `DELETE /duts/{asset_id}`
  - `POST /plan-components`
  - `DELETE /plan-components`

### 6.3 Requirements（`/api/v1/requirements`）

- `requirements:read`
  - `GET /`
  - `GET /{req_id}`
- `requirements:write`
  - `POST /`
  - `PUT /{req_id}`
  - `DELETE /{req_id}`

### 6.4 Test Cases（`/api/v1/test-cases`）

- `test_cases:read`
  - `GET /`
  - `GET /{case_id}`
- `test_cases:write`
  - `POST /`
  - `PUT /{case_id}`
  - `DELETE /{case_id}`

### 6.5 Auth（`/api/v1/auth`）

- `users:read`
  - `GET /users`
  - `GET /users/{user_id}`
- `users:write`
  - `POST /users`
  - `PUT /users/{user_id}`
- `roles:read`
  - `GET /roles`
  - `GET /roles/{role_id}`
- `roles:write`
  - `POST /roles`
  - `PUT /roles/{role_id}`
- `permissions:read`
  - `GET /permissions`
  - `GET /permissions/{perm_id}`
- `permissions:write`
  - `POST /permissions`
  - `PUT /permissions/{perm_id}`
- 免权限（公开）
  - `POST /login`
- 仅登录（不要求显式权限）
  - `POST /users/me/password`
  - `GET /users/me/permissions`
- 需登录且要求导航读取权限
  - `GET /users/me/navigation`（`navigation:read`）
- 管理员专用（`require_admin_user`）
  - `GET /admin/navigation/pages`
  - `GET /admin/navigation/pages/{view}`
  - `POST /admin/navigation/pages`
  - `PUT /admin/navigation/pages/{view}`
  - `DELETE /admin/navigation/pages/{view}`
  - `GET /admin/users/{user_id}/navigation`
  - `PUT /admin/users/{user_id}/navigation`
  - `PATCH /users/{user_id}/roles`
  - `PATCH /users/{user_id}/password`
  - `PATCH /roles/{role_id}/permissions`

### 6.6 Execution（`/api/v1/execution`）

- `execution_tasks:write`
  - `POST /tasks/dispatch`
  - `POST /tasks/{task_id}/consume-ack`
  - `POST /tasks/{task_id}/cancel`
  - `PUT /tasks/{task_id}/schedule`
  - `POST /tasks/{task_id}/retry`
- `execution_tasks:read`
  - `GET /tasks`
  - `GET /tasks/{task_id}/status`
- `execution_agents:read`
  - `GET /agents`
  - `GET /agents/{agent_id}`
- 当前未挂显式 RBAC 依赖的代理/回传接口
  - `POST /agents/register`
  - `POST /agents/{agent_id}/heartbeat`
  - `POST /tasks/{task_id}/events`
  - `POST /tasks/{task_id}/cases/{case_id}/status`
  - `POST /tasks/{task_id}/complete`

## 7. 默认权限与角色初始化

初始化脚本：`scripts/init_rbac.py`

- 负责初始化默认权限码（`DEFAULT_PERMISSIONS`）。
- 负责初始化默认角色（`ADMIN`、`TPM`、`TESTER`、`AUTOMATION`）。
- `ADMIN` 默认包含全量权限。

## 8. 测试策略

权限行为由集成测试覆盖：

- `tests/integration/test_api_authorization.py`
  - 验证业务路由无 token 时返回 `401`
  - 验证已登录但无权限时返回 `403`
- `tests/integration/test_api_workflow.py`
  - 通过依赖覆盖注入权限上下文，保证业务测试不依赖真实 DB 鉴权查询

## 9. 维护约束

- 新增业务路由必须明确声明：
  - 公开接口（免登录）或
  - 仅登录接口（`get_current_user`）或
  - 显式权限接口（`require_permission`）
- PR 必须同步更新权限文档与权限测试。
- 权限码新增时，必须同步更新 `scripts/init_rbac.py`。
