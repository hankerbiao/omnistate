# 认证与授权

## 1. 概述

DMLV4 后端使用 JWT 做认证，使用精简 RBAC 做授权。

当前模型是：

`User -> Role -> static permission codes`

能力边界如下：

- 认证：`POST /api/v1/auth/login`
- 当前用户权限：`GET /api/v1/auth/users/me/permissions`
- 用户管理：`/api/v1/auth/users/*`
- 角色管理：`/api/v1/auth/roles/*`
- 权限列表：`GET /api/v1/auth/permissions`

权限是代码内静态清单，不入库，不提供创建、更新、删除接口。导航可见性由前端基于当前用户权限过滤，不再有后端导航定义表和用户级导航覆盖。

## 2. 登录流程

1. 客户端调用 `POST /api/v1/auth/login`。
2. 后端校验 `user_id` 和密码。
3. 校验成功后生成 JWT。
4. 后续请求通过 `Authorization: Bearer <token>` 访问受保护接口。

### 2.1 请求

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "user_id": "admin",
  "password": "password123"
}
```

### 2.2 成功响应

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

### 2.3 失败响应

- 用户不存在：`404 user not found`
- 密码错误：`401 invalid credentials`
- 用户禁用：`401 user disabled`

## 3. Token 校验

受保护接口通过 `get_current_user` 依赖解析 JWT，并结合权限依赖做授权判断。

常见权限依赖：

- `require_permission("requirements:read")`
- `require_permission("requirements:write")`
- `require_any_permission([...])`

管理员专用接口还会额外通过 `require_admin_user` 判断当前用户是否拥有包含 `ADMIN` 字样的角色。

### 3.1 `get_current_user`

`get_current_user` 是大多数受保护接口的第一层依赖，职责包括：

- 从 `Authorization: Bearer <token>` 中提取 JWT。
- 校验签名、过期时间、`iss`、`aud` 等基础声明。
- 从 token 的 `sub` 中取出 `user_id`。
- 回查 `UserDoc`，并确认用户状态为 `ACTIVE`。
- 将当前用户信息以字典形式注入后续依赖和路由函数。

如果 token 非法、过期、用户不存在或已禁用，会直接返回 `401`。

### 3.2 `require_permission`

`require_permission(permission_code)` 用于要求当前用户必须拥有某一个明确的权限码。

典型写法：

```python
@router.get(
    "/requirements",
    dependencies=[Depends(require_permission("requirements:read"))],
)
async def list_requirements():
    ...
```

它的规则是：

- 声明当前接口需要一个指定权限，例如 `requirements:read`。
- 在请求进入路由函数前执行校验。
- 内部复用 `require_any_permission([permission_code])`。
- 如果当前用户角色中包含 `ADMIN`，则直接放行。
- 如果普通用户不具备该权限，则返回 `403 permission denied`。

### 3.3 `require_any_permission`

当一个接口允许多个权限中的任意一个访问时，可以使用 `require_any_permission(permission_codes)`。

例如：

```python
dependencies=[Depends(require_any_permission(["users:read", "work_items:read"]))]
```

它的规则是：

- 参数中的权限码会先去空、去重。
- 只要当前用户有效权限与要求集合存在交集，就允许访问。
- 管理员角色同样直接放行。
- 如果一个都不命中，则返回 `403 permission denied`。

## 4. RBAC 核心模型

### 4.1 User

`UserDoc` 表示登录主体，是认证和授权求值的起点。关键字段包括：

- `user_id`：业务登录账号。
- `password_salt` / `password_hash`：密码加盐哈希，不明文存储。
- `role_ids`：用户直接绑定的角色 ID 列表。
- `status`：当前是否可登录，认证阶段会校验是否为 `ACTIVE`。

用户不直接绑定权限码，也没有额外权限字段。权限变更应通过角色完成。

### 4.2 Role

`RoleDoc` 是权限聚合单元，用来把一组权限打包给用户。关键字段包括：

- `role_id`：角色主键，例如 `ADMIN`、`TESTER`。
- `name`：角色展示名称。
- `permission_ids`：该角色拥有的静态权限码列表。

一个用户可以同时拥有多个角色，系统会对多个角色的权限做并集计算。

### 4.3 Permission

权限定义位于 `app/modules/auth/permissions.py`，不是数据库模型。每个权限包含：

- `perm_id`：权限 ID，当前与权限码一致。
- `code`：真正参与鉴权的权限编码，例如 `requirements:read`。
- `name` / `description`：管理端展示信息。

建议把权限码视为稳定契约。一旦前后端或多个模块都引用某个权限码，就不要随意改名；新增能力时优先新增权限码。

### 4.4 有效权限如何计算

当前实现中的权限求值流程：

1. 通过 JWT 解析出当前登录用户。
2. 根据 `user_id` 查询 `UserDoc`。
3. 读取用户的 `role_ids`。
4. 查询所有角色并聚合其 `permission_ids`。
5. 用静态权限清单过滤合法权限码。
6. 对多角色结果取并集，作为用户的有效权限。

`/api/v1/auth/users/me/permissions` 返回的就是这一步计算后的结果，而不是数据库里某个“预先展开”的字段。

### 4.5 授权逻辑放在哪里

推荐遵循下面的分层约定：

- API 层：使用 `require_permission(...)`、`require_any_permission(...)`、`require_admin_user` 做入口级拦截。
- Service 层：负责用户、角色之间的关系校验和写入规则，例如更新用户角色前先校验角色是否存在。
- Domain / Application 层：当某些操作除了 RBAC 之外还依赖业务状态、负责人、工作流节点时，再叠加领域权限判断。

不要把所有权限判断都堆在路由层，也不要把接口级基础鉴权下沉到每个业务服务里重复实现。

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

### 5.2 用户自助修改密码

```http
POST /api/v1/auth/users/me/password
Authorization: Bearer <token>
Content-Type: application/json

{
  "old_password": "old_password123",
  "new_password": "new_password123"
}
```

成功返回当前用户信息。

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
| GET | `/api/v1/auth/permissions` | 查询静态权限列表 |

权限不提供写接口。角色通过 `permission_ids` 直接绑定这些静态权限码。

## 7. 初始化脚本

常用初始化流程：

```bash
cd backend
python scripts/init/sync_rbac.py
python scripts/init/create_user.py --user-id admin --username 管理员 --password 'admin123' --roles ADMIN
```

`sync_rbac.py` 只初始化/同步 `roles` 集合。重新初始化数据库时，`permissions` 和 `navigation_pages` 集合不再需要。旧用户字段 `extra_permission_ids`、`allowed_nav_views` 也不再使用。

## 8. Schema 事实

- 登录请求字段是 `user_id`，不是 `username`。
- 登录响应中的 `token_type` 默认值是 `Bearer`。
- `UserResponse` 包含 `created_at` 和 `updated_at`。
- `MePermissionsResponse.permissions` 返回的是权限码字符串列表，而不是完整权限对象列表。
- `PermissionResponse` 来自静态权限清单，不包含创建/更新时间。
