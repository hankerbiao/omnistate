# 认证授权模块 (Auth Module)

基于 RBAC (Role-Based Access Control) 的认证授权系统，提供完整的用户、角色、权限和导航页面管理功能。

## 🚀 功能特性

### 🔐 核心认证授权
- **JWT Token 认证**: 基于 JWT 的无状态认证机制
- **密码安全**: 使用 salt + hash 方式安全存储密码
- **权限控制**: 细粒度的权限管理，支持资源:动作格式 (如 `requirements:write`)

### 👥 用户管理
- 用户创建、更新、删除、查询
- 用户状态管理 (ACTIVE/INACTIVE)
- 用户角色绑定/解绑
- 密码修改和重置
- 用户导航页面权限个性化

### 🛡️ 角色管理
- 角色 CRUD 操作
- 角色与权限的绑定关系管理
- 角色继承机制支持
- 管理员角色特殊处理

### 🔑 权限管理
- 权限 CRUD 操作
- 权限编码规范：`资源:动作` (如 `requirements:read`, `test_cases:write`)
- 权限描述和文档化
- 权限与角色的关联管理

### 🧭 导航页面管理
- 可配置的导航页面定义
- 页面级权限控制
- 公共页面和受保护页面
- 导航顺序管理
- 用户级导航权限覆盖

## 📁 项目结构

```
auth/
├── api/                    # API 路由层
│   └── routes.py          # FastAPI 路由定义
├── repository/            # 数据访问层
│   └── models/           # 数据模型
│       ├── rbac.py       # 用户/角色/权限模型
│       └── navigation.py # 导航页面模型
├── schemas/               # 数据模式
│   └── rbac.py          # API 请求/响应模式
├── service/              # 业务逻辑层
│   ├── user_service.py   # 用户资源服务
│   ├── role_service.py   # 角色资源服务
│   ├── permission_service.py # 权限资源服务
│   ├── navigation_access_service.py # 导航访问服务
│   ├── navigation_page_service.py # 导航页面服务
│   └── exceptions.py     # 业务异常定义
└── README.md            # 本文档
```

## 🔌 API 端点

### 用户管理
- `POST /auth/users` - 创建用户
- `GET /auth/users/{user_id}` - 获取用户详情
- `GET /auth/users` - 查询用户列表
- `PUT /auth/users/{user_id}` - 更新用户信息
- `PATCH /auth/users/{user_id}/password` - 修改用户密码
- `PATCH /auth/users/{user_id}/roles` - 更新用户角色
- `PATCH /auth/users/{user_id}/navigation` - 更新用户导航权限

### 角色管理
- `POST /auth/roles` - 创建角色
- `GET /auth/roles/{role_id}` - 获取角色详情
- `GET /auth/roles` - 查询角色列表
- `PUT /auth/roles/{role_id}` - 更新角色信息
- `DELETE /auth/roles/{role_id}` - 删除角色
- `PUT /auth/roles/{role_id}/permissions` - 更新角色权限

### 权限管理
- `POST /auth/permissions` - 创建权限
- `GET /auth/permissions/{perm_id}` - 获取权限详情
- `GET /auth/permissions` - 查询权限列表
- `PUT /auth/permissions/{perm_id}` - 更新权限信息
- `DELETE /auth/permissions/{perm_id}` - 删除权限

### 导航页面管理
- `POST /auth/navigation` - 创建导航页面
- `GET /auth/navigation/{view}` - 获取导航页面详情
- `GET /auth/navigation` - 查询导航页面列表
- `PUT /auth/navigation/{view}` - 更新导航页面
- `DELETE /auth/navigation/{view}` - 删除导航页面

### 认证相关
- `POST /auth/login` - 用户登录
- `GET /auth/me` - 获取当前用户信息
- `GET /auth/me/permissions` - 获取当前用户权限
- `GET /auth/me/navigation` - 获取当前用户可访问的导航页面

## 🗄️ 数据库模型

### 用户 (UserDoc)
```python
user_id: str              # 用户唯一ID (业务主键)
username: str             # 用户名
email: Optional[str]      # 邮箱
password_hash: str        # 密码哈希
password_salt: str        # 密码盐
role_ids: List[str]       # 角色ID列表
allowed_nav_views: List[str] # 用户允许访问的导航页面
status: str               # 用户状态 (ACTIVE/INACTIVE)
created_at: datetime      # 创建时间
updated_at: datetime      # 更新时间
```

### 角色 (RoleDoc)
```python
role_id: str              # 角色唯一ID
name: str                 # 角色名称
permission_ids: List[str] # 权限ID列表
created_at: datetime      # 创建时间
updated_at: datetime      # 更新时间
```

### 权限 (PermissionDoc)
```python
perm_id: str              # 权限唯一ID
code: str                 # 权限编码 (资源:动作)
name: str                 # 权限名称
description: Optional[str] # 权限描述
created_at: datetime      # 创建时间
updated_at: datetime      # 更新时间
```

### 导航页面 (NavigationPageDoc)
```python
view: str                 # 导航视图唯一标识
label: str                # 导航名称
permission: Optional[str] # 访问权限码
description: Optional[str] # 页面说明
order: int                # 导航排序
is_active: bool           # 是否启用
is_deleted: bool          # 逻辑删除
created_at: datetime      # 创建时间
updated_at: datetime      # 更新时间
```

## 🔐 权限控制流程

### 1. 认证流程
1. 用户登录验证 (`POST /auth/login`)
2. 生成 JWT Token
3. 后续请求携带 Token 进行认证

### 2. 授权流程
1. 解析用户 Token 获取用户信息
2. 根据用户角色获取权限列表
3. 检查请求是否需要特定权限
4. 验证用户是否拥有所需权限

### 3. 权限编码规范
- 格式：`资源:动作`
- 示例：
  - `requirements:read` - 查看需求
  - `requirements:write` - 创建/修改需求
  - `test_cases:delete` - 删除测试用例
  - `nav:public` - 公共导航页面

## 🛠️ 使用示例

### 创建用户
```python
# 请求
{
    "user_id": "user001",
    "username": "张三",
    "email": "zhangsan@example.com",
    "password": "password123",
    "role_ids": ["role001", "role002"]
}

# 响应
{
    "code": 0,
    "message": "ok",
    "data": {
        "user_id": "user001",
        "username": "张三",
        "email": "zhangsan@example.com",
        "role_ids": ["role001", "role002"],
        "status": "ACTIVE"
    }
}
```

### 用户登录
```python
# 请求
{
    "username": "zhangsan",
    "password": "password123"
}

# 响应
{
    "code": 0,
    "message": "ok",
    "data": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "bearer",
        "expires_in": 3600
    }
}
```

### 获取用户权限
```python
# GET /auth/me/permissions
{
    "code": 0,
    "message": "ok",
    "data": [
        {
            "perm_id": "perm001",
            "code": "requirements:read",
            "name": "查看需求",
            "description": "可以查看所有测试需求"
        },
        {
            "perm_id": "perm002",
            "code": "requirements:write",
            "name": "编辑需求",
            "description": "可以创建和修改测试需求"
        }
    ]
}
```

## 🔧 依赖注入

### Service 依赖
```python
from fastapi import Depends
from app.modules.auth.service import UserService

def get_user_service() -> UserService:
    return UserService()

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
```

### 权限检查
```python
from app.shared.auth import require_permission

@router.get("/requirements")
async def list_requirements(current_user = Depends(require_permission("requirements:read"))):
    return {"message": "获取需求列表"}
```

## 🚦 异常处理

### 业务异常
- `UserNotFoundError` - 用户不存在
- `RoleNotFoundError` - 角色不存在
- `PermissionNotFoundError` - 权限不存在
- `NavigationPageNotFoundError` - 导航页面不存在

### HTTP 状态码
- `200` - 成功
- `201` - 创建成功
- `400` - 请求参数错误
- `401` - 未认证
- `403` - 权限不足
- `404` - 资源不存在
- `409` - 资源冲突
- `500` - 服务器内部错误

## 📝 最佳实践

### 1. 权限设计
- 遵循最小权限原则
- 使用有意义的权限编码
- 定期审查和清理无用权限

### 2. 用户管理
- 定期更新密码
- 及时禁用离职员工账号
- 监控异常登录行为

### 3. 角色设计
- 角色命名规范统一
- 避免角色权限过于复杂
- 考虑角色的业务含义

### 4. 安全注意事项
- 密码必须加密存储
- JWT Token 设置合适的过期时间
- 敏感操作需要二次确认

## 🔗 相关文档

- [JWT 认证机制](../shared/auth/jwt_auth.py)
- [权限装饰器](../shared/auth/__init__.py)
- [数据库模型](../repository/models/)
- [API 文档](../api/routes.py)

---

**维护者**: DML V4 开发团队
**最后更新**: 2024-03-06
