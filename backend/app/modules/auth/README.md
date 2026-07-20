# Auth Module

认证授权模块现在采用精简 RBAC：

```text
User -> Roles -> static permission codes
```

权限是代码契约，定义在 `app/modules/auth/permissions.py`，不再作为数据库模型维护。角色存储选择了哪些权限码，用户只绑定角色。

## 功能范围

- JWT 登录和当前用户识别
- 密码 hash + salt 存储
- 用户管理：创建、查询、更新、禁用、重置密码、分配角色
- 角色管理：创建、查询、更新、删除自定义角色、配置静态权限码
- 权限查询：只读返回代码内静态权限清单

已移除：

- 动态权限创建、更新、删除
- 用户级额外权限
- 用户级导航覆盖
- 数据库导航页面配置
- 独立用户组模型/接口

## API

### Auth

- `POST /auth/login`
- `POST /auth/users/me/password`
- `GET /auth/users/me`
- `GET /auth/users/me/permissions`

### Users

- `POST /auth/users`
- `GET /auth/users`
- `GET /auth/users/{user_id}`
- `PUT /auth/users/{user_id}`
- `PATCH /auth/users/{user_id}/roles`
- `PATCH /auth/users/{user_id}/password`
- `DELETE /auth/users/{user_id}`
- `GET /auth/users/{user_id}/permissions`

### Roles

- `POST /auth/roles`
- `GET /auth/roles`
- `GET /auth/roles/{role_id}`
- `PUT /auth/roles/{role_id}`
- `PATCH /auth/roles/{role_id}/permissions`
- `DELETE /auth/roles/{role_id}`

### Permissions

- `GET /auth/permissions`

## 数据模型

### UserDoc

```python
user_id: str
username: str
email: Optional[str]
password_hash: str
password_salt: str
role_ids: list[str]
status: str  # ACTIVE / DISABLED
itcode: str
subscribe_notifications: bool
```

### RoleDoc

```python
role_id: str
name: str
description: Optional[str]
is_system: bool
permission_ids: list[str]  # static permission codes
```

## 初始化

```bash
cd backend
python scripts/init/init_rbac.py
```

该脚本只初始化/同步 `roles` 集合。`permissions` 和 `navigation_pages` 集合不再需要；如果重新初始化数据库，可以不创建这两张表。
