"""RBAC API 模型

AI 友好注释说明：
- 这些模型用于 API 的请求体与响应体校验。
- Request 类只包含前端可提交字段；Response 类包含服务端返回字段。
- 这里不做权限校验，只负责数据结构。
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ========== User ==========

class CreateUserRequest(BaseModel):
    """创建用户请求体"""
    user_id: str = Field(..., description="用户唯一 ID")
    username: str = Field(..., description="用户名")
    password: str = Field(..., min_length=6, description="登录密码")
    email: Optional[str] = None
    role_ids: List[str] = Field(default_factory=list)
    status: str = Field(default="ACTIVE")


class UpdateUserRequest(BaseModel):
    """更新用户信息请求体（不含角色）"""
    username: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None


class UpdateUserRolesRequest(BaseModel):
    """更新用户角色请求体（管理员操作）"""
    role_ids: List[str] = Field(default_factory=list)


class UpdateUserPasswordRequest(BaseModel):
    """更新用户密码请求体（管理员或本人）"""
    new_password: str = Field(..., min_length=6)


class ChangePasswordRequest(BaseModel):
    """用户自助修改密码请求体（需要旧密码）"""
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    """登录请求体"""
    user_id: str
    password: str


class UserResponse(BaseModel):
    """用户返回结构"""
    id: str
    user_id: str
    username: str
    email: Optional[str]
    role_ids: List[str]
    status: str
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    """登录响应结构"""
    access_token: str
    token_type: str = "Bearer"
    user: UserResponse


class MePermissionsResponse(BaseModel):
    """当前用户权限响应结构"""
    user_id: str
    role_ids: List[str]
    permissions: List[str]


class NavigationPageResponse(BaseModel):
    """导航页面定义"""
    id: Optional[str] = None
    view: str
    label: str
    permission: Optional[str] = None
    description: Optional[str] = None
    order: int = 0
    is_active: bool = True


class CreateNavigationPageRequest(BaseModel):
    """创建导航页面请求"""
    view: str = Field(..., description="导航视图标识")
    label: str = Field(..., description="导航名称")
    permission: Optional[str] = Field(None, description="访问权限码")
    description: Optional[str] = Field(None, description="导航描述")
    order: int = Field(default=0, description="排序值，越小越靠前")
    is_active: bool = Field(default=True, description="是否启用")


class UpdateNavigationPageRequest(BaseModel):
    """更新导航页面请求"""
    label: Optional[str] = None
    permission: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class UserNavigationResponse(BaseModel):
    """用户导航访问响应"""
    user_id: str
    role_ids: List[str]
    permissions: List[str]
    allowed_nav_views: List[str]


class UpdateUserNavigationRequest(BaseModel):
    """更新用户导航访问请求"""
    allowed_nav_views: List[str] = Field(default_factory=list)


# ========== Role ==========

class CreateRoleRequest(BaseModel):
    """创建角色请求体"""
    role_id: str = Field(..., description="角色唯一 ID")
    name: str = Field(..., description="角色名称")
    permission_ids: List[str] = Field(default_factory=list)


class UpdateRoleRequest(BaseModel):
    """更新角色请求体（不含权限）"""
    name: Optional[str] = None


class UpdateRolePermissionsRequest(BaseModel):
    """更新角色权限请求体（管理员操作）"""
    permission_ids: List[str] = Field(default_factory=list)


class RoleResponse(BaseModel):
    """角色返回结构"""
    id: str
    role_id: str
    name: str
    permission_ids: List[str]
    created_at: datetime
    updated_at: datetime


# ========== Permission ==========

class CreatePermissionRequest(BaseModel):
    """创建权限请求体"""
    perm_id: str = Field(..., description="权限唯一 ID")
    code: str = Field(..., description="权限编码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = None


class UpdatePermissionRequest(BaseModel):
    """更新权限请求体"""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class PermissionResponse(BaseModel):
    """权限返回结构"""
    id: str
    perm_id: str
    code: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
