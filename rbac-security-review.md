# 身份校验与 RBAC 安全评审报告

> 评审对象：`dmlv4` 后端 `auth` 模块 + 共享鉴权层 + 各业务模块权限接入
> 评审范围：安全性设计、权限模型完整性与可扩展性、角色/权限分配逻辑、入口点覆盖、业务契合度与最佳实践
> 评审方式：只读代码审查 + 关键声明逐条核验（已对照 `config.yaml`、`ai_routes.py`、`agent_auth.py`、`router_registry.py` 等真实文件）

---

## 0. 结论速览

| 维度 | 评级 | 关键判断 |
|------|------|----------|
| 密码与哈希 | 🟢 良好 | PBKDF2-HMAC-SHA256 / 20万迭代 / 随机盐 / 常量时间比较 |
| JWT 实现 | 🟡 中等 | 手写 HS256，无 `jti`/刷新/吊销；secret 硬编码入库 |
| 密钥与凭据管理 | 🔴 高危 | `config.yaml` 提交真实 JWT/MinIO 密钥 |
| **AI 接口鉴权覆盖** | 🔴 高危 | `system_config/api/ai_routes.py` 与 `ai_analysis` 6+ 端点**无任何 auth 依赖** |
| 执行 Agent 机器鉴权 | 🔴 高危 | `agent_hmac_mode` 默认 `optional`，默认部署下 agent 可零签名冒充 |
| 横向越权（IDOR） | 🟠 中高 | 附件下载/项目只读/用例集 CRUD 仅登录、无对象级归属校验 |
| 全局防御纵深 | 🟡 中等 | 无全局认证中间件，完全依赖逐路由注入，漏加即公开 |
| CORS | 🟡 中等 | `cors_origins: ['*']` + `allow_credentials=True` |
| RBAC 模型完整性 | 🟢 良好 | 用户↔角色↔权限多对多、额外权限、管理员短路、导航授权闭环 |
| RBAC 可扩展性 | 🟡 中等 | 权限码硬编码在 init 脚本、扁平无层级、无集中注册表/枚举 |
| 测试覆盖 | 🟢 良好 | 登录/CRUD/权限强制/导航均有集成测试 |

**总体判断**：RBAC 的权限模型与分配逻辑设计合理、可用；但**身份校验的入口点覆盖存在明确高危缺口（AI 接口、Agent 机器鉴权），且密钥管理不合规**。这些属于"已实现功能被暴露"而非"模型缺陷"，修复优先级高于模型重构。

---

## 1. 安全性设计：是否存在漏洞

### 1.1 🔴 高危 — 密钥与凭据明文入库
- `backend/config.yaml:60` 提交真实 JWT `secret_key`：`fa5922eb…c23fe5dc`
- `backend/config.yaml:55` 提交 MinIO `secret_key: kk123123`；同文件另有 MongoDB/Redis/RabbitMQ 连接凭据
- 影响：攻击者一旦获取仓库读权限，即可**离线伪造任意用户 JWT**（HS256 对称密钥），且可直连存储/消息中间件。
- 建议：密钥移出仓库，改用环境变量/密钥管理服务（`DML_OPEN_PLATFORM_API_KEY_PEPPER` 已证明环境变量覆盖机制可用，应推广到 JWT/DB 凭据）。**立即轮换已暴露的密钥**。

### 1.2 🔴 高危 — AI 接口无认证（入口点缺失最严重）
核验 `backend/app/modules/system_config/api/ai_routes.py`：6 个端点（`/polish`、`/analyze-steps`、`/generate-cases`、`/review-case`、`/recommend-cases`）的 `@router.post` 定义中**无任何 `Depends(get_current_user)` / `require_permission`**（已逐行 grep 确认）。`ai_analysis/api/routes.py`（`/ai-analyze/collections/{id}`）同样无依赖。
- 影响：匿名请求可消耗外部 AI `api_key`（成本滥用），并读取/外传用例库与需求内容（数据泄露）。`recommend-cases` 无 `project_id` 限制时会遍历全库用例。
- 修复：在 router 或各端点加 `dependencies=[Depends(get_current_user)]`，并按业务加 `require_permission("system:config")` 或独立 `ai:use` 权限码。

### 1.3 🔴 高危 — 执行 Agent 机器鉴权默认失效
核验 `backend/app/shared/config/settings.py:156`：`agent_hmac_mode: Literal["optional","required"] = "optional"`（默认值）。
`backend/app/modules/execution/api/agent_auth.py:58-74`：当 `mode == "optional"` 且缺少认证头时，进入 **legacy 分支**——仅从 path/body 取 `agent_id`，**不做任何 HMAC 校验即放行**（`return legacy_agent_id`）。
- 影响：默认部署下，任意请求者可冒充任意 `agent_id` 注册/心跳/上报结果，**无机器身份认证**。
- 修复：默认改为 `"required"`；或移除 legacy 无签名回退，缺失签名即 401。

### 1.4 🟠 中高 — 横向越权（IDOR）
- 附件下载 `attachments/api/routes.py`：`get_current_user` 仅校验登录，**不校验 `file_id` 归属** → 任一登录用户可获取任意附件预签名 URL。
- 项目只读 `project/api/routes.py`：仅登录，无 `require_permission` → 任一登录用户可读全部项目。
- 用例集 CRUD `test_case_collection/api/routes.py`：仅登录，无权限/归属校验 → 任一登录用户可增删改任意集合。
- 修复：加对象级（同项目/同组织/创建者）归属校验，或至少 `require_permission(...)`。

### 1.5 🟡 中等 — 其它
- **用户枚举**：`authenticate_user` 用户不存在/禁用抛 `UserNotFoundError`→404，密码错→`ValueError`→401，攻击者可由状态码差异枚举账号。建议统一返回 401。
- **无登录限流/账户锁定**：无失败计数、无速率限制，存在暴力破解风险（PBKDF2 仅提升离线破解成本，不挡在线爆破）。
- **CORS 过宽**：`config.yaml:5-6` `cors_origins: ['*']` + `main.py` `allow_credentials=True` + `allow_methods/headers: ["*"]`，等效接受任意站点携带凭据的跨域请求。建议改为前端域名白名单。
- **JWT 无吊销/刷新/登出**：无 `jti`、无黑名单、无 refresh token；token 在 `exp`（默认 480 分钟）前始终有效，泄露无法即时作废。无 logout 端点。
- **无全局认证中间件**：`app/main.py` 仅挂 CORS + 请求日志 + 审计日志。鉴权完全靠逐路由注入，任何路由漏加依赖即对外公开（§1.2 即实例）。建议增加路由级默认依赖或全局中间件作纵深防御。
- **死配置/死引用**：`settings.py:52-53` `dev_bypass_auth`/`dev_user_id` 仅定义未接线（当前无旁路风险，但属隐患）；`router_registry.py` 对不存在的 `open_platform` 模块用 `try/except ImportError` 静默跳过（注：当前 checkout 中 `open_platform`、`terminal` 模块均不存在，已 `ls` 核验，本次不影响风险面，但应清理该死引用）。

### 1.6 🟢 良好 — 已做对的部分
- **密码哈希**：`shared/auth/password.py` PBKDF2-HMAC-SHA256、20万迭代、每用户随机盐 `os.urandom(16)`、校验用 `hmac.compare_digest` 常量时间比较。
- **JWT 签名比对**：`jwt_auth.py` 用 `hmac.compare_digest` 常量时间比较；且**忽略 header 中的 `alg` 字段**、始终以 HMAC-SHA256 重算，天然免疫 `alg:none` 与算法混淆攻击（建议仍显式断言 `alg == "HS256"`）。
- **日志/审计脱敏**：`shared/security/redaction.py` 覆盖 password/secret/token/authorization 等字段；`RequestLoggingMiddleware`、`AuditLogMiddleware` 对 `/login`、`/password`、`/token` 等路径直接脱敏或不记 body。**密码与 token 不会以明文进入日志**。

---

## 2. 权限模型：是否完整且可扩展

### 结构（核验 `auth/repository/models/rbac.py`）
- `UserDoc`：`role_ids: List[str]`（用户→角色，多对多嵌入）+ `extra_permission_ids: List[str]`（用户级额外权限）+ `allowed_nav_views`（用户级导航覆盖）+ `status`。
- `RoleDoc`：`permission_ids: List[str]`（角色→权限，多对多嵌入）+ `is_system`（系统角色不可删）。
- `PermissionDoc`：`code`（如 `requirements:read`）、`name`、`description`，唯一索引 `perm_id`/`code`。
- 关联方式：嵌入 ID 列表，**无中间表**，解析时 `User→Role→Permission` 双向查库。

### 完整性：🟢 良好
- 支持用户多角色、角色多权限、用户额外权限并集、管理员短路、用户级导航覆盖、系统角色保护——覆盖典型 RBAC 需求。
- 权限判定 `get_user_permissions` = 角色权限 ∪ 额外权限（`jwt_auth.py:156-163`），`is_admin_role` 短路放行（`jwt_auth.py:206-207`）。
- 导航授权闭环：后端 `/users/me/navigation` + 前端 `config/navigation.ts` 的 `permission` 字段 ≡ 后端 `PermissionDoc.code`，前端经 `/users/me/permissions` 下发权限数组做 `includes` 过滤。

### 可扩展性：🟡 中等（受限点）
1. **权限码无集中注册表/枚举**：权限码硬编码在 `scripts/init/init_rbac.py` 的 `DEFAULT_PERMISSIONS`（约 32 个），运行时各模块直接用字符串字面量（如 `require_permission("requirements:read")`）。新增/改名权限码无编译期检查，易拼写漂移。
2. **扁平无层级**：无角色继承/父子关系（`inherit/parent_role` 全仓无匹配）。多角色仅做权限并集，无法表达"角色 A 继承角色 B"。当前 8 个系统角色够用，但业务扩张后维护成本高。
3. **仅 Allow 模型**：`extra_permission_ids` 只能追加，无 Deny/黑名单概念。若需"授予角色但排除某敏感操作"需绕道。
4. **无权限分组/通配**：权限按 `资源:动作` 单码管理，无法批量授予（如 `requirements:*`）。

---

## 3. 角色与权限分配逻辑：是否清晰

### 分配入口（核验路由 + 脚本）
- 用户→角色：`PATCH /users/{id}/roles`（`routes_users.py:97`）、`scripts/init/create_user.py --roles`（CLI）。
- 角色→权限：`PATCH /roles/{id}/permissions`（**整体替换**，`routes_roles.py:71`）、`init_rbac.py` 预置。
- 用户额外权限：`PUT /users/{id}/permissions/extra`（`routes_users.py:129`）。
- 创建角色/权限时 `_ensure_permissions_exist`/`_ensure_roles_exist`（`support.py`）校验引用 ID 存在。

### 清晰度：🟢 良好
- 管理员操作均 `require_admin_user`/`users:write` 保护，权限校验与业务路由一致。
- `UserService.get_effective_permissions` 返回 `role_permissions`/`extra_permissions`/`permissions` 三段（带来源），便于审计与调试。
- "最后一个 ADMIN" 受保护（`delete_user` 禁止删除自己、禁止非 ADMIN 删最后一个 ADMIN）。
- 初始化脚本幂等（`upsert`、`is_system` 不被覆盖），可重复执行。

### 注意点
- 角色权限更新是**整体替换**而非增量——调用方需先拉全量再合并，易误覆盖（应提供增量 add/remove 接口或文档明确）。
- 两套 403 机制并存：`require_permission` 直接 `raise HTTPException(403)`，领域服务用 `PermissionDeniedError`（统一 handler → 403）。终点一致但风格不统一，建议收敛到领域异常。

---

## 4. 身份校验流程：是否覆盖所有关键入口点

### 已覆盖（✅）
- `/auth/login` 是唯一公开端点；其余 `auth` 体系（`users`/`roles`/`permissions`/`navigation`）全部 `require_permission`/`require_admin_user`。
- system_config 配置面、redis 写操作、workflow/test_specs/execution_plan 业务写操作、部分 execution 人工面均显式 `require_permission`。
- health/llms.txt 等预期公开，合理。

### 未覆盖 / 薄弱（见 §1.2–§1.4）
1. 🔴 `system_config/api/ai_routes.py` 5 端点 + `ai_analysis/api/routes.py` 1+ 端点 —— **完全匿名可达**。
2. 🔴 `execution` agent 注册/心跳 —— 默认 optional 模式零签名放行。
3. 🟠 附件下载 / 项目只读 / 用例集 CRUD —— 仅登录、无对象级授权（IDOR）。
4. 🟡 `enums` 端点公开（仅常量，低风险）。

### 前端侧
- `App.tsx` 路由守卫仅检查 `localStorage` 中 `jwt_token` 是否存在（`AuthProvider`），**不校验有效性/过期**，可被绕过。这在"服务端严格鉴权"前提下是可接受的 UX 层；真正风险在服务端缺口（§4.1–§4.3）。
- `LoginPage` 将账号密码存入 `localStorage`（默认 `admin`/`Test@123`），`TerminalPage` 将 token 写入 websocket URL —— 内网可控环境可接受，但属凭据落盘风险。

**结论**：身份校验在"已接线路由"上覆盖良好，但**存在匿名可达的高危入口（AI 接口）与默认失效的机器鉴权（Agent）**，且缺少全局兜底机制，整体入口点覆盖不达标。

---

## 5. RBAC 实现与业务需求/最佳实践的契合度

### 契合点（🟢）
- 权限码采用 `资源:动作` 约定，与"测试用例编写需求/用例/执行任务/工作项/系统配置/导航/用户/角色/权限"等业务域一一对应，语义清晰。
- 管理员短路 + 最后一个 ADMIN 保护，符合最小权限与防锁死原则。
- 导航授权前后端用同一 `code` 闭环，避免前后端权限语义漂移。
- 集成测试覆盖登录、CRUD、权限强制、导航过滤（含"无角色用户 → 403""无效 token → 401""ADMIN 全放行"等），质量可靠。

### 偏离最佳实践（🟡）
- 手写 JWT 而非 PyJWT/python-jose（功能正确但维护性与审计性弱）。
- 密码策略偏弱：仅 `min_length=6`，无复杂度/历史约束。
- 无 token 生命周期管理（吊销/刷新/登出）。
- 无登录防护（限流/锁定）。
- 无全局鉴权中间件（依赖逐路由，易遗漏）。
- 权限码缺枚举注册表（靠字符串字面量，易错）。
- 角色扁平无层级（业务扩张后维护成本）。

---

## 6. 潜在风险分级与改进建议

### P0 — 立即处理（高危，可远程利用）
1. **轮换并移除仓库中的真实密钥**：JWT `secret_key`、MinIO `secret_key` 及 DB/中间件凭据移出 `config.yaml`，改环境变量/密钥管理；已暴露密钥立即轮换。
2. **为 AI 接口加鉴权**：`ai_routes.py`、`ai_analysis/api/routes.py` 加 `get_current_user`（建议加 `system:config` 或 `ai:use` 权限）。
3. **收紧 Agent 机器鉴权**：`agent_hmac_mode` 默认改为 `required`，或删除 legacy 无签名回退。

### P1 — 近期处理（中高，需结合业务确认）
4. **对象级授权（防 IDOR）**：附件下载校验归属、项目/用例集按组织/创建者隔离或加 `require_permission`。
5. **Token 生命周期管理**：引入 `jti` + Redis 黑名单（或短 `exp` + refresh token），提供 logout 端点。
6. **登录限流/账户锁定**：Redis 计数器，失败 N 次锁定 M 分钟。
7. **收紧 CORS**：`cors_origins` 改为前端域名白名单。
8. **修复用户枚举**：登录失败统一 401。
9. **强化密码策略**：提高最小长度、加复杂度/历史约束（PBKDF2 可保留，或迁移 argon2id）。

### P2 — 架构优化（持续提升）
10. **全局鉴权中间件/路由默认依赖**：作为纵深防御，避免未来漏加依赖即公开。
11. **集中权限码注册表**：用枚举/常量类替代散落字符串字面量，新增即编译期校验。
12. **清理死代码**：移除 `dev_bypass_auth`/`dev_user_id` 死配置与 `router_registry` 对不存在 `open_platform` 的死引用。
13. **统一 403 机制**：`require_permission` 改抛 `PermissionDeniedError`，与领域服务一致。
14. **可扩展性增强**（按需）：角色继承/层级、权限分组通配（`resource:*`）、Deny 权限。
15. **前端启动期 token 校验**：`AuthProvider` 初始化时调 `/users/me` 验活，过期/失效即跳登录。

---

## 附：关键证据文件

| 关注点 | 路径 |
|--------|------|
| 密钥硬编码 | `backend/config.yaml:55,60` |
| AI 接口无鉴权 | `backend/app/modules/system_config/api/ai_routes.py:40,94,201,321,431` |
| Agent 默认无签名 | `backend/app/shared/config/settings.py:156`；`backend/app/modules/execution/api/agent_auth.py:58-74` |
| JWT 手写实现 | `backend/app/shared/auth/jwt_auth.py` |
| 密码哈希 | `backend/app/shared/auth/password.py` |
| RBAC 数据模型 | `backend/app/modules/auth/repository/models/rbac.py` |
| 鉴权依赖 | `backend/app/shared/auth/jwt_auth.py:109-215`；`backend/app/modules/auth/api/dependencies.py` |
| 权限码注册 | `backend/scripts/init/init_rbac.py`（`DEFAULT_PERMISSIONS`/`DEFAULT_ROLES`） |
| 导航授权闭环 | `backend/app/modules/auth/api/routes_login.py:69` + `frontend/src/config/navigation.ts` |
| 中间件挂载 | `backend/app/main.py:147-156` |
| CORS 配置 | `backend/config.yaml:5-6` |
