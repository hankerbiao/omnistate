# Auth 模块

## 模块职责

`auth` 负责：

- 用户、角色、权限管理
- JWT 登录认证
- RBAC 授权
- 导航访问控制

## 当前结构特点

`auth` 现在以资源级 service 为主，不再通过单一大 facade 汇总：

- `UserService`
- `RoleService`
- `PermissionService`
- `NavigationAccessService`
- `NavigationPageService`

## 核心目录

- `api/`
  登录、用户、角色、权限、导航相关路由
- `service/`
  资源级 service 和异常定义
- `repository/models/`
  用户、角色、权限、导航模型
- `schemas/rbac.py`
  请求响应结构

## 核心模型

- `UserDoc`
- `RoleDoc`
- `PermissionDoc`
- `NavigationPageDoc`

## 关键调用链

- 登录：
  API -> `UserService.authenticate_user()` -> JWT 生成
- 用户管理：
  API -> `UserService`
- 角色与权限管理：
  API -> `RoleService` / `PermissionService`
- 导航访问：
  API -> `NavigationAccessService`

## RBAC 初始化默认角色与权限

RBAC 默认数据初始化脚本是 `backend/scripts/init_rbac.py`。这份脚本负责幂等写入：

- `permissions` 集合中的默认权限
- `roles` 集合中的默认角色
- 每个角色默认绑定的 `permission_ids`

### 默认权限表

| 权限码 | 说明 |
| --- | --- |
| `nav:public` | 登录后即可访问的公共导航权限 |
| `work_items:read` | 读取 workflow 工单 |
| `work_items:write` | 创建或修改 workflow 工单 |
| `work_items:transition` | 执行 workflow 状态流转 |
| `users:read` | 查看用户 |
| `users:write` | 修改用户 |
| `roles:read` | 查看角色 |
| `roles:write` | 修改角色 |
| `permissions:read` | 查看权限定义 |
| `permissions:write` | 修改权限定义 |
| `requirements:read` | 查看需求 |
| `requirements:write` | 修改需求 |
| `test_cases:read` | 查看测试用例 |
| `test_cases:write` | 修改测试用例 |
| `execution_tasks:read` | 查看执行任务 |
| `execution_tasks:write` | 修改执行任务 |
| `terminal:connect` | 使用终端连接能力 |
| `navigation:read` | 查看导航页面定义 |
| `navigation:write` | 修改导航页面定义 |

### 默认角色表

| 角色 ID | 角色名 | 初始化语义 |
| --- | --- | --- |
| `ADMIN` | `ADMIN` | 拥有默认权限表中的全部权限 |
| `TPM` | `TPM` | 偏需求、流程推进和执行管理 |
| `TESTER` | `TESTER` | 偏测试设计、状态流转和执行查看 |
| `AUTOMATION` | `AUTOMATION` | 偏自动化用例维护和执行相关能力 |

### 角色与权限绑定表

| 角色 | 默认权限 |
| --- | --- |
| `ADMIN` | `nav:public`、`work_items:read`、`work_items:write`、`work_items:transition`、`users:read`、`users:write`、`roles:read`、`roles:write`、`permissions:read`、`permissions:write`、`requirements:read`、`requirements:write`、`test_cases:read`、`test_cases:write`、`execution_tasks:read`、`execution_tasks:write`、`terminal:connect`、`navigation:read`、`navigation:write` |
| `TPM` | `users:read`、`requirements:read`、`requirements:write`、`test_cases:read`、`work_items:read`、`work_items:write`、`work_items:transition`、`execution_tasks:read`、`execution_tasks:write`、`terminal:connect`、`navigation:read`、`navigation:write` |
| `TESTER` | `users:read`、`requirements:read`、`test_cases:read`、`test_cases:write`、`work_items:read`、`work_items:write`、`work_items:transition`、`execution_tasks:read`、`terminal:connect`、`navigation:read`、`navigation:write` |
| `AUTOMATION` | `users:read`、`test_cases:read`、`test_cases:write`、`assets:read`、`work_items:read`、`work_items:write`、`execution_tasks:read`、`terminal:connect`、`navigation:read`、`navigation:write` |

### 初始化字段说明

| 集合 | 字段 | 说明 |
| --- | --- | --- |
| `permissions` | `perm_id` | 权限业务 ID，当前和 `code` 保持一致 |
| `permissions` | `code` | 授权判断实际使用的权限码，格式通常为 `resource:action` |
| `permissions` | `name` | 权限显示名，初始化脚本会在重复执行时刷新 |
| `permissions` | `description` | 扩展描述，默认初始化为 `None` |
| `roles` | `role_id` | 角色业务 ID，例如 `ADMIN`、`TPM` |
| `roles` | `name` | 角色名称，当前与 `role_id` 相同 |
| `roles` | `permission_ids` | 角色绑定的权限 ID 列表，授权时会据此聚合用户权限 |

### 当前初始化脚本的风险点

- `AUTOMATION` 角色包含 `assets:read`，但 `DEFAULT_PERMISSIONS` 并没有初始化这个权限码。这意味着如果数据库里之前没有手工补过该权限，角色会引用一个未初始化的权限 ID。
- `ADMIN` 目前通过“直接取默认权限列表全部 code”获得全量权限，所以它能覆盖的范围取决于 `DEFAULT_PERMISSIONS` 是否完整。

## 认证与登录中的 Token 创建和校验

当前后端的 Token 机制实现主要在：

- `app/modules/auth/api/routes_login.py`
- `app/shared/auth/jwt_auth.py`

### 登录时如何创建 Token

登录入口是 `POST /api/v1/auth/login`。

链路如下：

1. 路由接收 `user_id` 和 `password`
2. 调用 `UserService.authenticate_user()` 校验用户是否存在、密码是否正确
3. 认证成功后，路由调用 `create_access_token(user["user_id"])`
4. 返回 `access_token` 和当前用户信息

也就是说，登录接口本身不直接拼 JWT，而是统一交给 `app/shared/auth/jwt_auth.py` 处理。

### Token 创建时写入了哪些内容

`create_access_token()` 当前会构造一个标准三段式 JWT：

- Header
  - `alg`: `HS256`
  - `typ`: `JWT`
- Payload
  - `sub`: 用户业务 ID，也就是 `user_id`
  - `iat`: 签发时间
  - `exp`: 过期时间
  - `iss`: 签发者，来自 `JWT_ISSUER`
  - `aud`: 受众，来自 `JWT_AUDIENCE`
- Signature
  - 使用 `JWT_SECRET_KEY` 和 HMAC-SHA256 对 `header.payload` 签名

这里最关键的是：

- `sub` 是后续查当前用户的入口字段
- `exp`、`iss`、`aud` 会在校验阶段严格检查

### Token 是如何编码和签名的

当前实现没有依赖第三方 JWT 库做黑盒处理，而是手工实现了：

- `_b64url_encode()`
  用于 Base64 URL Safe 编码
- `_sign_hs256()`
  用于基于密钥生成 HS256 签名

创建流程本质上是：

1. 把 header 和 payload 转成 JSON
2. 分别做 base64url 编码
3. 拼成 `header.payload`
4. 用 `JWT_SECRET_KEY` 做 HMAC-SHA256 签名
5. 拼成最终 token：`header.payload.signature`

### 请求进来后如何校验 Token

校验入口主要是 `get_current_user()`，它会被 FastAPI 依赖系统挂到需要认证的接口上。

校验链路如下：

1. `HTTPBearer` 从请求头拿到 `Authorization: Bearer <token>`
2. `get_current_user()` 调用 `decode_token(token)`
3. `decode_token()` 先拆分三段结构
4. 重新计算签名，并和 token 中的签名做比对
5. 解析 payload
6. 校验 `exp` 是否过期
7. 校验 `iss` 是否等于 `JWT_ISSUER`
8. 校验 `aud` 是否等于 `JWT_AUDIENCE`
9. 取出 `sub`，按 `user_id` 查询 `UserDoc`
10. 若用户不存在或状态不是 `ACTIVE`，直接拒绝

通过后，`get_current_user()` 会返回当前用户字典，里面包含：

- `id`
- `user_id`
- `username`
- `role_ids`
- 其他用户字段

### 权限校验是如何接在 Token 之后的

Token 校验通过，只能证明“用户身份有效”，还不能证明“用户有权限”。

后续的授权流程是：

1. `require_permission(...)` 或 `require_any_permission(...)` 依赖先拿到 `current_user`
2. 若用户角色中包含管理员标识，则直接放行
3. 否则根据 `current_user["user_id"]` 读取用户角色
4. 根据角色聚合 `permission_ids`
5. 再把权限 ID 解析成权限码 `code`
6. 如果请求所需权限码不在集合中，则返回 `403 permission denied`

### 相关配置项

Token 创建与校验直接依赖这些配置：

- `JWT_SECRET_KEY`
  签名密钥
- `JWT_ALGORITHM`
  当前代码语义上使用 `HS256`
- `JWT_EXPIRE_MINUTES`
  过期时间
- `JWT_ISSUER`
  签发者校验
- `JWT_AUDIENCE`
  受众校验

### 修改认证链路时优先看哪里

- 改登录返回内容：`app/modules/auth/api/routes_login.py`
- 改 token 结构或签名逻辑：`app/shared/auth/jwt_auth.py`
- 改当前用户加载逻辑：`get_current_user()`
- 改权限校验规则：`require_permission()` / `require_any_permission()`

## 关键业务规则

- 权限码采用 `resource:action`
- 管理员判定由角色标识推导
- 用户有效权限来自角色权限聚合

## 常见修改场景

- 改登录或 token：看 `app/shared/auth/*`
- 改资源级权限逻辑：看 `auth/service/*`
- 改路由依赖：看 `auth/api/dependencies.py`

## 风险点

- `NavigationAccessService` 和 `NavigationPageService` 名称接近，修改时要先区分“页面 CRUD”还是“用户导航访问计算”
