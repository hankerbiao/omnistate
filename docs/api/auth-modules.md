# 认证授权 API

## 概述

认证授权模块提供基于RBAC（Role-Based Access Control）的用户、角色、权限管理功能，支持导航页面权限控制。

**基础路径**: `/api/v1/auth`

## 注意事项

- 用户相关接口需要 `users:read` 或 `users:write` 权限
- 角色相关接口需要 `roles:read` 或 `roles:write` 权限
- 权限相关接口需要 `permissions:read` 或 `permissions:write` 权限
- 管理员接口需要ADMIN角色

## 用户认证

### 数据模型

```typescript
interface UserDoc {
  user_id: string;             // 用户ID（主键）
  username: string;            // 用户名
  email: string;              // 邮箱
  phone: string;              // 电话
  full_name: string;          // 全名
  status: string;             // 用户状态
  role_ids: string[];         // 角色ID列表
  last_login: string;         // 最后登录时间
  password_hash: string;      // 密码哈希
  created_at: string;         // 创建时间
  updated_at: string;         // 更新时间
  created_by: string;         // 创建人
  is_deleted: boolean;        // 是否删除
}

interface LoginRequest {
  user_id: string;            // 用户ID或用户名
  password: string;           // 密码
}

interface LoginResponse {
  access_token: string;       // JWT访问令牌
  user: UserResponse;         // 用户信息
}

interface UserResponse {
  user_id: string;
  username: string;
  email: string;
  full_name: string;
  status: string;
  role_ids: string[];
  last_login: string;
}
```

### 用户登录

```http
POST /api/v1/auth/login
```

**请求体**:
```json
{
  "user_id": "admin",
  "password": "password123"
}
```

**字段说明**:
- `user_id` (string, required): 用户ID或用户名
- `password` (string, required): 密码

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "user_id": "admin",
      "username": "admin",
      "email": "admin@example.com",
      "full_name": "系统管理员",
      "status": "ACTIVE",
      "role_ids": ["ADMIN", "USER_MANAGER"],
      "last_login": "2026-03-03T11:42:00Z"
    }
  }
}
```

**使用说明**:
- 登录成功后返回JWT Token
- Token用于后续接口的身份认证
- Token通常有有效期限制（由系统配置决定）

## 用户管理

### 创建用户

```http
POST /api/v1/auth/users
```

**权限要求**: `users:write`

**请求体**:
```json
{
  "username": "john_doe",
  "email": "john.doe@example.com",
  "phone": "13800138000",
  "full_name": "约翰·道",
  "status": "ACTIVE",
  "role_ids": ["USER", "TESTER"],
  "password": "initial_password"
}
```

**字段说明**:
- `username` (string, required): 用户名，全局唯一
- `email` (string, required): 邮箱，全局唯一
- `phone` (string, optional): 电话号码
- `full_name` (string, required): 全名
- `status` (string, optional): 用户状态，默认ACTIVE
- `role_ids` (string[], required): 角色ID列表
- `password` (string, required): 初始密码

**用户状态值**:
- ACTIVE, INACTIVE, SUSPENDED, PENDING

### 获取用户详情

```http
GET /api/v1/auth/users/{user_id}
```

**权限要求**: `users:read` 或 `work_items:read`

**路径参数**:
- `user_id` (string, required): 用户ID

### 查询用户列表

```http
GET /api/v1/auth/users
```

**权限要求**: `users:read` 或 `work_items:read`

**查询参数**:
- `status` (string, optional): 按用户状态筛选
- `role_id` (string, optional): 按角色筛选
- `limit` (integer, optional): 返回数量限制 (1-200, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

### 更新用户信息

```http
PUT /api/v1/auth/users/{user_id}
```

**权限要求**: `users:write`

**路径参数**:
- `user_id` (string, required): 用户ID

**请求体**:
```json
{
  "email": "john.doe.new@example.com",
  "phone": "13900139000",
  "full_name": "约翰·道（更新）",
  "status": "ACTIVE"
}
```

**说明**: 仅更新请求中显式提交的字段

### 更新用户角色

```http
PATCH /api/v1/auth/users/{user_id}/roles
```

**权限要求**: `users:write`

**路径参数**:
- `user_id` (string, required): 用户ID

**请求体**:
```json
{
  "role_ids": ["USER", "TESTER", "REVIEWER"]
}
```

### 重置用户密码

```http
PATCH /api/v1/auth/users/{user_id}/password
```

**权限要求**: `users:write`

**路径参数**:
- `user_id` (string, required): 用户ID

**请求体**:
```json
{
  "new_password": "new_password_123"
}
```

### 用户自助修改密码

```http
POST /api/v1/auth/users/me/password
```

**认证**: 需要当前用户信息

**请求体**:
```json
{
  "old_password": "current_password",
  "new_password": "new_password_123"
}
```

### 获取当前用户权限

```http
GET /api/v1/auth/users/me/permissions
```

**认证**: 需要当前用户信息

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "user_id": "current_user",
    "roles": [
      {
        "role_id": "USER",
        "role_name": "普通用户",
        "permissions": ["work_items:read", "test_cases:read"]
      }
    ],
    "effective_permissions": ["work_items:read", "test_cases:read"],
    "navigation_access": ["req_list", "req_form", "case_form"]
  }
}
```

### 获取当前用户导航权限

```http
GET /api/v1/auth/users/me/navigation
```

**认证**: 需要当前用户信息

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "user_id": "current_user",
    "allowed_nav_views": [
      {
        "view": "req_list",
        "name": "需求列表",
        "permission_required": "requirements:read"
      },
      {
        "view": "case_form",
        "name": "创建用例",
        "permission_required": "test_cases:write"
      }
    ]
  }
}
```

## 角色管理

### 数据模型

```typescript
interface RoleDoc {
  role_id: string;            // 角色ID（主键）
  role_name: string;          // 角色名称
  description: string;        // 角色描述
  permission_ids: string[];   // 权限ID列表
  is_system_role: boolean;    // 是否系统角色
  created_at: string;         // 创建时间
  updated_at: string;         // 更新时间
  created_by: string;         // 创建人
  is_deleted: boolean;        // 是否删除
}

interface RoleResponse {
  role_id: string;
  role_name: string;
  description: string;
  permission_ids: string[];
  is_system_role: boolean;
  created_at: string;
  updated_at: string;
}
```

### 创建角色

```http
POST /api/v1/auth/roles
```

**权限要求**: `roles:write`

**请求体**:
```json
{
  "role_name": "测试工程师",
  "description": "负责测试用例执行和质量保证",
  "permission_ids": ["test_cases:read", "test_cases:write", "work_items:read"]
}
```

### 获取角色详情

```http
GET /api/v1/auth/roles/{role_id}
```

**权限要求**: `roles:read`

### 查询角色列表

```http
GET /api/v1/auth/roles
```

**权限要求**: `roles:read`

**查询参数**:
- `limit` (integer, optional): 返回数量限制 (1-200, 默认50)
- `offset` (integer, optional): 分页偏移 (默认0)

### 更新角色信息

```http
PUT /api/v1/auth/roles/{role_id}
```

**权限要求**: `roles:write`

**路径参数**:
- `role_id` (string, required): 角色ID

### 更新角色权限

```http
PATCH /api/v1/auth/roles/{role_id}/permissions
```

**权限要求**: `roles:write`

**路径参数**:
- `role_id` (string, required): 角色ID

**请求体**:
```json
{
  "permission_ids": ["test_cases:read", "test_cases:write", "test_cases:delete"]
}
```

## 权限管理

### 数据模型

```typescript
interface PermissionDoc {
  perm_id: string;            // 权限ID（主键）
  perm_name: string;          // 权限名称
  description: string;        // 权限描述
  resource: string;           // 资源
  action: string;             // 操作
  is_system_perm: boolean;    // 是否系统权限
  created_at: string;         // 创建时间
  updated_at: string;         // 更新时间
  created_by: string;         // 创建人
  is_deleted: boolean;        // 是否删除
}

interface PermissionResponse {
  perm_id: string;
  perm_name: string;
  description: string;
  resource: string;
  action: string;
  is_system_perm: boolean;
  created_at: string;
  updated_at: string;
}
```

### 创建权限

```http
POST /api/v1/auth/permissions
```

**权限要求**: `permissions:write`

**请求体**:
```json
{
  "perm_name": "执行测试任务",
  "description": "可以执行测试任务",
  "resource": "execution_tasks",
  "action": "execute"
}
```

### 获取权限详情

```http
GET /api/v1/auth/permissions/{perm_id}
```

**权限要求**: `permissions:read`

### 查询权限列表

```http
GET /api/v1/auth/permissions
```

**权限要求**: `permissions:read`

**查询参数**:
- `limit` (integer, optional): 返回数量限制 (1-200, 默认100)
- `offset` (integer, optional): 分页偏移 (默认0)

### 更新权限

```http
PUT /api/v1/auth/permissions/{perm_id}
```

**权限要求**: `permissions:write`

**路径参数**:
- `perm_id` (string, required): 权限ID

## 导航页面管理

### 数据模型

```typescript
interface NavigationPageDoc {
  view: string;               // 页面标识（主键）
  name: string;               // 页面名称
  description: string;        // 页面描述
  url_path: string;           // URL路径
  permission_required: string; // 所需权限
  is_active: boolean;         // 是否启用
  display_order: number;      // 显示顺序
  icon: string;               // 图标
  parent_view: string;        // 父页面
  created_at: string;         // 创建时间
  updated_at: string;         // 更新时间
  is_deleted: boolean;        // 是否删除
}

interface NavigationPageResponse {
  view: string;
  name: string;
  description: string;
  url_path: string;
  permission_required: string;
  is_active: boolean;
  display_order: number;
  icon: string;
  parent_view: string;
}

interface UserNavigationResponse {
  user_id: string;
  allowed_nav_views: NavigationPageResponse[];
}

interface UpdateUserNavigationRequest {
  allowed_nav_views: string[]; // 允许访问的页面标识列表
}
```

### 获取系统导航页面定义（管理员）

```http
GET /api/v1/admin/navigation/pages
```

**权限要求**: 管理员权限

**查询参数**:
- `include_inactive` (boolean, optional): 是否包含未启用页面，默认true

### 获取导航页面定义（管理员）

```http
GET /api/v1/admin/navigation/pages/{view}
```

**权限要求**: 管理员权限

### 创建导航页面（管理员）

```http
POST /api/v1/admin/navigation/pages
```

**权限要求**: 管理员权限

**请求体**:
```json
{
  "name": "测试执行监控",
  "description": "监控测试任务执行状态",
  "url_path": "/execution/monitor",
  "permission_required": "execution_tasks:read",
  "display_order": 30,
  "icon": "monitor",
  "parent_view": "execution"
}
```

### 更新导航页面（管理员）

```http
PUT /api/v1/admin/navigation/pages/{view}
```

**权限要求**: 管理员权限

### 删除导航页面（管理员）

```http
DELETE /api/v1/admin/navigation/pages/{view}
```

**权限要求**: 管理员权限

### 获取用户导航访问权限（管理员）

```http
GET /api/v1/admin/users/{user_id}/navigation
```

**权限要求**: 管理员权限

### 更新用户导航访问权限（管理员）

```http
PUT /api/v1/admin/users/{user_id}/navigation
```

**权限要求**: 管理员权限

**请求体**:
```json
{
  "allowed_nav_views": ["req_list", "req_form", "case_form", "case_list"]
}
```

## 权限系统说明

### 权限命名规范

权限采用 `resource:action` 的命名格式：

| 资源 | 操作 | 示例权限 |
|------|------|----------|
| work_items | read/write/transition/delete | work_items:read |
| requirements | read/write/delete | requirements:write |
| test_cases | read/write/delete | test_cases:read |
| assets | read/write/delete | assets:write |
| execution_tasks | read/write/execute | execution_tasks:read |
| users | read/write | users:read |
| roles | read/write | roles:write |
| permissions | read/write | permissions:read |

### 内置角色

| 角色ID | 角色名称 | 描述 |
|--------|----------|------|
| ADMIN | 系统管理员 | 拥有所有权限 |
| USER_MANAGER | 用户管理员 | 管理用户和角色 |
| TEST_MANAGER | 测试经理 | 管理测试相关功能 |
| REVIEWER | 审核员 | 负责审核工作 |
| TESTER | 测试工程师 | 执行测试工作 |
| VIEWER | 观察者 | 仅查看权限 |

### 内置权限

系统预定义的权限包括：
- `users:read`, `users:write`
- `roles:read`, `roles:write`
- `permissions:read`, `permissions:write`
- `work_items:read`, `work_items:write`, `work_items:transition`
- `requirements:read`, `requirements:write`, `requirements:delete`
- `test_cases:read`, `test_cases:write`, `test_cases:delete`
- `assets:read`, `assets:write`, `assets:delete`
- `execution_tasks:read`, `execution_tasks:write`, `execution_tasks:execute`

## 使用示例

### 用户登录和权限获取

```bash
# 1. 用户登录
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "admin",
    "password": "password123"
  }'

# 2. 获取当前用户权限（需要Token）
curl -X GET "http://localhost:8000/api/v1/auth/users/me/permissions" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 获取当前用户导航权限
curl -X GET "http://localhost:8000/api/v1/auth/users/me/navigation" \
  -H "Authorization: Bearer your_jwt_token"
```

### 用户管理

```bash
# 1. 创建用户
curl -X POST "http://localhost:8000/api/v1/auth/users" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "email": "test@example.com",
    "full_name": "测试用户",
    "role_ids": ["TESTER"]
  }'

# 2. 查询用户列表
curl -X GET "http://localhost:8000/api/v1/auth/users?status=ACTIVE&limit=10" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 更新用户角色
curl -X PATCH "http://localhost:8000/api/v1/auth/users/test_user/roles" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "role_ids": ["TESTER", "REVIEWER"]
  }'
```

### 角色和权限管理

```bash
# 1. 创建角色
curl -X POST "http://localhost:8000/api/v1/auth/roles" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "role_name": "高级测试工程师",
    "description": "负责复杂的测试任务",
    "permission_ids": ["test_cases:read", "test_cases:write", "execution_tasks:read"]
  }'

# 2. 查询权限列表
curl -X GET "http://localhost:8000/api/v1/auth/permissions?limit=50" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 创建权限
curl -X POST "http://localhost:8000/api/v1/auth/permissions" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "perm_name": "管理测试计划",
    "description": "可以管理测试计划的创建和配置",
    "resource": "test_plans",
    "action": "manage"
  }'
```

## 最佳实践

### 权限设计
1. 遵循最小权限原则
2. 合理规划资源分类
3. 统一命名规范
4. 定期审查权限分配

### 角色管理
1. 根据业务需要定义角色
2. 避免角色权限过度重叠
3. 定期评估角色必要性
4. 记录角色变更历史

### 用户管理
1. 及时激活/停用用户
2. 定期审查用户权限
3. 强制密码复杂度要求
4. 记录用户操作日志

### 安全考虑
1. Token过期时间设置合理
2. 敏感操作需要二次确认
3. 定期审查管理员权限
4. 记录所有权限变更操作