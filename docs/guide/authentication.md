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

### 4.1 `get_current_user`

`get_current_user` 是大多数受保护接口的第一层依赖，职责包括：

- 从 `Authorization: Bearer <token>` 中提取 JWT。
- 校验签名、过期时间、`iss`、`aud` 等基础声明。
- 从 token 的 `sub` 中取出 `user_id`。
- 回查 `UserDoc`，并确认用户状态为 `ACTIVE`。
- 将当前用户信息以字典形式注入后续依赖和路由函数。

如果 token 非法、过期、用户不存在或已禁用，会直接返回 `401`。

### 4.2 `require_permission`

`require_permission(permission_code)` 是最常用的接口级授权依赖，用于要求当前用户必须拥有某一个明确的权限码。

典型写法：

```python
@router.get(
    "/requirements",
    dependencies=[Depends(require_permission("requirements:read"))],
)
async def list_requirements():
    ...
```

它的功能可以概括为：

- 声明当前接口需要一个指定权限，例如 `requirements:read`。
- 在请求进入路由函数前执行校验。
- 内部复用 `require_any_permission([permission_code])`，因此本质上是“至少命中一个权限”的单权限特例。
- 如果当前用户角色中包含 `ADMIN`，则直接放行，不再检查具体权限码。
- 如果普通用户不具备该权限，则返回 `403 permission denied`。

对开发人员来说，它的价值不只是“拦一下请求”，更重要的是把接口授权要求直接固化在路由定义上。阅读路由时，可以立刻看到接口依赖哪个权限码。

### 4.3 `require_any_permission`

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

这类依赖适合“跨模块复用接口”或“管理端与业务端共享读取能力”的场景。

### 4.4 `require_permission` 的执行链路

从 FastAPI 请求进入到权限校验完成，大致会经历下面这条链路：

1. `HTTPBearer` 提取请求头中的 Bearer token。
2. `get_current_user` 解析并校验 JWT。
3. `require_permission("xxx")` 创建一个依赖检查器。
4. 检查器读取当前用户的 `role_ids`。
5. 如果命中管理员角色，直接放行。
6. 如果不是管理员，则按 `user -> role_ids -> permission_ids -> permission.code` 计算有效权限。
7. 判断目标权限码是否存在于有效权限集合中。
8. 通过则继续执行路由函数，失败则返回 `403`。

这里要注意两点：

- `require_permission` 自身不查询业务数据，也不判断工作流状态，它只负责 RBAC 层面的“有没有这个权限”。
- 如果接口还要求“只能负责人修改”“只有某个状态允许操作”，这些规则应在后续业务层继续校验。

### 4.5 什么时候用它，什么时候不够

推荐使用 `require_permission` 的场景：

- 资源列表查询、详情查询、创建、更新、删除等标准接口授权。
- 管理接口对某个后台资源的读写限制。
- 前后端已经约定清楚的静态权限边界。

仅使用 `require_permission` 不够的场景：

- 权限取决于数据归属关系，例如“只能修改自己创建的数据”。
- 权限取决于工作流状态，例如“仅 DRAFT 状态允许编辑”。
- 权限取决于更细粒度的领域规则，例如负责人、审批人、执行人等动态上下文。

这类情况通常应采用“路由层 RBAC + 应用/领域层业务权限”的组合，而不是试图把所有判断都编码成一个权限码。

## 5. RBAC 核心模型

这一部分面向后端和前端开发人员，描述系统中“用户、角色、权限、导航”四类对象如何协作完成授权判断。

### 5.1 模型关系总览

系统采用典型的 RBAC 关系链：

`User -> Role -> Permission`

同时引入导航可见性这一层：

`User -> allowed_nav_views`

以及：

`Permission -> NavigationPage.permission`

可以把它理解成两条并行链路：

- 业务接口授权链路：用户绑定角色，角色绑定权限，接口通过权限码做访问控制。
- 前端导航可见性链路：导航页面定义自身需要的权限，后端根据用户有效权限推导可见页面；如果用户存在显式导航覆盖，则优先使用覆盖结果。

### 5.2 User

`UserDoc` 表示登录主体，是认证和授权求值的起点。开发时最重要的字段包括：

- `user_id`：业务上的登录账号，登录接口使用它作为身份标识。
- `password_salt` / `password_hash`：密码不会明文存储，创建用户或修改密码时由服务层完成加盐和哈希。
- `role_ids`：用户直接绑定的角色 ID 列表。
- `status`：当前是否可登录，认证阶段会校验是否为 `ACTIVE`。
- `allowed_nav_views`：用户级导航覆盖配置，用于覆盖默认的“按权限推导导航”结果。

对开发人员来说，`UserDoc` 不是直接挂权限码，而是只维护角色关系。这样做的好处是权限收敛在角色层，权限变更只需要修改角色，不需要批量改用户。

### 5.3 Role

`RoleDoc` 是权限聚合单元，用来把一组权限打包给用户。关键字段主要是：

- `role_id`：角色主键，例如 `ADMIN`、`TESTER`。
- `name`：角色展示名称。
- `permission_ids`：该角色拥有的权限 ID 列表。

在实现上，一个用户可以同时拥有多个角色，系统会对多个角色的权限做并集计算，不做“拒绝优先”或“最小权限交集”这类复杂规则。因此：

- 角色设计应该偏向职责分组，而不是给每个用户定制一个角色。
- 如果一个接口被多个岗位共同使用，应把对应权限抽到共享角色或多个角色中复用。
- 修改角色权限会影响所有绑定该角色的用户，这也是最常见的授权调整入口。

### 5.4 Permission

`PermissionDoc` 是最小授权单元。接口层、导航层、部分业务层都会围绕权限码工作。核心字段包括：

- `perm_id`：权限记录 ID，供角色绑定使用。
- `code`：真正参与鉴权的权限编码，例如 `requirements:read`、`requirements:write`、`nav:req_list:view`。
- `name` / `description`：面向管理端和维护人员的可读信息。

对开发人员而言，真正重要的是 `code`，因为：

- API 路由依赖一般直接写权限码，例如 `require_permission("requirements:read")`。
- 角色求值最终返回的也是权限码集合。
- 导航页面定义中的 `permission` 字段，本质上也是权限码。

建议把权限码视为稳定契约。一旦前后端或多个模块都引用某个权限码，就不要随意改名；新增能力时优先新增权限码，而不是复用语义接近但边界不清的旧权限。

### 5.5 NavigationPage

`NavigationPageDoc` 不是标准 RBAC 三元组的一部分，但在 DMLV4 中它承担了“前端导航授权配置”的职责。每个导航页面会定义：

- `view`：前端路由或视图标识。
- `permission`：访问该页面需要的权限码，典型值如 `nav:req_list:view`。
- 其他展示字段：如名称、排序、是否启用等，由导航管理服务维护。

这意味着“是否能看到某个菜单”不是由前端硬编码决定，而是由后端根据导航定义和用户权限统一计算。这样有两个直接收益：

- 前后端对导航授权规则的理解一致，不容易出现“接口无权但菜单可见”或“有权但菜单缺失”的偏差。
- 新增后台页面时，可以把页面定义和权限要求一起纳入管理接口，而不是散落在前端条件判断里。

### 5.6 有效权限如何计算

当前实现中的权限求值流程可以概括为：

1. 通过 JWT 解析出当前登录用户。
2. 根据 `user_id` 查询 `UserDoc`。
3. 读取用户的 `role_ids`。
4. 根据所有角色查询其绑定的 `permission_ids`。
5. 将权限记录转换为权限码集合。
6. 对多角色结果取并集，作为用户的有效权限。

`/api/v1/auth/users/me/permissions` 返回的就是这一步计算后的结果，而不是数据库里某个“预先展开”的字段。

这带来两个开发层面的含义：

- 角色和权限更新后，用户的有效权限会按最新关联关系重新计算，不需要额外做权限缓存落库。
- 如果你要排查“某个用户为什么有这个权限”，应该沿着 `user -> role_ids -> permission_ids -> permission.code` 这条链路去看，而不是只检查用户表。

### 5.7 导航可见性如何计算

导航不是简单地“权限码存在就显示”，而是包含用户级覆盖逻辑。当前规则为：

1. 管理员角色用户直接拥有全部导航页面。
2. 非管理员用户如果设置了 `allowed_nav_views`，优先使用该覆盖列表。
3. 如果没有用户级覆盖，则根据用户有效权限与 `NavigationPage.permission` 做匹配推导。
4. 如果仍推导不出结果，系统会回退到默认导航集合。
5. 最终结果还会补齐必须存在的基础页面。

因此，`allowed_nav_views` 应该被理解为“显式导航定制”，而不是权限系统本身。它解决的是个性化或临时运营配置问题，不应替代正式的角色授权。

### 5.8 开发时应把授权逻辑放在哪里

推荐遵循下面的分层约定：

- API 层：使用 `require_permission(...)`、`require_any_permission(...)`、`require_admin_user` 做入口级拦截。
- Service 层：负责用户、角色、权限、导航之间的关系校验和写入规则，例如更新用户角色前先校验角色是否存在。
- Domain / Application 层：当某些操作除了 RBAC 之外还依赖业务状态、负责人、工作流节点时，再叠加领域权限判断。

换句话说：

- “这个用户有没有访问某类资源的资格”通常是 RBAC。
- “这个用户在当前状态下能不能修改这条具体数据”通常还需要业务规则参与。

不要把所有权限判断都堆在路由层，也不要把接口级基础鉴权下沉到每个业务服务里重复实现。

### 5.9 面向开发的建模建议

- 用户只绑角色，不直接绑权限，避免授权关系失控。
- 角色尽量表达岗位职责，而不是表达某个具体人的临时组合。
- 权限码命名保持资源加动作风格，例如 `requirements:read`、`test_cases:write`、`navigation:read`。
- 导航权限和业务接口权限可以共存，但语义要清晰区分；前者描述页面可见性，后者描述数据操作能力。
- 新增模块时，先定义清楚资源边界和动作集合，再补角色绑定和菜单映射，避免后续权限码失真。

## 6. 当前用户接口

### 6.1 获取当前用户权限

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

### 6.2 获取当前用户导航可见性

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

### 6.3 用户自助修改密码

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

## 7. 管理接口概览

### 7.1 用户

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/users` | 创建用户 |
| GET | `/api/v1/auth/users` | 查询用户列表 |
| GET | `/api/v1/auth/users/{user_id}` | 查询用户详情 |
| PUT | `/api/v1/auth/users/{user_id}` | 更新用户基础信息 |
| PATCH | `/api/v1/auth/users/{user_id}/roles` | 更新用户角色 |
| PATCH | `/api/v1/auth/users/{user_id}/password` | 管理员重置密码 |

### 7.2 角色

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/roles` | 创建角色 |
| GET | `/api/v1/auth/roles` | 查询角色列表 |
| GET | `/api/v1/auth/roles/{role_id}` | 查询角色详情 |
| PUT | `/api/v1/auth/roles/{role_id}` | 更新角色 |
| PATCH | `/api/v1/auth/roles/{role_id}/permissions` | 更新角色权限 |

### 7.3 权限

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/permissions` | 创建权限 |
| GET | `/api/v1/auth/permissions` | 查询权限列表 |
| GET | `/api/v1/auth/permissions/{perm_id}` | 查询权限详情 |
| PUT | `/api/v1/auth/permissions/{perm_id}` | 更新权限 |

### 7.4 导航定义与用户导航

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

### 7.5 管理接口示例

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

## 8. Schema 事实

与旧文档相比，当前代码中的几个关键事实是：

- 登录请求字段是 `user_id`，不是 `username`。
- 登录响应中的 `token_type` 默认值是 `Bearer`。
- `UserResponse` 包含 `created_at` 和 `updated_at`。
- `MePermissionsResponse.permissions` 返回的是权限码字符串列表，而不是完整权限对象列表。

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
