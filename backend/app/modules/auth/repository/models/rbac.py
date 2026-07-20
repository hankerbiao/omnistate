"""User and role Beanie models."""
from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel

from app.shared.core.document_mixins import TimestampedDocumentMixin


class UserDoc(Document, TimestampedDocumentMixin):
    """User account with role assignments."""

    user_id: str = Field(..., description="用户唯一 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    password_hash: str = Field(..., description="密码哈希")
    password_salt: str = Field(..., description="密码盐")
    role_ids: List[str] = Field(default_factory=list, description="角色 ID 列表")
    status: str = Field(default="ACTIVE", description="用户状态")
    itcode: str = Field(default="", description="光圈通知 itcode")
    subscribe_notifications: bool = Field(default=False, description="是否订阅光圈通知")

    class Settings:
        name = "users"
        indexes = [
            IndexModel("user_id", unique=True),
            IndexModel("username"),
            IndexModel("email"),
            IndexModel("status"),
        ]


class RoleDoc(Document, TimestampedDocumentMixin):
    """Role with a static permission-code selection."""

    role_id: str = Field(..., description="角色唯一 ID")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")
    is_system: bool = Field(default=False, description="是否系统角色（系统角色不可删除）")
    permission_ids: List[str] = Field(default_factory=list, description="权限 ID 列表")

    class Settings:
        name = "roles"
        indexes = [
            IndexModel("role_id", unique=True),
            IndexModel("name", unique=True),
        ]


class UserModel(BaseModel):
    """API user response without password fields."""

    id: Optional[str] = Field(None, description="文档唯一标识 ID")
    user_id: str = Field(..., description="用户唯一 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    status: str = Field(..., description="用户状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class RoleModel(BaseModel):
    """API role response."""

    id: Optional[str] = Field(None, description="文档唯一标识 ID")
    role_id: str = Field(..., description="角色唯一 ID")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")
    is_system: bool = Field(False, description="是否系统角色")
    permission_ids: List[str] = Field(..., description="权限 ID 列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)
