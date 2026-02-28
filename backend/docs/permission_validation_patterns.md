# 权限校验设计模式（Permission Validation Patterns）

更新时间：2026-02-28

本文档用于沉淀后端权限校验的可复用模式，重点覆盖当前项目（FastAPI + RBAC + JWT）的实现方式与演进建议。

## 1. 目标

- 让授权行为可预测：同类接口采用同类权限策略。
- 让错误语义可观测：401/403/500 边界清晰。
- 让扩展可落地：从“接口级权限”平滑升级到“资源级策略”。

## 2. 术语

- 认证（Authentication）：确认“你是谁”，当前使用 JWT。
- 授权（Authorization）：确认“你能做什么”，当前使用 RBAC 权限码。
- 权限码：`资源:动作`，例如 `work_items:read`、`users:write`。

## 3. 模式清单

### 模式 A：认证前置（Authn-First）

- 设计：所有业务路由先做 token 校验，再进入权限判断。
- 现状实现：
  - `HTTPBearer` + `decode_token()` + `get_current_user()`
  - 代码：`app/shared/auth/jwt_auth.py`
- 优点：
  - 认证失败统一 401，阻断后续 DB 授权查询。

### 模式 B：单权限门（Single Permission Gate）

- 设计：接口依赖单个权限码，最常用于 CRUD。
- 示例：
  - `Depends(require_permission("assets:read"))`
  - `Depends(require_permission("requirements:write"))`
- 优点：
  - 规则直观，审计成本低。
- 适用：
  - 语义明确的一对一接口权限映射。

### 模式 C：任一权限门（Any-Of Permission Gate）

- 设计：接口接受多个可替代权限，只要命中其一即可。
- 现状实现：
  - `require_any_permission([...])`
  - 代码：`app/shared/auth/jwt_auth.py`
- 示例：
  - `/api/v1/auth/users` 允许 `users:read` 或 `work_items:read`。
- 优点：
  - 兼容跨角色协作场景，减少“角色过细导致接口不可用”。

### 模式 D：公开接口白名单（Public Endpoint Whitelist）

- 设计：少量接口不需要登录，如 `POST /auth/login`、`GET /health`。
- 约束：
  - 白名单必须最小化，禁止业务敏感接口进入白名单。

### 模式 E：仅登录门（Authenticated-Only Gate）

- 设计：不需要细粒度权限，但必须确认用户身份。
- 示例：
  - 用户自助改密、获取本人权限。
- 方式：
  - 依赖 `get_current_user`，不附加 `require_permission`。

### 模式 F：启动期权限基线（Bootstrap Baseline）

- 设计：通过初始化脚本写入默认权限和角色，避免环境漂移。
- 现状实现：
  - `app/init_mongodb.py`
  - `scripts/init_rbac.py`
- 关键点：
  - 权限表、角色表均采用 upsert，支持幂等执行。

### 模式 G：统一错误语义（Error Semantics）

- 设计：
  - 401：未认证/认证无效
  - 403：已认证但权限不足
  - 500：系统异常（不伪装成 400）
- 现状实现：
  - 全局异常处理器：`app/shared/api/errors/handlers.py`

### 模式 H：资源级授权扩展点（ABAC Hook，建议）

- 设计：在“接口级权限”通过后，再校验资源归属（owner/creator/team/state）。
- 推荐落点：
  - Service 层统一策略函数，如 `can_transition(user, item, action)`。
- 目的：
  - 防止“有功能权限即可操作任意资源”的越权风险。

## 4. 推荐分层策略

1. API 层：认证 + 粗粒度权限（`read/write/transition`）。
2. Service 层：资源级授权（归属、状态、租户、组织边界）。
3. Domain 层：业务状态机约束（动作是否合法、字段是否完整）。

这三层是互补关系，不建议只做其中一层。

## 5. 接口设计约定

- 约定 1：权限依赖写在路由声明上，不隐藏在函数体内部。
- 约定 2：对外暴露接口必须明确属于 `single` 还是 `any-of` 模式。
- 约定 3：新增接口必须在权限矩阵文档登记（同步维护 `backend/docs/authorization_design.md` 的第 6 章）。
- 约定 4：前端调用用户列表等基础数据接口前，需确认当前角色具备对应读权限。

## 6. 测试模式建议

- 认证测试：无 token -> 401。
- 授权测试：有 token 无权限 -> 403。
- 放行测试：有 token 且命中权限 -> 2xx。
- 任一权限测试：列表中任一权限命中即可通过。
- 回归测试：权限脚本更新后，关键页面初始化链路（如用户列表加载）必须覆盖。

## 7. 当前项目的最小实践清单

- 使用 `require_permission` 管理常规接口。
- 使用 `require_any_permission` 管理跨角色共享接口。
- 默认角色通过初始化脚本提供基础读权限（含 `users:read`）。
- 所有权限错误走统一 envelope，便于前端统一处理。

## 8. 演进路线（建议）

1. 引入资源级策略函数（先覆盖 workflow transition/reassign）。
2. 增加审计字段：`actor_id`、`effective_actor_id`、`request_id`。
3. 对高风险接口加“权限变更回归测试套件”。
4. 长期演进到策略中心（RBAC + ABAC 组合）。
