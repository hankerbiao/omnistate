"""
用户、角色、权限模型 (Beanie ODM)

AI 友好注释说明：
- 这是 RBAC 的基础数据层，用于持久化用户、角色与权限。
- Document 类负责数据库表结构与索引；Pydantic Model 用于 API 返回。
"""
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from beanie import Document, before_event, Save, Insert
from pymongo import IndexModel


# ========== Beanie 文档模型 ==========

class UserDoc(Document):
    """用户 - 数据库模型（保存用户与角色绑定信息）"""
    # user_id 是业务主键，避免直接暴露 ObjectId
    user_id: str = Field(..., description="用户唯一 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    # 密码存储为 hash + salt（避免明文）
    password_hash: str = Field(..., description="密码哈希")
    password_salt: str = Field(..., description="密码盐")
    # 一个用户可绑定多个角色
    role_ids: List[str] = Field(default_factory=list, description="角色 ID 列表")
    # 用户级导航可见页面覆盖（为空时按角色/权限默认）
    allowed_nav_views: List[str] = Field(default_factory=list, description="用户允许访问的导航页面")
    status: str = Field(default="ACTIVE", description="用户状态")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="更新时间")

    @before_event([Save, Insert])
    def update_updated_at(self):
        # 每次写入前自动刷新更新时间
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "users"
        indexes = [
            IndexModel("user_id", unique=True),
            IndexModel("username"),
            IndexModel("email"),
            IndexModel("status"),
        ]


class RoleDoc(Document):
    """角色 - 数据库模型（角色聚合多个权限）"""
    role_id: str = Field(..., description="角色唯一 ID")
    name: str = Field(..., description="角色名称")
    # 角色绑定权限集合
    permission_ids: List[str] = Field(default_factory=list, description="权限 ID 列表")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="更新时间")

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "roles"
        indexes = [
            IndexModel("role_id", unique=True),
            IndexModel("name", unique=True),
        ]


class PermissionDoc(Document):
    """权限 - 数据库模型（最小授权单元）"""
    perm_id: str = Field(..., description="权限唯一 ID")
    # code 建议格式：资源:动作（例如 requirements:write）
    code: str = Field(..., description="权限编码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="更新时间")

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "permissions"
        indexes = [
            IndexModel("perm_id", unique=True),
            IndexModel("code", unique=True),
            IndexModel("name"),
        ]


# ========== Pydantic 响应模型 (API) ==========

class UserModel(BaseModel):
    """API 返回用用户模型（不含敏感字段）"""
    id: Optional[str] = Field(None, description="文档唯一标识 ID")
    user_id: str = Field(..., description="用户唯一 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    role_ids: List[str] = Field(..., description="角色 ID 列表")
    allowed_nav_views: List[str] = Field(default_factory=list, description="用户允许访问的导航页面")
    status: str = Field(..., description="用户状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class RoleModel(BaseModel):
    """API 返回用角色模型"""
    id: Optional[str] = Field(None, description="文档唯一标识 ID")
    role_id: str = Field(..., description="角色唯一 ID")
    name: str = Field(..., description="角色名称")
    permission_ids: List[str] = Field(..., description="权限 ID 列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class PermissionModel(BaseModel):
    """API 返回用权限模型"""
    id: Optional[str] = Field(None, description="文档唯一标识 ID")
    perm_id: str = Field(..., description="权限唯一 ID")
    code: str = Field(..., description="权限编码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)
