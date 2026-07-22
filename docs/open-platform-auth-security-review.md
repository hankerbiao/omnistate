# DML v4 开放平台 — 主后端鉴权安全评审与网关引入改动清单

> 评审人：高见远（架构师 / software-architect）
> 性质：**安全评审（聚焦主后端鉴权）** —— 既评现状合理性，也给出「引入统一身份轻量网关」时后端需改什么。非实现，不含代码。
> 依据：直接读取实际源码并引行号（路径相对 `backend/`）。

## 0. 重要前提订正（先说清楚，避免误判）

| 原假定（来自上游） | 实际代码核查结论 |
|---|---|
| `backend/app/shared/security/signing.py` 存在 Execution Agent HMAC-SHA256 + Nonce 防重放，可作网关身份头参考实现 | **不存在**。全仓 `backend/app` 搜索 `nonce`/`Nonce` **零命中**；`security/` 下只有 `client_ip.py`、`redaction.py`。所谓「HMAC-Nonce 防重放」在当前 FastAPI 代码库中**并未落地**（仅 Kafka Worker 心跳用 `agent_id` 字符串，无密码学校验）。因此「复用 HMAC-Nonce 思路」需**新建**，而非复用。 |
| MCP 走 `backend_token` 静态令牌 | 属实，但 `backend_token` 以 `Bearer` 发往后端（`client.py:24-25`），后端按普通 JWT 解码 → 它本质是**带 8h 过期、无刷新**的 JWT（`config.yaml:60` 的 `secret_key` 签发，`expire_minutes:480`）。若 MCP 进程存活超 8h 且不重启，会**静默失效**。 |

---

## 1. 现状鉴权实现合理性逐条评审（含风险等级）

### 1.1 JWT 鉴权（`app/shared/auth/jwt_auth.py`）

| 评审点 | 行号 | 现状 | 判定 | 风险 |
|---|---|---|---|---|
| 算法是否硬编码 HS256 | `create_access_token` L44（header `alg:"HS256"`）；`settings.py:142` `algorithm="HS256"` | 硬编码 HS256，对称密钥 | 合理 | 低 |
| 算法混淆(alg confusion)防护 | `decode_token` L63-70 | **完全忽略 header 中的 `alg`**，始终用 `_sign_hs256(secret_key, HS256)` 重算并 `hmac.compare_digest` 比对（L69）。攻击者改 `alg:none` 或 `RS256` 均无法绕过（签名仍按 HS256 校验） | **天然免疫**（因自研实现不信任 header.alg） | 低（但见下） |
| 自研 vs 标准库 | 整个文件 | 手搓 JWT（base64url + HMAC），未用 PyJWT/python-jose | 功能可用，但**非标准库**，可维护性/演进风险 | 中 |
| secret 来源与强度 | `config.yaml:60` `secret_key: fa5922…5dc`（64 hex = 256bit）；`settings.py:141` 默认 `"CHANGE_ME"` | 实际已覆盖为 256bit 随机值，强度足够；但**明文写在仓库 config.yaml 中** | 强度 OK；**密钥管理不合规** | 中-高（明文入库） |
| exp 校验 | L89-94 | `now_ts >= exp_ts` → 401 | 正确 | 低 |
| iss 校验 | L96 | `payload.iss != _jwt.issuer` → 401 | 正确 | 低 |
| aud 校验 | L98 | `payload.aud != _jwt.audience` → 401 | 正确 | 低 |
| nbf / jti / typ 校验 | — | 无 nbf、无 jti、未强制 typ | 缺失但不致命 | 低 |
| 令牌可吊销 | — | **无** jti、无 denylist、无服务端会话；只能等 exp | 不可吊销 | 中-高 |
| refresh / logout | `routes_login.py:21-30` | 仅发 `access_token`，**无 refresh、无 logout/黑名单** | 缺撤销能力 | 中 |
| 签名比较 | L69 | `hmac.compare_digest`（常量时间） | 正确 | 低 |
| 用户状态实时校验 | `get_current_user` L131-133 | 每请求 `UserDoc.find_one` + `status != "ACTIVE"` → 401 | 良好（禁用即时生效） | 低 |
| 操作上下文注入 | L139-143 | `set_operation_context(user_id, username, role_ids)` 供审计 | 仅 JWT 用户有；机器用户需补 | 低（接网关时需补） |

**小结**：JWT 本身**设计与实现基本合理**（alg 混淆恰好因自研实现而免疫，exp/iss/aud 齐全，常量时间比较）。主要短板是**可吊销性缺失**（无 jti/黑名单）与**密钥明文入库**。自研 JWT 属中风险（建议后续换 PyJWT，但非网关阻塞项）。

### 1.2 密码处理（`app/shared/auth/password.py` + `modules/auth/service/user_service.py`）

| 评审点 | 行号 | 现状 | 判定 | 风险 |
|---|---|---|---|---|
| 哈希算法 | `password.py:12,22-28` | **PBKDF2-HMAC-SHA256**，迭代 200,000，盐 16B，输出 32B | 可用，但非当前 OWASP 首选（Argon2id）；200k 偏低（2023 建议 ≥600k） | 低-中 |
| 每用户盐 | `password.py:21,27-29` | 随机盐 + base64 存储 | 正确 | 低 |
| 校验比较 | `password.py:43` | `hmac.compare_digest` | 常量时间 | 低 |
| 登录失败/暴力破解防护 | `user_service.authenticate_user:34-40`；`routes_login.py:21-30` | **无**失败计数、无锁定、无速率限制、无验证码、无 `sleep`；仅 `ValueError→401` | **完全缺失** | **高** |
| 密码强度策略 | — | 注册/改密处未见强度校验（未在本次范围深查，建议补） | 未知/缺失 | 中 |

**小结**：哈希本身合格（PBKDF2+盐），但**无暴力破解防护**是明确的高风险点，对外暴露前必须加（网关层或登录路由层限流+锁定）。

### 1.3 MCP 鉴权（`app/mcp_server/config.py` + `client.py` + `server.py`）

| 评审点 | 行号 | 现状 | 判定 | 风险 |
|---|---|---|---|---|
| 静态密钥管理 | `config.py:19`（默认 `""`）、`config.py:49`（env `DML_MCP_BACKEND_TOKEN`）、`client.py:24-25` | 静态 Bearer 令牌，env 注入，无轮换/无过期管理 | 可接受（内部） | 中 |
| 远程暴露限制 | `config.py:41-45,57-64` | streamable-http **仅允许 loopback**（`_is_loopback_host`），否则启动报错；stdio 默认无网络 | 设计良好（注释明确要求远程前配 MCP 认证） | 低 |
| 令牌有效期/刷新 | 同上 | 实为 8h JWT（`expire_minutes:480`），MCP 客户端**无刷新逻辑** | 进程长活超 8h 会静默失败 | 中（可用性） |

**小结**：MCP 的 loopback 限制设计正确；风险在于它是**无刷新静态 JWT**，长活即失效，且若未来远程暴露需独立鉴权。

### 1.4 CORS 与中间件（`app/main.py` + `app/shared/config/settings.py` + `app/shared/security/client_ip.py`）

| 评审点 | 行号 | 现状 | 判定 | 风险 |
|---|---|---|---|---|
| CORS 来源 | `main.py:149`（取 `app.cors_origins`）；`settings.py:50` 默认 `["*"]`；`config.yaml:5-6` 实际 `['*']` | **通配 `*`** | 不合理（对外暴露时） | **高** |
| CORS 凭证 | `main.py:150` `allow_credentials=True` + `allow_origins=['*']` | 凭据型通配 → 任意站点可发起带凭据跨域请求（Starlette 会回显 Origin） | **高危配置** | **高** |
| CORS 方法/头 | `main.py:151-152` `methods/headers=['*']` | 全开 | 暴露面过大 | 中 |
| ProxyHeadersMiddleware | `main.py:147-156` | **未启用** `ProxyHeadersMiddleware` | 当前安全（不信任 XFF）；但接网关后需启用以正确识别对等端 | 中（接网关时） |
| trusted_proxies | `settings.py:51` 默认 `[]`；`config.yaml` 未设 → 空 | 空 | 当前 `get_client_ip` 直接返回直连 IP（安全）；接网关时需配置 | 中（接网关时） |
| XFF 信任逻辑 | `client_ip.py:12-42` | `_is_trusted` 按 `trusted_proxies` 判定；不可信时忽略 XFF | 逻辑正确、默认安全 | 低 |
| 审计/追踪中间件 | `main.py:155-156` `RequestLoggingMiddleware`+`AuditLogMiddleware` | 已启用，注入 trace/operation 上下文 | 良好（但仅 JWT 用户被 `set_operation_context`） | 低 |

**小结**：当前 `trusted_proxies` 为空 + 未启用 `ProxyHeadersMiddleware` 在「无网关」时反而安全（不盲信 XFF）；但 `CORS='*' + credentials` 是**现网已有的高危配置**，无论是否上网关都应收紧。接网关后需启用 `ProxyHeadersMiddleware` 并配置 `trusted_proxies=[网关 CIDR]`。

### 1.5 其他

| 评审点 | 行号 | 现状 | 判定 | 风险 |
|---|---|---|---|---|
| `dev_bypass_auth` 开发绕权 | `settings.py:52-53`（默认 False）；`app.log:2302` 显示已从默认配置移除 | 死配置（代码未引用），默认 False | 当前无害，但属潜伏风险 | 低 |
| 仓库明文密钥 | `config.yaml:14,55,60,85` | RabbitMQ/MinIO/Redis/JWT 密钥均明文入库 | 严重密钥管理问题（对外暴露前必须迁移） | 中-高 |

---

## 2. 网关引入后：后端鉴权改动清单

既定方向：open-platform/backend 扩为网关（保留 MCP）；主后端仅加 `trust_gateway_identity` + 配 `trusted_proxies` + 收紧 CORS。

### 2.1 设计结论（先定方向，再列改动）

**(a) `trust_gateway_identity` 怎么写**
- 新增依赖（建议放 `app/shared/auth/jwt_auth.py` 或新建 `app/shared/auth/gateway_auth.py`）。
- 两步校验：① **来源校验**——`request.client.host`（启用 `ProxyHeadersMiddleware` 后取受信 XFF）必须 ∈ `trusted_proxies`（网关 CIDR）；② **签名校验**——解析并验证 `X-Open-Identity` 头（HMAC-SHA256，专用 `gateway_shared_secret`）。
- 解析出 `developer_id / organization / scopes / service_account_user_id`，调用 `set_operation_context(...)` 写入审计上下文（补 1.1 缺口：机器用户目前不写上下文）。
- 返回「机器用户」dict（含 `user_id=service_account_user_id`、`role_ids`、并标 `is_machine=True`），使下游 `require_permission` 可复用。
- **推荐映射方式**：网关把 API-Key 解析为**一个已存在的 service-account（UserDoc，状态 ACTIVE，绑定角色）的 user_id**，后端 `trust_gateway_identity` 直接返回该 user_id → **完全复用现有 RBAC，零改动 `require_any_permission`**。不要改成「注入 scopes 再改 RBAC」，避免动到人类路由的鉴权核心。

**(b) 身份头防伪造（含前提订正）**
- 上游假定「复用 HMAC-Nonce」——**但 HMAC-Nonce 代码不存在**，需新建。
- 方案：新增 `app/shared/security/signing.py`（当前缺失），提供 `sign_identity` / `verify_identity`：用 HMAC-SHA256（可复用 `jwt_auth.py:29-31` 的 `_sign_hs256` 思路）对 `developer_id|org_id|scopes|iat|nonce` 签名；`verify_identity` 验签名 + 验 `iat` 时间窗（如 ±5min 防过期重放）+ 查 nonce 去重。
- **nonce 存储**：用**现有 Redis**（`settings.py:194-208` 已配）存 `{nonce: expire_at}`，TTL 短（如 5–10min），实现防重放。**这是新增基础设施，但 Redis 已就绪**。
- 结论：网关→后端身份头 = 「HMAC-SHA256 + 时间戳 + Redis nonce 去重」，密钥为**独立**的 `gateway_shared_secret`（不要复用 JWT `secret_key`，缩小爆炸半径）。

**(c) CORS 收紧到什么范围**
- `config.yaml` 的 `app.cors_origins` 从 `['*']` 改为**显式来源清单**：主前端源（如 `http://localhost:5173` 或生产域名）+ 开发者门户源（`open-platform/frontend` :3100）+ 网关自身管理面（若网关也有浏览器管理 UI）。
- `allow_credentials=True` 仅在与**非 `*` 的显式源**配合时才安全（Starlette 对显式源不会回显 `*`）。
- `allow_methods` / `allow_headers` 由 `['*']` 收敛为实际所需（`GET,POST,PUT,DELETE` + 必要头）。**必须**。

**(d) `trusted_proxies` 与 `ProxyHeadersMiddleware`**
- 启用 `ProxyHeadersMiddleware`（`from uvicorn.middleware.proxy_headers`），并将 `app.trusted_proxies` 设为网关 CIDR（如 `["10.x.x.x/32", "127.0.0.1"]`）。
- 作用：让 `request.client` 在「网关前还有 nginx 等反代」时正确回退到受信 XFF；同时 `trust_gateway_identity` 的来源校验依赖它。
- 若部署上**后端端口仅网关可达**（网络隔离），来源校验可简化，但签名校验仍是主控制；IP 绑定作 defense-in-depth。**建议（非绝对必须，取决于拓扑）**。

**(e) 网关自身调主后端用什么凭证（backend_token 还是 JWT？）**
- **不要用 MCP 的静态 `backend_token`**（它是 8h 无刷新 JWT，长活即失效，见 1.3）。
- **推荐**：网关对每个发往后端的请求，**自行用 `gateway_shared_secret` 签署 `X-Open-Identity` 头**（机器对机器，无需过期，靠 nonce+时间戳防重放）。后端 `trust_gateway_identity` 验之。人类开发者登录门户仍走**现有 `/login` JWT**，不变（见下）。

**(f) 现有 JWT / 人类登录是否要改**
- **不改**。`/login`（`routes_login.py:21-30`）、`get_current_user`、`require_permission` 全部保留。
- 区别仅在于：人类浏览器请求带 `Authorization: Bearer <JWT>` → `get_current_user`；网关转发/代理的机器请求带 `X-Open-Identity` → `trust_gateway_identity`。两套身份来源在 RBAC 层汇合（service-account 映射法下 `require_permission` 无感）。

**(g) 是否要补：API-Key 哈希存储 / 开发者 secret 管理 / 密钥存放**
- **API-Key 哈希存储**：属**网关侧（open-platform/backend）+ 其 MongoDB**，主后端不存 API-Key。但主后端需定义信任契约（头名、签名方案、secret 来源）。API-Key 落地时**必须哈希存储**（SHA-256 或 HMAC+pepper），原文仅创建时展示一次，支持轮换/吊销。**必须（做 API-Key 功能时）**。
- **开发者 secret 管理**：`gateway_shared_secret` 与任何开发者密钥**通过 env / 密钥管理器注入，绝不写 config.yaml**（当前 `config.yaml` 已明文提交 JWT 等密钥，是反面教材，见 1.5）。**必须**。
- **密钥存放位置**：env 或 K8s Secret / Vault；主后端与网关共享 `gateway_shared_secret`（或各自持有，后端只验）。主后端 `jwt.secret_key` 同样应迁移出 config.yaml。**必须（公开暴露前）**。

### 2.2 后端鉴权改动清单（文件 / 改动点 / 是否必须 / 风险）

| # | 文件 | 改动点 | 是否必须 | 风险 |
|---|------|--------|---------|------|
| C1 | `app/shared/auth/jwt_auth.py`（或新建 `gateway_auth.py`） | 新增 `trust_gateway_identity` 依赖：来源校验（∈ trusted_proxies）+ `X-Open-Identity` 签名校验 + `set_operation_context` + 返回机器用户 dict（映射 service-account user_id） | **必须** | 中（动鉴权核心，需回归测试） |
| C2 | `app/shared/config/settings.py` | 新增 `OpenPlatformConfig`：`gateway_shared_secret`、`identity_header_name`、`trusted_gateway_cidrs`；`app.trusted_proxies` 改为可配网关 CIDR | **必须** | 低 |
| C3 | `app/main.py` | 收紧 CORS（`cors_origins` 显式源；`allow_methods/headers` 收敛）；启用 `ProxyHeadersMiddleware` | CORS 收紧=**必须**；ProxyHeaders=建议（依拓扑） | 低-中 |
| C4 | `app/shared/security/signing.py`（**新建**） | 实现 `sign_identity`/`verify_identity`（HMAC-SHA256 + iat 时间窗 + Redis nonce 去重）；复用 `_sign_hs256` 思路 | **必须** | 中（新密码学代码） |
| C5 | `app/shared/security/client_ip.py` | 若启用 `ProxyHeadersMiddleware`，确认 `get_client_ip` 与 `trust_gateway_identity` 来源判定一致（都用 `trusted_proxies`） | 建议（与 C3 联动） | 低 |
| C6 | `app/modules/auth/api/routes_login.py` + `user_service.py` | （可选，非网关阻塞）补登录限流/失败锁定，缓解 1.2「高」风险 | 建议（对外暴露前必须） | 中 |
| C7 | `app/shared/config/settings.py` + `config.yaml` | `jwt.secret_key` 及 RabbitMQ/MinIO/Redis 密钥**迁移出 config.yaml** 至 env/密钥管理器 | **必须（公开暴露前）** | 中-高 |
| C8 | `app/mcp_server/client.py` | 若长期保留 MCP→后端调用，为 `backend_token` 增加**刷新/重签发**逻辑（避免 8h 静默失效）；或统一改用 `X-Open-Identity` 签名头 | 建议 | 中（可用性） |
| C9 | 网关侧（open-platform/backend，本次不改动主后端） | API-Key 哈希存储、开发者 secret 管理、密钥存放；与后端约定信任契约 | **必须（做 API-Key 时）** | 中（但不在本仓库主后端） |

> 说明：C1 采用「service-account 映射」后，**`require_permission` / `require_any_permission`（`jwt_auth.py:192-215`）无需改动**，把对鉴权核心的回归风险降到最低。若改走「注入 scopes 改 RBAC」则需动 C1+RBAC，风险升为中-高，不推荐。

---

## 3. 高优先级 Must-Fix（对外暴露前）

1. **CORS `*` + credentials（高）**：`config.yaml:5-6` + `main.py:149-150` 必须收紧，否则任何网站可发起带凭据跨域请求。
2. **登录无暴力破解防护（高）**：`user_service.py:34-40` 无锁定/限流，对外前必须补（C6）。
3. **仓库明文密钥（中-高）**：`config.yaml:14,55,60,85` 全部明文，公开前迁 env/密钥管理器（C7）。
4. **令牌不可吊销（中-高）**：无 jti/黑名单，泄露后只能等 8h 过期；开放平台场景下建议补 denylist（可放在网关侧按 API-Key 吊销，比改 JWT 更轻）。
5. **网关身份头防伪造（中）**：新建 `signing.py`（C4）+ 独立 `gateway_shared_secret`；不要复用不存在的「HMAC-Nonce」。

---

## 4. 评审结论速览

- **现状是否合理**：JWT 设计基本合理（alg 混淆因自研实现天然免疫，exp/iss/aud 齐全）；密码哈希合格（PBKDF2+盐）；MCP loopback 限制正确。**高风险点**仅两个——**CORS 通配+凭据**、**登录无暴力破解防护**；**中高风险**为密钥明文入库、令牌不可吊销、MCP 静态令牌无刷新。
- **前提订正**：上游所述 `signing.py`/HMAC-Nonce **不存在**，不能复用，需新建；MCP `backend_token` 实为 8h 无刷新 JWT。
- **网关引入后端改动**：核心只改 4 处——① 新增 `trust_gateway_identity`（映射 service-account，复用 RBAC）；② 新增 `signing.py`（HMAC 身份头 + Redis nonce）；③ 收紧 CORS + 配 `trusted_proxies` + 启用 `ProxyHeadersMiddleware`；④ 密钥迁 env。**人类登录/JWT 不改**，网关用签名 `X-Open-Identity` 调后端（不用 `backend_token`）。API-Key 哈希/开发者 secret 在网关侧落库。
- **总体判定**：既定「轻量网关」方向**对主后端侵入很小且风险可控**，但**现有两个高危配置必须先行修复**，`trust_gateway_identity` 与 `signing.py` 需配齐回归测试。
