# 权限管理接口权限说明

本文档说明 RBAC 模块与工作流模块当前已接入的接口权限规则，便于前端与测试对齐。

## 1. 权限码规范
权限码采用 `资源:动作` 形式：
- `work_items:read`
- `work_items:write`
- `work_items:transition`
- `users:write` / `roles:write` / `permissions:write`（建议扩展）

> 说明：`test_specs` 与 `assets` 相关权限尚未接入依赖，可在后续补充。

---

## 2. 工作流模块（已接入权限）
路径前缀：`/api/v1/work-items`

### 2.1 读取权限（work_items:read）
- `GET /api/v1/work-items`
- `GET /api/v1/work-items/sorted`
- `GET /api/v1/work-items/search`
- `GET /api/v1/work-items/{item_id}`
- `GET /api/v1/work-items/{item_id}/test-cases`
- `GET /api/v1/work-items/{item_id}/requirement`
- `GET /api/v1/work-items/{item_id}/logs`
- `GET /api/v1/work-items/logs/batch`
- `GET /api/v1/work-items/{item_id}/transitions`

### 2.2 写入权限（work_items:write）
- `POST /api/v1/work-items`
- `DELETE /api/v1/work-items/{item_id}`
- `POST /api/v1/work-items/{item_id}/reassign`

### 2.3 流转权限（work_items:transition）
- `POST /api/v1/work-items/{item_id}/transition`

---

## 3. RBAC 模块（建议接入权限）
路径前缀：`/api/v1/auth`

目前 RBAC 接口尚未强制绑定权限依赖，可按以下建议接入：

### 3.1 用户管理
- `POST /api/v1/auth/users` → `users:write`
- `PUT /api/v1/auth/users/{user_id}` → `users:write`
- `PATCH /api/v1/auth/users/{user_id}/roles` → `users:write`
- `GET /api/v1/auth/users` → `users:read`
- `GET /api/v1/auth/users/{user_id}` → `users:read`

### 3.2 角色管理
- `POST /api/v1/auth/roles` → `roles:write`
- `PUT /api/v1/auth/roles/{role_id}` → `roles:write`
- `PATCH /api/v1/auth/roles/{role_id}/permissions` → `roles:write`
- `GET /api/v1/auth/roles` → `roles:read`
- `GET /api/v1/auth/roles/{role_id}` → `roles:read`

### 3.3 权限管理
- `POST /api/v1/auth/permissions` → `permissions:write`
- `PUT /api/v1/auth/permissions/{perm_id}` → `permissions:write`
- `GET /api/v1/auth/permissions` → `permissions:read`
- `GET /api/v1/auth/permissions/{perm_id}` → `permissions:read`

---

## 4. 后续建议
- 对 `test_specs` 与 `assets` 模块补充权限依赖
- 在 API 返回中加入权限不足的标准化错误结构
- 对管理员操作统一绑定 `ADMIN` 角色或 `roles:write/users:write` 权限
