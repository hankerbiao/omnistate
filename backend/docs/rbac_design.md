# 用户与权限管理模块设计方案（支持可编辑权限）

## 1. 目标
- 支持不同用户拥有不同权限
- ADMIN 具备编辑用户权限与角色的能力
- 权限模型与当前系统模块（workflow / test_specs / assets）可直接对齐
- 保持可扩展性（后续可增加项目级/资产级权限）

---

## 2. 核心概念
- **User（用户）**：系统登录主体
- **Role（角色）**：权限集合的抽象
- **Permission（权限）**：最小授权粒度（资源 + 动作）

---

## 3. 权限编码规范
采用 `资源:动作` 形式，示例：
- `requirements:read`
- `requirements:write`
- `test_cases:read`
- `test_cases:write`
- `assets:read`
- `assets:write`
- `work_items:read`
- `work_items:transition`

资源建议与现有模块对齐：
- `requirements`
- `test_cases`
- `assets`
- `work_items`

动作建议：
- `read`（查询/详情）
- `write`（创建/更新/删除）
- `transition`（工作流状态流转）

---

## 4. 数据模型设计

### 4.1 User
- `user_id`：唯一 ID
- `username`：用户名
- `email`：邮箱
- `role_ids`：关联角色列表
- `status`：ACTIVE / DISABLED
- `created_at`
- `updated_at`

### 4.2 Role
- `role_id`：唯一 ID
- `name`：角色名（ADMIN / TPM / TESTER / AUTOMATION）
- `permission_ids`：关联权限列表
- `created_at`
- `updated_at`

### 4.3 Permission
- `perm_id`：唯一 ID
- `code`：权限编码（如 `requirements:write`）
- `name`：权限名称
- `description`

---

## 5. ADMIN 权限编辑逻辑

### 5.1 权限定义
- ADMIN 默认拥有系统所有权限
- 额外具备：
  - 用户管理权限（增/改/禁用）
  - 角色管理权限（增/改）
  - 权限分配权限（为用户绑定/解绑角色）

建议权限码：
- `users:read`
- `users:write`
- `roles:read`
- `roles:write`
- `permissions:read`
- `permissions:write`

### 5.2 可编辑权限场景
1. **管理员编辑用户角色**
   - 修改 `User.role_ids`
2. **管理员编辑角色权限**
   - 修改 `Role.permission_ids`

---

## 6. API 设计（管理员可编辑权限）

### 6.1 用户管理
- `POST /api/v1/auth/users` 创建用户
- `GET /api/v1/auth/users` 用户列表
- `GET /api/v1/auth/users/{user_id}` 用户详情
- `PUT /api/v1/auth/users/{user_id}` 更新用户信息
- `PATCH /api/v1/auth/users/{user_id}/roles` 更新用户角色（ADMIN 专用）
- `PATCH /api/v1/auth/users/{user_id}/status` 启用/禁用用户（ADMIN 专用）

### 6.2 角色管理
- `POST /api/v1/auth/roles` 创建角色
- `GET /api/v1/auth/roles` 角色列表
- `GET /api/v1/auth/roles/{role_id}` 角色详情
- `PUT /api/v1/auth/roles/{role_id}` 更新角色
- `PATCH /api/v1/auth/roles/{role_id}/permissions` 更新角色权限（ADMIN 专用）

### 6.3 权限管理
- `POST /api/v1/auth/permissions` 创建权限
- `GET /api/v1/auth/permissions` 权限列表

---

## 7. 权限校验流程
1. 用户登录 → 获取 JWT
2. 请求进入 API
3. 从 JWT 解析 `user_id`
4. 查询 User → 角色 → 权限集合
5. 校验接口所需权限是否包含在集合中
6. 不满足则返回 403

---

## 8. 角色建议（适配当前系统）

### ADMIN
- 全部权限
- 可编辑用户/角色/权限

### TPM / PM
- `requirements:read/write`
- `test_cases:read`
- `work_items:read/transition`

### TESTER
- `test_cases:read/write`
- `requirements:read`
- `work_items:read/transition`

### AUTOMATION
- `test_cases:read/write`
- `assets:read`
- `work_items:read`

---

## 9. 扩展能力（可选）

### 9.1 项目级权限
增加 `project_id` 维度，定义用户在项目内的角色与权限。

### 9.2 资产级权限
增加 `asset_id` 维度，限制用户可操作的 DUT 或部件范围。

---

## 10. 落地步骤建议
1. 先实现全局角色权限（User-Role-Permission）
2. 将权限校验注入到已有 API（FastAPI 依赖）
3. 增加 ADMIN 编辑角色与用户权限接口
4. 后续按需扩展项目级/资产级权限
