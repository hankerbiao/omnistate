# Auth 模块

## 模块职责

`auth` 负责三件事：

- 用户登录与 JWT 认证
- 用户、角色管理
- 基于角色的权限校验

当前权限模型已经瘦身为：

`User -> Role -> static permission codes`

权限是代码内静态清单，不再是数据库业务数据；导航可见性由前端根据权限过滤，不再有后端导航定义表和用户级导航覆盖。

## 当前结构特点

`auth` 以资源级 service 为主：

- `UserService`：用户 CRUD、登录校验、密码修改、用户角色绑定。
- `RoleService`：角色 CRUD、角色权限绑定。
- `PermissionService`：只读返回静态权限清单。

## 核心目录

- `api/`
  登录、用户、角色、只读权限列表路由。
- `service/`
  资源级 service、校验辅助和异常定义。
- `repository/models/`
  只注册 `UserDoc`、`RoleDoc` 两个 Beanie 文档。
- `permissions.py`
  静态权限清单，角色表中的 `permission_ids` 直接引用这里的权限码。
- `schemas/rbac.py`
  请求响应结构。

## 核心模型

- `UserDoc`
- `RoleDoc`

不再注册或初始化：

- `PermissionDoc`
- `NavigationPageDoc`

## 关键调用链

- 登录：
  API -> `UserService.authenticate_user()` -> JWT 生成。
- 当前用户：
  `get_current_user()` 解 JWT，按 `user_id` 读取 `UserDoc`，并校验用户状态。
- 权限校验：
  `require_permission()` / `require_any_permission()` -> 读取用户角色 -> 聚合角色 `permission_ids` -> 对静态权限码求交。
- 用户管理：
  API -> `UserService`。
- 角色管理：
  API -> `RoleService`。
- 权限列表：
  API -> `PermissionService.list_permissions()` -> `permissions.py`。

## RBAC 初始化默认角色与权限

初始化脚本是 `backend/scripts/init/sync_rbac.py`。它只幂等写入 `roles` 集合：

- 不创建 `permissions` 集合。
- 不创建 `navigation_pages` 集合。
- 写入角色时会过滤掉不存在于静态权限清单的权限码。

### 静态权限清单

静态权限定义位于 `app/modules/auth/permissions.py`。权限码采用 `resource:action` 或 `nav:<page>:view` 风格，例如：

- `users:read` / `users:write`
- `roles:read` / `roles:write`
- `permissions:read`
- `requirements:read` / `requirements:write`
- `test_cases:read` / `test_cases:write`
- `execution_plans:read` / `execution_plans:write`
- `execution_tasks:read` / `execution_tasks:write`
- `execution_agents:read` / `execution_agents:write`
- `projects:read` / `projects:write` / `projects:delete`
- `system:config`
- `case_governance:read`
- `search:global`

如需新增权限，先在 `permissions.py` 增加静态项，再在初始化脚本的默认角色中绑定。

### 默认角色

当前默认系统角色：

| 角色 ID | 说明 |
| --- | --- |
| `ADMIN` | 系统管理员，绑定全部静态权限 |
| `TPM` | 测试项目管理员，偏项目管理、需求、流程和执行管理 |
| `REVIEWER` | 评审者，偏需求和测试用例审核 |
| `MANUAL_DEV` | 手动测试开发工程师 |
| `QA` | 质量保证工程师 |
| `TESTER` | 测试执行工程师 |
| `AUTO_DEV` | 自动化测试开发工程师 |
| `AUTOMATION` | 自动化测试运行角色 |

## 认证与登录中的 Token 创建和校验

当前后端的 Token 机制主要在：

- `app/modules/auth/api/routes_login.py`
- `app/shared/auth/jwt_auth.py`

### 登录时如何创建 Token

登录入口是 `POST /api/v1/auth/login`。

链路如下：

1. 路由接收 `user_id` 和 `password`。
2. 调用 `UserService.authenticate_user()` 校验用户是否存在、密码是否正确。
3. 认证成功后，路由调用 `create_access_token(user["user_id"])`。
4. 返回 `access_token` 和当前用户信息。

登录接口不直接拼 JWT，而是统一交给 `app/shared/auth/jwt_auth.py` 处理。

### Token 创建时写入了哪些内容

`create_access_token()` 构造标准三段式 JWT：

- Header
  - `alg`: `HS256`
  - `typ`: `JWT`
- Payload
  - `sub`: 用户业务 ID，也就是 `user_id`
  - `iat`: 签发时间
  - `exp`: 过期时间
  - `iss`: 签发者，来自配置
  - `aud`: 受众，来自配置
- Signature
  - 使用 JWT 密钥和 HMAC-SHA256 对 `header.payload` 签名。

### 请求进来后如何校验 Token

校验入口是 `get_current_user()`：

1. `HTTPBearer` 从请求头读取 `Authorization: Bearer <token>`。
2. `decode_token(token)` 校验 token 结构、签名、过期时间、签发者和受众。
3. 取出 `sub`，按 `user_id` 查询 `UserDoc`。
4. 用户不存在或状态不是 `ACTIVE` 时拒绝请求。
5. 通过后返回当前用户字典。

### 权限校验是如何接在 Token 之后的

Token 校验只能证明“用户身份有效”，后续授权流程是：

1. `require_permission(...)` 或 `require_any_permission(...)` 依赖先拿到 `current_user`。
2. 若用户角色中包含管理员标识，则直接放行。
3. 否则根据用户 `role_ids` 查询角色。
4. 聚合所有角色的 `permission_ids`。
5. 用静态权限清单过滤并转换为有效权限码集合。
6. 如果请求所需权限码不在集合中，则返回 `403 permission denied`。

## 关键业务规则

- 用户只绑定角色，不直接绑定额外权限。
- 角色直接绑定静态权限码。
- 权限定义不入库，不提供权限写接口。
- 管理员判定由角色标识推导。
- 用户有效权限运行时从角色聚合，不落库缓存。
- 业务归属、工作流状态等动态规则不塞进 RBAC，应在业务 service/domain 中继续校验。

## 常见修改场景

- 改登录或 token：看 `app/shared/auth/*` 和 `auth/api/routes_login.py`。
- 新增权限码：改 `auth/permissions.py`，再更新 `scripts/init/sync_rbac.py` 的角色绑定。
- 改角色/用户管理接口：看 `auth/api/routes_roles.py`、`auth/api/routes_users.py` 与对应 service。
- 改路由权限依赖：看具体路由上的 `require_permission(...)`。

## 数据库说明

重新初始化数据库时，Auth 只需要 `users`、`roles` 两个集合。

旧集合/字段不再使用：

- `permissions`
- `navigation_pages`
- `users.extra_permission_ids`
- `users.allowed_nav_views`
