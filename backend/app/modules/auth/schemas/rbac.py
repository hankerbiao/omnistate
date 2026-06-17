"""RBAC API 数据模型定义

说明：
- 本文件仅负责 API 请求体/响应体的数据结构与字段校验。
- Request 模型表示前端可提交参数；Response 模型表示后端返回结构。
- 这里不承载权限判断与业务规则，仅做 schema 约束与文档描述。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ========== User ==========

class CreateUserRequest(BaseModel):
    """数据模型：创建用户请求体。"""

    user_id: str = Field(..., description="用户登录 ID（系统内唯一）")
    username: str = Field(..., description="用户名（展示名称）")
    password: str = Field(..., min_length=6, description="登录密码，最少 6 位")
    email: Optional[str] = Field(default=None, description="邮箱地址，可选")
    role_ids: List[str] = Field(default_factory=list, description="初始角色 ID 列表")
    status: str = Field(default="ACTIVE", description="用户状态：ACTIVE / INACTIVE")
    itcode: str = Field(default="", description="光圈通知 itcode")
    subscribe_notifications: bool = Field(default=False, description="是否订阅通知")


class UpdateUserRequest(BaseModel):
    """数据模型：更新用户基础信息请求体（不含角色）。"""

    username: Optional[str] = Field(default=None, description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱地址")
    status: Optional[str] = Field(default=None, description="用户状态：ACTIVE / INACTIVE")
    itcode: Optional[str] = Field(default=None, description="光圈通知 itcode")
    subscribe_notifications: Optional[bool] = Field(default=None, description="是否订阅通知")


class UpdateUserRolesRequest(BaseModel):
    """数据模型：更新用户角色请求体（管理员操作）。"""

    role_ids: List[str] = Field(default_factory=list, description="角色 ID 列表")


class UpdateUserExtraPermissionsRequest(BaseModel):
    """数据模型：更新用户额外权限请求体。"""

    extra_permission_ids: List[str] = Field(default_factory=list, description="用户独立额外权限 ID 列表")


class UserExtraPermissionsResponse(BaseModel):
    """数据模型：用户生效权限响应体。"""

    user_id: str = Field(..., description="用户 ID")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    extra_permission_ids: List[str] = Field(..., description="用户独立额外权限 ID 列表")
    role_permissions: List[str] = Field(..., description="从角色继承的权限码")
    extra_permissions: List[str] = Field(..., description="从个人额外设置的权限码")
    permissions: List[str] = Field(..., description="并集后的全部权限码")


class UpdateUserPasswordRequest(BaseModel):
    """数据模型：管理员或本人更新密码请求体。"""

    new_password: str = Field(..., min_length=6, description="新密码，最少 6 位")


class ChangePasswordRequest(BaseModel):
    """数据模型：用户自助改密请求体（需提供旧密码）。"""

    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码，最少 6 位")


class LoginRequest(BaseModel):
    """数据模型：登录请求体。"""

    user_id: str = Field(..., description="用户登录 ID")
    password: str = Field(..., description="登录密码")


class UserResponse(BaseModel):
    """数据模型：用户信息响应体。"""

    id: str = Field(..., description="数据库文档 ID")
    user_id: str = Field(..., description="用户登录 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱地址")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    extra_permission_ids: List[str] = Field(default_factory=list, description="用户独立额外权限 ID 列表")
    allowed_nav_views: List[str] = Field(default_factory=list, description="用户级导航视图覆盖")
    status: str = Field(..., description="用户状态")
    itcode: str = Field(default="", description="光圈通知 itcode")
    subscribe_notifications: bool = Field(default=False, description="是否订阅通知")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class LoginResponse(BaseModel):
    """数据模型：登录响应体。"""

    access_token: str = Field(..., description="访问令牌（JWT）")
    token_type: str = Field(default="Bearer", description="令牌类型，默认 Bearer")
    user: UserResponse = Field(..., description="当前登录用户信息")


class MePermissionsResponse(BaseModel):
    """数据模型：当前用户权限响应体。"""

    user_id: str = Field(..., description="用户 ID")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    extra_permission_ids: List[str] = Field(default_factory=list, description="用户独立额外权限 ID 列表")
    permissions: List[str] = Field(..., description="权限码列表")


class NavigationPageResponse(BaseModel):
    """数据模型：导航页面定义响应体。"""

    id: Optional[str] = Field(default=None, description="导航页面文档 ID")
    view: str = Field(..., description="导航视图标识（唯一）")
    label: str = Field(..., description="导航名称")
    permission: Optional[str] = Field(default=None, description="访问该导航所需权限码")
    description: Optional[str] = Field(default=None, description="导航描述")
    order: int = Field(default=0, description="排序值，越小越靠前")
    is_active: bool = Field(default=True, description="是否启用")


class CreateNavigationPageRequest(BaseModel):
    """数据模型：创建导航页面请求体。"""

    view: str = Field(..., description="导航视图标识")
    label: str = Field(..., description="导航名称")
    permission: Optional[str] = Field(default=None, description="访问权限码")
    description: Optional[str] = Field(default=None, description="导航描述")
    order: int = Field(default=0, description="排序值，越小越靠前")
    is_active: bool = Field(default=True, description="是否启用")


class UpdateNavigationPageRequest(BaseModel):
    """数据模型：更新导航页面请求体（支持部分字段）。"""

    label: Optional[str] = Field(default=None, description="导航名称")
    permission: Optional[str] = Field(default=None, description="访问权限码")
    description: Optional[str] = Field(default=None, description="导航描述")
    order: Optional[int] = Field(default=None, description="排序值，越小越靠前")
    is_active: Optional[bool] = Field(default=None, description="是否启用")


class UserNavigationResponse(BaseModel):
    """数据模型：用户导航访问权限响应体。"""

    user_id: str = Field(..., description="用户 ID")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    permissions: List[str] = Field(..., description="权限码列表")
    allowed_nav_views: List[str] = Field(..., description="当前生效的导航视图列表")
    role_derived_nav_views: List[str] = Field(..., description="仅由角色权限推导的导航视图列表")
    has_nav_override: bool = Field(..., description="是否设置了用户级导航覆盖")


class UpdateUserNavigationRequest(BaseModel):
    """数据模型：更新用户导航访问权限请求体。"""

    allowed_nav_views: List[str] = Field(default_factory=list, description="允许访问的导航视图列表")


# ========== Role ==========

class CreateRoleRequest(BaseModel):
    """数据模型：创建角色请求体。"""

    role_id: Optional[str] = Field(default=None, description="角色唯一 ID（可选，不提供时自动生成）")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    is_system: bool = Field(default=False, description="是否系统角色")
    permission_ids: List[str] = Field(default_factory=list, description="角色绑定的权限 ID 列表")


class UpdateRoleRequest(BaseModel):
    """数据模型：更新角色基础信息请求体（不含权限）。"""

    name: Optional[str] = Field(default=None, description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")


class UpdateRolePermissionsRequest(BaseModel):
    """数据模型：更新角色权限请求体（管理员操作）。"""

    permission_ids: List[str] = Field(default_factory=list, description="权限 ID 列表")


class RoleResponse(BaseModel):
    """数据模型：角色响应体。"""

    id: str = Field(..., description="数据库文档 ID")
    role_id: str = Field(..., description="角色唯一 ID")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    is_system: bool = Field(default=False, description="是否系统角色")
    permission_ids: List[str] = Field(..., description="权限 ID 列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


# ========== Permission ==========

class CreatePermissionRequest(BaseModel):
    """数据模型：创建权限请求体。"""

    perm_id: str = Field(..., description="权限唯一 ID")
    code: str = Field(..., description="权限编码（如 nav:req_list:view）")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(default=None, description="权限描述")


class UpdatePermissionRequest(BaseModel):
    """数据模型：更新权限请求体（支持部分字段）。"""

    code: Optional[str] = Field(default=None, description="权限编码")
    name: Optional[str] = Field(default=None, description="权限名称")
    description: Optional[str] = Field(default=None, description="权限描述")


class PermissionResponse(BaseModel):
    """数据模型：权限响应体。"""

    id: str = Field(..., description="数据库文档 ID")
    perm_id: str = Field(..., description="权限唯一 ID")
    code: str = Field(..., description="权限编码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(default=None, description="权限描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
