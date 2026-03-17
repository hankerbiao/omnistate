# 认证与登录指南

## 1. 概述

DMLV4 系统采用基于 JWT 的身份认证和 RBAC（基于角色的访问控制）权限管理体系。用户需要登录后才能访问系统功能。

## 2. 认证流程

### 2.1 登录流程

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  前端    │────▶│  后端    │────▶│  MongoDB │
│  登录页  │     │  API     │     │  用户验证 │
└──────────┘     └──────────┘     └──────────┘
     │                │                │
     │ 1. 输入账号密码 │                │
     │ 2. 发送登录请求 │                │
     │                │ 3. 验证用户   │
     │ 4. 返回 JWT   │◀─────────────│
     │◀─────────────│                │
     │                │                │
     ▼                ▼                ▼
  保存 Token       生成 Token        查询密码
```

### 2.2 请求流程

登录后，前端在每次 API 请求中携带 JWT Token：

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  前端    │────▶│  后端    │────▶│  业务逻辑 │
│  请求    │     │  鉴权    │     │          │
└──────────┘     └──────────┘     └──────────┘
     │                │                │
     │ Authorization: │                │
     │ Bearer <token> │                │
     │                │ 验证 Token    │
     │                │ 检查权限      │
     │                │               │
     ▼                ▼                ▼
```

## 3. API 说明

### 3.1 登录接口

**请求**

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "user_id": "admin",
  "password": "password123"
}
```

**响应（成功）**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "507f1f77bcf86cd799439011",
      "user_id": "admin",
      "username": "管理员",
      "email": "admin@example.com",
      "role_ids": ["ADMIN_ROLE"],
      "status": "ACTIVE"
    }
  }
}
```

**响应（失败）**

```json
{
  "code": 401,
  "message": "invalid credentials",
  "data": null
}
```

### 3.2 获取当前用户权限

登录后可获取当前用户的权限信息：

```http
GET /api/v1/auth/users/me/permissions
Authorization: Bearer <token>
```

**响应**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "user_id": "admin",
    "role_ids": ["ADMIN_ROLE"],
    "permissions": [
      "users:read",
      "users:write",
      "work_items:read",
      "work_items:write"
    ]
  }
}
```

### 3.3 获取用户导航权限

获取当前用户可访问的导航页面：

```http
GET /api/v1/auth/users/me/navigation
Authorization: Bearer <token>
```

### 3.4 用户自助修改密码

```http
POST /api/v1/auth/users/me/password
Authorization: Bearer <token>
Content-Type: application/json

{
  "old_password": "old_password123",
  "new_password": "new_password123"
}
```

## 4. 前端实现

### 4.1 登录组件

前端登录页面位于 `frontend/src/components/LoginPage.tsx`。

**核心代码**

```tsx
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();

  try {
    const response = await api.login(formData);

    // 获取 Token
    const token = response.data.access_token;

    // 保存到 localStorage
    localStorage.setItem('jwt_token', token);

    // 设置 API 客户端 Token
    api.setToken(token);

    // 登录成功，跳转页面
    if (onLoginSuccess) {
      onLoginSuccess();
    }
  } catch (err) {
    setError('登录失败，请检查用户名和密码');
  }
};
```

### 4.2 Token 存储

- **存储位置**：`localStorage`
- **存储键名**：`jwt_token`

### 4.3 API 请求携带 Token

API 客户端在请求时自动添加 Authorization 头：

```typescript
private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (this.token) {
    headers['Authorization'] = `Bearer ${this.token}`;
  }

  // ... 发送请求
}
```

### 4.4 环境配置

在 `.env.local` 中配置 API 地址：

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## 5. 后端实现

### 5.1 JWT 生成

位置：`app/shared/auth/__init__.py`

```python
from app.shared.auth import create_access_token

# 使用 user_id 生成 Token
token = create_access_token(user["user_id"])
```

### 5.2 Token 验证

后端通过依赖 `get_current_user` 验证 Token：

```python
from app.shared.auth import get_current_user

@router.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"user_id": current_user["user_id"]}
```

### 5.3 权限检查

使用 `require_permission` 或 `require_any_permission` 进行权限检查：

```python
from app.shared.auth import require_permission, require_any_permission

# 需要特定权限
@router.post("/users")
async def create_user(_=Depends(require_permission("users:write"))):
    pass

# 需要任意一个权限
@router.get("/users")
async def list_users(_=Depends(require_any_permission(["users:read", "work_items:read"]))):
    pass
```

## 6. RBAC 模型

### 6.1 核心概念

| 概念 | 说明 |
|------|------|
| **用户（User）** | 系统登录账号 |
| **角色（Role）** | 权限集合，如 ADMIN、TESTER |
| **权限（Permission）** | 具体操作许可，如 `users:read` |
| **导航页面（NavigationPage）** | 前端页面访问控制 |

### 6.2 内置角色

| 角色 ID | 说明 |
|---------|------|
| ADMIN | 管理员，拥有所有权限 |
| TESTER | 测试人员 |
| DEVELOPER | 开发人员 |

### 6.3 权限格式

权限采用 `资源:操作` 格式：

| 权限 | 说明 |
|------|------|
| `users:read` | 查看用户 |
| `users:write` | 创建/修改用户 |
| `roles:read` | 查看角色 |
| `roles:write` | 创建/修改角色 |
| `permissions:read` | 查看权限 |
| `permissions:write` | 创建/修改权限 |
| `work_items:read` | 查看工作项 |
| `work_items:write` | 创建/修改工作项 |
| `navigation:read` | 查看导航 |

## 7. 初始化

### 7.1 创建管理员用户

```bash
cd backend
python scripts/create_user.py
```

### 7.2 初始化 RBAC 数据

```bash
cd backend
python scripts/init_rbac.py
```

这将创建：
- 默认权限（users、roles、permissions、navigation 等）
- 默认角色（ADMIN、TESTER、DEVELOPER）
- 角色与权限的绑定关系

## 8. 常见问题

### 8.1 登录失败

**可能原因**：
1. 用户名或密码错误
2. 用户状态为非 ACTIVE
3. 后端服务未启动

**排查步骤**：
1. 检查浏览器控制台错误信息
2. 确认用户名密码正确
3. 检查后端服务状态

### 8.2 Token 过期

JWT Token 有有效期限制，过期后需要重新登录。前端应处理 401 响应，引导用户重新登录。

### 8.3 权限不足

如果用户访问受限资源，会返回 403 错误。需要管理员为用户分配相应角色。

## 9. 安全建议

1. **生产环境**：使用 HTTPS 传输
2. **密码策略**：强制使用强密码，定期更换
3. **Token 有效期**：根据业务需求设置合理的过期时间
4. **敏感操作**：如修改密码、删除数据，建议二次验证