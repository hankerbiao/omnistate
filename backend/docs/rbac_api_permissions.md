# 接口权限速查（RBAC）

更新时间：2026-02-28

主设计文档请参考：`docs/authorization_design.md`

## 1. 权限码

- `work_items:read` / `work_items:write` / `work_items:transition`
- `assets:read` / `assets:write`
- `requirements:read` / `requirements:write`
- `test_cases:read` / `test_cases:write`
- `menu:read` / `menu:write`
- `users:read` / `users:write`
- `roles:read` / `roles:write`
- `permissions:read` / `permissions:write`

## 2. 各模块映射

### 2.1 Workflow（`/api/v1/work-items`）

- `work_items:read`：`GET /types /states /configs / /sorted /search /{item_id} /{item_id}/test-cases /{item_id}/requirement /{item_id}/logs /logs/batch /{item_id}/transitions`
- `work_items:write`：`POST /`、`DELETE /{item_id}`、`POST /{item_id}/reassign`
- `work_items:transition`：`POST /{item_id}/transition`

### 2.2 Assets（`/api/v1/assets`）

- `assets:read`：`GET /components`、`GET /components/{part_number}`、`GET /duts`、`GET /duts/{asset_id}`、`GET /plan-components`
- `assets:write`：`POST|PUT|DELETE /components*`、`POST|PUT|DELETE /duts*`、`POST|DELETE /plan-components`

### 2.3 Requirements（`/api/v1/requirements`）

- `requirements:read`：`GET /`、`GET /{req_id}`
- `requirements:write`：`POST /`、`PUT /{req_id}`、`DELETE /{req_id}`

### 2.4 Test Cases（`/api/v1/test-cases`）

- `test_cases:read`：`GET /`、`GET /{case_id}`
- `test_cases:write`：`POST /`、`PUT /{case_id}`、`DELETE /{case_id}`

### 2.5 Menu（`/api/v1/menus`）

- `menu:read`：`GET /`、`GET /{menu_id}`
- `menu:write`：`POST /`、`PUT /{menu_id}`、`DELETE /{menu_id}`
- 仅登录：`GET /me`

### 2.6 Auth（`/api/v1/auth`）

- `users:read`：`GET /users`、`GET /users/{user_id}`
- `users:write`：`POST /users`、`PUT /users/{user_id}`、`PATCH /users/{user_id}/roles`、`PATCH /users/{user_id}/password`
- `roles:read`：`GET /roles`、`GET /roles/{role_id}`
- `roles:write`：`POST /roles`、`PUT /roles/{role_id}`、`PATCH /roles/{role_id}/permissions`
- `permissions:read`：`GET /permissions`、`GET /permissions/{perm_id}`
- `permissions:write`：`POST /permissions`、`PUT /permissions/{perm_id}`
- 公开：`POST /login`
- 仅登录：`POST /users/me/password`、`GET /users/me/permissions`

## 3. 错误语义（实现现状）

- 未认证：`401`
- 已认证但权限不足：`403`

统一返回结构由 `APIResponse` envelope 包装。
