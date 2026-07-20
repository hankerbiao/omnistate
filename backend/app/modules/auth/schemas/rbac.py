"""Auth API schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    user_id: str = Field(..., description="用户登录 ID（系统内唯一）")
    username: str = Field(..., description="用户名（展示名称）")
    password: str = Field(..., min_length=6, description="登录密码，最少 6 位")
    email: Optional[str] = Field(default=None, description="邮箱地址，可选")
    role_ids: List[str] = Field(default_factory=list, description="初始角色 ID 列表")
    status: str = Field(default="ACTIVE", description="用户状态：ACTIVE / DISABLED")
    itcode: str = Field(default="", description="光圈通知 itcode")
    subscribe_notifications: bool = Field(default=False, description="是否订阅通知")


class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(default=None, description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱地址")
    status: Optional[str] = Field(default=None, description="用户状态：ACTIVE / DISABLED")
    itcode: Optional[str] = Field(default=None, description="光圈通知 itcode")
    subscribe_notifications: Optional[bool] = Field(default=None, description="是否订阅通知")


class UpdateUserRolesRequest(BaseModel):
    role_ids: List[str] = Field(default_factory=list, description="角色 ID 列表")


class UserPermissionsResponse(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    role_permissions: List[str] = Field(..., description="从角色继承的权限码")
    permissions: List[str] = Field(..., description="全部权限码")


class UpdateUserPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, description="新密码，最少 6 位")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码，最少 6 位")


class LoginRequest(BaseModel):
    user_id: str = Field(..., description="用户登录 ID")
    password: str = Field(..., description="登录密码")


class UserResponse(BaseModel):
    id: str = Field(..., description="数据库文档 ID")
    user_id: str = Field(..., description="用户登录 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱地址")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    status: str = Field(..., description="用户状态")
    itcode: str = Field(default="", description="光圈通知 itcode")
    subscribe_notifications: bool = Field(default=False, description="是否订阅通知")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="访问令牌（JWT）")
    token_type: str = Field(default="Bearer", description="令牌类型，默认 Bearer")
    user: UserResponse = Field(..., description="当前登录用户信息")


class MePermissionsResponse(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    permissions: List[str] = Field(..., description="权限码列表")


class CreateRoleRequest(BaseModel):
    role_id: Optional[str] = Field(default=None, description="角色唯一 ID（可选，不提供时自动生成）")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    is_system: bool = Field(default=False, description="是否系统角色")
    permission_ids: List[str] = Field(default_factory=list, description="角色绑定的权限 ID 列表")


class UpdateRoleRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")


class UpdateRolePermissionsRequest(BaseModel):
    permission_ids: List[str] = Field(default_factory=list, description="权限 ID 列表")


class RoleResponse(BaseModel):
    id: str = Field(..., description="数据库文档 ID")
    role_id: str = Field(..., description="角色唯一 ID")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    is_system: bool = Field(default=False, description="是否系统角色")
    permission_ids: List[str] = Field(..., description="权限 ID 列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class PermissionResponse(BaseModel):
    id: str = Field(..., description="权限唯一 ID")
    perm_id: str = Field(..., description="权限唯一 ID")
    code: str = Field(..., description="权限编码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
