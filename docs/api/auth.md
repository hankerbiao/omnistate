# 认证说明

## 概述

本文档详细说明DMLV4系统的认证授权机制，包括JWT Token的使用、权限控制和安全最佳实践。

## 认证流程

### 1. 用户登录

用户通过用户名/用户ID和密码进行身份验证，系统验证成功后返回JWT访问令牌。

```bash
# 登录请求
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_username",
    "password": "your_password"
  }'
```

### 2. Token使用

在后续请求中携带Token进行身份认证。

```bash
# 使用Token访问API
curl -X GET "http://localhost:8000/api/v1/work-items" \
  -H "Authorization: Bearer your_jwt_token_here"
```

### 3. Token验证

系统验证Token的有效性和权限，决定是否允许访问请求的资源。

## JWT Token结构

### Token组成

JWT（JSON Web Token）由三部分组成，用点号分隔：

```
Header.Payload.Signature
```

### Header（头部）

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### Payload（载荷）

```json
{
  "user_id": "user123",
  "username": "john_doe",
  "role_ids": ["USER", "TESTER"],
  "iat": 1640995200,
  "exp": 1641081600
}
```

| 字段 | 说明 |
|------|------|
| `user_id` | 用户唯一标识 |
| `username` | 用户名 |
| `role_ids` | 用户角色列表 |
| `iat` | 签发时间（Unix时间戳） |
| `exp` | 过期时间（Unix时间戳） |

### Signature（签名）

使用HMAC SHA256算法和服务器密钥对Header和Payload进行签名。

## 权限控制

### 基于角色的访问控制（RBAC）

系统采用RBAC模型：

```
用户(User) → 角色(Role) → 权限(Permission) → 资源(Resource)
```

### 权限检查流程

1. **身份验证**：验证JWT Token有效性
2. **角色验证**：检查用户角色列表
3. **权限验证**：检查角色是否具有所需权限
4. **资源访问**：允许或拒绝访问请求

### 权限类型

| 权限级别 | 说明 | 示例 |
|----------|------|------|
| 读权限 | 查看数据和信息 | `work_items:read` |
| 写权限 | 创建和修改数据 | `test_cases:write` |
| 删除权限 | 删除数据和资源 | `requirements:delete` |
| 执行权限 | 执行特定操作 | `execution_tasks:execute` |
| 管理权限 | 系统管理功能 | `users:write` |

## 接口权限要求

### 核心模块权限

| 模块 | 读权限 | 写权限 | 特殊权限 |
|------|--------|--------|----------|
| 工作流 | `work_items:read` | `work_items:write` | `work_items:transition` |
| 测试需求 | `requirements:read` | `requirements:write` | - |
| 测试用例 | `test_cases:read` | `test_cases:write` | - |
| 测试执行 | `execution_tasks:read` | `execution_tasks:write` | `execution_tasks:execute` |
| 资产管理 | `assets:read` | `assets:write` | - |

### 支撑模块权限

| 模块 | 读权限 | 写权限 | 管理权限 |
|------|--------|--------|----------|
| 用户管理 | `users:read` | `users:write` | - |
| 角色管理 | `roles:read` | `roles:write` | - |
| 权限管理 | `permissions:read` | `permissions:write` | - |

## 常见认证场景

### 场景1：查看工作项列表

```bash
# 需要 work_items:read 权限
curl -X GET "http://localhost:8000/api/v1/work-items" \
  -H "Authorization: Bearer your_token"
```

### 场景2：创建测试用例

```bash
# 需要 test_cases:write 权限
curl -X POST "http://localhost:8000/api/v1/test-cases" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"title": "新用例", "description": "用例描述"}'
```

### 场景3：执行状态流转

```bash
# 需要 work_items:transition 权限
curl -X POST "http://localhost:8000/api/v1/work-items/{id}/transition" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"action": "SUBMIT", "operator_id": "user123"}'
```

### 场景4：系统管理操作

```bash
# 需要管理员权限
curl -X GET "http://localhost:8000/api/v1/admin/navigation/pages" \
  -H "Authorization: Bearer admin_token"
```

## 错误处理

### 认证失败场景

| 状态码 | 错误消息 | 原因 | 解决方案 |
|--------|----------|------|----------|
| 401 | "Unauthorized" | Token缺失或无效 | 重新登录获取Token |
| 403 | "Forbidden" | 权限不足 | 联系管理员分配权限 |
| 404 | "Not Found" | 资源不存在 | 检查资源ID是否正确 |

### 错误响应示例

```json
{
  "code": 401,
  "message": "Unauthorized",
  "detail": "Token has expired",
  "timestamp": "2026-03-03T11:42:00Z"
}
```

```json
{
  "code": 403,
  "message": "Forbidden",
  "detail": "Insufficient permissions: work_items:transition required",
  "timestamp": "2026-03-03T11:42:00Z"
}
```

## 安全最佳实践

### Token管理

1. **安全存储**：在客户端安全存储Token，避免泄露
2. **及时清理**：用户登出时清理本地存储的Token
3. **传输安全**：使用HTTPS传输敏感信息
4. **过期处理**：处理Token过期情况，自动刷新或重新登录

### 权限设计

1. **最小权限原则**：只授予用户必要的最小权限
2. **定期审查**：定期审查和更新用户权限
3. **分离职责**：关键操作需要多级审批
4. **审计日志**：记录所有权限变更和敏感操作

### 网络安全

1. **HTTPS优先**：生产环境强制使用HTTPS
2. **CORS配置**：合理配置跨域访问策略
3. **IP白名单**：对敏感接口实施IP白名单
4. **频率限制**：对登录接口实施频率限制

## 常见问题

### Q1: Token过期后如何处理？

A: 当Token过期时，API会返回401错误。客户端应该：
1. 提示用户重新登录
2. 清除本地存储的过期Token
3. 引导用户重新认证

### Q2: 如何检查当前用户的权限？

A: 使用以下接口：
```bash
curl -X GET "http://localhost:8000/api/v1/auth/users/me/permissions" \
  -H "Authorization: Bearer your_token"
```

### Q3: 如何实现单点登录（SSO）？

A: 当前系统原生不支持SSO，但可以通过以下方式扩展：
1. 集成LDAP/AD认证
2. 使用OAuth 2.0/OpenID Connect
3. 开发自定义认证中间件

### Q4: 密码策略如何配置？

A: 密码策略由系统配置决定，通常包括：
- 最小长度要求
- 复杂度要求（大小写、数字、特殊字符）
- 历史密码检查
- 定期强制修改密码

### Q5: 如何处理并发登录？

A: 系统支持多设备同时登录，但可以通过配置限制：
- 单用户最大登录设备数
- 强制下线机制
- 会话管理策略

## 示例代码

### JavaScript/TypeScript

```typescript
// API客户端封装
class ApiClient {
  private baseURL = 'http://localhost:8000/api/v1';
  private token: string | null = localStorage.getItem('token');

  // 设置Token
  setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  // 通用请求方法
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Token过期，处理重新登录
      this.handleUnauthorized();
      throw new Error('Token expired');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Request failed');
    }

    return response.json();
  }

  // 登录
  async login(userId: string, password: string) {
    const response = await this.request<{ data: { access_token: string; user: any } }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, password }),
    });

    this.setToken(response.data.access_token);
    return response.data;
  }

  // 获取工作项列表
  async getWorkItems(params: any = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/work-items?${query}`);
  }

  // 处理未授权
  private handleUnauthorized() {
    this.token = null;
    localStorage.removeItem('token');
    // 跳转到登录页或触发登录流程
    window.location.href = '/login';
  }
}
```

### Python

```python
import requests
import json
from typing import Optional, Dict, Any

class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.session = requests.Session()

    def set_token(self, token: str):
        self.token = token
        self.session.headers.update({'Authorization': f'Bearer {token}'})

    def login(self, user_id: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"user_id": user_id, "password": password}
        )
        response.raise_for_status()

        data = response.json()
        self.set_token(data["data"]["access_token"])
        return data["data"]

    def get_work_items(self, **params) -> Dict[str, Any]:
        """获取工作项列表"""
        response = self.session.get(f"{self.base_url}/work-items", params=params)
        response.raise_for_status()
        return response.json()

    def create_test_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建测试用例"""
        response = self.session.post(
            f"{self.base_url}/test-cases",
            json=case_data
        )
        response.raise_for_status()
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = ApiClient()

    try:
        # 登录
        auth_data = client.login("admin", "password123")
        print(f"登录成功: {auth_data['user']['full_name']}")

        # 获取工作项列表
        work_items = client.get_work_items(limit=10)
        print(f"获取到 {len(work_items['data'])} 个工作项")

    except requests.exceptions.HTTPError as e:
        print(f"请求失败: {e}")
    except Exception as e:
        print(f"错误: {e}")
```

这些示例代码展示了如何在前端和后端集成认证功能，实现安全的API访问。