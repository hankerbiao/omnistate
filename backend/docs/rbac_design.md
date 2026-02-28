# 用户与权限管理模块设计方案（RBAC）

更新时间：2026-02-28

## 1. 目标

- 支持按角色授予后端 API 权限。
- 保持权限码与业务模块一一对应，便于审计与排障。
- 支持管理员维护用户、角色、权限及导航访问能力。

## 2. 核心概念

- User（用户）：登录主体，包含 `role_ids`。
- Role（角色）：权限集合，包含 `permission_ids`。
- Permission（权限）：最小授权单元，编码为 `资源:动作`。

## 3. 权限编码规范

采用 `资源:动作`：

- `work_items:read` / `work_items:write` / `work_items:transition`
- `assets:read` / `assets:write`
- `requirements:read` / `requirements:write`
- `test_cases:read` / `test_cases:write`
- `menu:read` / `menu:write`
- `users:read` / `users:write`
- `roles:read` / `roles:write`
- `permissions:read` / `permissions:write`

## 4. 数据模型

### 4.1 User

- `user_id`: 唯一 ID
- `username`: 用户名
- `email`: 邮箱
- `role_ids`: 角色 ID 列表
- `status`: `ACTIVE` / `DISABLED`
- `created_at`, `updated_at`

### 4.2 Role

- `role_id`: 唯一 ID
- `name`: 角色名（如 `ADMIN`/`TPM`/`TESTER`/`AUTOMATION`）
- `permission_ids`: 权限 ID 列表
- `created_at`, `updated_at`

### 4.3 Permission

- `perm_id`: 唯一 ID
- `code`: 权限编码（如 `requirements:write`）
- `name`: 权限名称
- `description`: 权限描述

## 5. 权限校验链路

1. 登录成功后由 `/api/v1/auth/login` 返回 JWT。
2. 请求进入路由后先做 JWT 认证（`get_current_user`）。
3. 再由 `require_permission` 或 `require_any_permission` 校验权限。
4. 未认证返回 `401`，权限不足返回 `403`。

实现位置：`app/shared/auth/jwt_auth.py`

## 6. API 能力（当前实现）

### 6.1 用户管理（`/api/v1/auth/users`）

- `POST /users`
- `GET /users`
- `GET /users/{user_id}`
- `PUT /users/{user_id}`
- `PATCH /users/{user_id}/roles`
- `PATCH /users/{user_id}/password`

### 6.2 当前用户能力

- `POST /users/me/password`
- `GET /users/me/permissions`
- `GET /users/me/navigation`

### 6.3 导航访问控制（管理员）

- `GET /admin/navigation/pages`
- `GET /admin/users/{user_id}/navigation`
- `PUT /admin/users/{user_id}/navigation`

### 6.4 角色管理（`/api/v1/auth/roles`）

- `POST /roles`
- `GET /roles`
- `GET /roles/{role_id}`
- `PUT /roles/{role_id}`
- `PATCH /roles/{role_id}/permissions`

### 6.5 权限管理（`/api/v1/auth/permissions`）

- `POST /permissions`
- `GET /permissions`
- `GET /permissions/{perm_id}`
- `PUT /permissions/{perm_id}`

## 7. 默认角色建议

- `ADMIN`：全量权限，含角色与权限维护能力。
- `TPM`：需求与流程推进相关权限。
- `TESTER`：需求读取、用例编辑、流程执行相关权限。
- `AUTOMATION`：用例与自动化执行相关权限。

默认角色初始化由 `scripts/init_rbac.py` 维护。

## 8. 代码映射

- 路由层：`app/modules/auth/api/routes.py`
- 服务层：`app/modules/auth/service/rbac_service.py`
- 数据模型：`app/modules/auth/repository/models/rbac.py`
- Schema：`app/modules/auth/schemas/rbac.py`

## 9. 维护约束

- 新增接口时必须声明权限模式（公开 / 仅登录 / 显式权限）。
- 新增权限码时必须同步更新初始化脚本与测试。
- 权限矩阵以 `authorization_design.md` 第 6 章为准。

## 10. 相关文档

- `authorization_design.md`
- `permission_validation_patterns.md`
- `../../docs/认证与登录指南.md`
- `../../docs/项目架构规范.md`
