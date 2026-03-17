# 认证与授权

## 1. 概述

DMLV4 后端使用 JWT 做认证，使用 RBAC 做授权。

能力边界如下：

- 认证：`/api/v1/auth/login`
- 当前用户权限：`/api/v1/auth/users/me/permissions`
- 当前用户导航可见性：`/api/v1/auth/users/me/navigation`
- 用户、角色、权限、导航定义的管理接口：统一位于 `/api/v1/auth/*`

## 2. 登录流程

1. 客户端调用 `POST /api/v1/auth/login`。
2. 后端校验 `user_id` 和密码。
3. 校验成功后生成 JWT。
4. 后续请求通过 `Authorization: Bearer <token>` 访问受保护接口。

## 3. 登录接口

### 3.1 请求

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "user_id": "admin",
  "password": "password123"
}
```

### 3.2 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "user_id": "admin",
      "username": "管理员",
      "email": "admin@example.com",
      "role_ids": ["ADMIN"],
      "status": "ACTIVE",
      "created_at": "2026-03-17T10:00:00Z",
      "updated_at": "2026-03-17T10:00:00Z"
    }
  }
}
```

### 3.3 失败响应

- 用户不存在：`404 user not found`
- 密码错误：`401 invalid credentials`

## 4. Token 校验

受保护接口通过 `get_current_user` 依赖解析 JWT，并结合权限依赖做授权判断。

常见权限依赖：

- `require_permission("requirements:read")`
- `require_permission("requirements:write")`
- `require_any_permission([...])`

管理员专用接口还会额外通过 `require_admin_user` 判断当前用户是否拥有包含 `ADMIN` 字样的角色。

## 5. 当前用户接口

### 5.1 获取当前用户权限

```http
GET /api/v1/auth/users/me/permissions
Authorization: Bearer <token>
```

成功返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "user_id": "admin",
    "role_ids": ["ADMIN"],
    "permissions": [
      "users:read",
      "users:write",
      "requirements:read",
      "requirements:write",
      "test_cases:read",
      "test_cases:write",
      "execution_tasks:read",
      "execution_tasks:write"
    ]
  }
}
```

### 5.2 获取当前用户导航可见性

```http
GET /api/v1/auth/users/me/navigation
Authorization: Bearer <token>
```

注意：

- 该接口本身还要求 `navigation:read` 权限。

成功返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "user_id": "admin",
    "role_ids": ["ADMIN"],
    "permissions": [
      "navigation:read",
      "navigation:write",
      "requirements:read",
      "test_cases:read"
    ],
    "allowed_nav_views": [
      "requirements",
      "test_cases",
      "execution_tasks",
      "admin_users"
    ]
  }
}
```

### 5.3 用户自助修改密码

```http
POST /api/v1/auth/users/me/password
Authorization: Bearer <token>
Content-Type: application/json

{
  "old_password": "old_password123",
  "new_password": "new_password123"
}
```

成功返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "user_id": "admin",
    "username": "管理员",
    "email": "admin@example.com",
    "role_ids": ["ADMIN"],
    "status": "ACTIVE",
    "created_at": "2026-03-17T10:00:00Z",
    "updated_at": "2026-03-17T12:00:00Z"
  }
}
```

## 6. 管理接口概览

### 6.1 用户

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/users` | 创建用户 |
| GET | `/api/v1/auth/users` | 查询用户列表 |
| GET | `/api/v1/auth/users/{user_id}` | 查询用户详情 |
| PUT | `/api/v1/auth/users/{user_id}` | 更新用户基础信息 |
| PATCH | `/api/v1/auth/users/{user_id}/roles` | 更新用户角色 |
| PATCH | `/api/v1/auth/users/{user_id}/password` | 管理员重置密码 |

### 6.2 角色

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/roles` | 创建角色 |
| GET | `/api/v1/auth/roles` | 查询角色列表 |
| GET | `/api/v1/auth/roles/{role_id}` | 查询角色详情 |
| PUT | `/api/v1/auth/roles/{role_id}` | 更新角色 |
| PATCH | `/api/v1/auth/roles/{role_id}/permissions` | 更新角色权限 |

### 6.3 权限

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/permissions` | 创建权限 |
| GET | `/api/v1/auth/permissions` | 查询权限列表 |
| GET | `/api/v1/auth/permissions/{perm_id}` | 查询权限详情 |
| PUT | `/api/v1/auth/permissions/{perm_id}` | 更新权限 |

### 6.4 导航定义与用户导航

这些接口不是旧文档中的 `/auth/navigation` 风格，而是管理员域名空间下的路由：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/auth/admin/navigation/pages` | 查询导航定义 |
| GET | `/api/v1/auth/admin/navigation/pages/{view}` | 查询单个导航定义 |
| POST | `/api/v1/auth/admin/navigation/pages` | 创建导航定义 |
| PUT | `/api/v1/auth/admin/navigation/pages/{view}` | 更新导航定义 |
| DELETE | `/api/v1/auth/admin/navigation/pages/{view}` | 删除导航定义 |
| GET | `/api/v1/auth/admin/users/{user_id}/navigation` | 查询用户导航可见性 |
| PUT | `/api/v1/auth/admin/users/{user_id}/navigation` | 更新用户导航可见性 |

### 6.5 管理接口示例

创建用户：

```http
POST /api/v1/auth/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "tester01",
  "username": "测试工程师",
  "password": "tester123",
  "email": "tester01@example.com",
  "role_ids": ["TESTER"],
  "status": "ACTIVE"
}
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439012",
    "user_id": "tester01",
    "username": "测试工程师",
    "email": "tester01@example.com",
    "role_ids": ["TESTER"],
    "status": "ACTIVE",
    "created_at": "2026-03-17T12:10:00Z",
    "updated_at": "2026-03-17T12:10:00Z"
  }
}
```

查询角色列表：

```http
GET /api/v1/auth/roles?limit=20&offset=0
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": "507f1f77bcf86cd799439101",
      "role_id": "ADMIN",
      "name": "ADMIN",
      "permission_ids": ["users:read", "users:write", "requirements:read"],
      "created_at": "2026-03-17T09:00:00Z",
      "updated_at": "2026-03-17T09:00:00Z"
    }
  ]
}
```

创建导航定义：

```http
POST /api/v1/auth/admin/navigation/pages
Authorization: Bearer <token>
Content-Type: application/json

{
  "view": "execution_tasks",
  "label": "执行任务",
  "permission": "execution_tasks:read",
  "description": "执行任务列表页",
  "order": 30,
  "is_active": true
}
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439201",
    "view": "execution_tasks",
    "label": "执行任务",
    "permission": "execution_tasks:read",
    "description": "执行任务列表页",
    "order": 30,
    "is_active": true
  }
}
```

## 7. Schema 事实

与旧文档相比，当前代码中的几个关键事实是：

- 登录请求字段是 `user_id`，不是 `username`。
- 登录响应中的 `token_type` 默认值是 `Bearer`。
- `UserResponse` 包含 `created_at` 和 `updated_at`。
- `MePermissionsResponse.permissions` 返回的是权限码字符串列表，而不是完整权限对象列表。

## 8. RBAC 核心模型

### 8.1 用户

- 业务主键：`user_id`
- 角色集合：`role_ids`
- 状态：`ACTIVE` / `INACTIVE`

### 8.2 角色

- 业务主键：`role_id`
- 权限集合：`permission_ids`

### 8.3 权限

- 业务主键：`perm_id`
- 权限码：`code`

### 8.4 导航页

- 业务主键：`view`
- 访问控制字段：`permission`
- 启用状态：`is_active`

## 9. 初始化脚本

常用初始化流程：

```bash
cd backend
python scripts/init_rbac.py
python scripts/create_user.py --user-id admin --username 管理员 --password 'admin123' --roles ADMIN
```

## 10. 文档修正说明

本页已修正以下常见误导点：

- 删除了前端实现细节。
- 删除了代码中不存在的 `/auth/me`、`/auth/navigation` 风格旧路径。
- 将权限返回结构修正为“权限码字符串列表”。
