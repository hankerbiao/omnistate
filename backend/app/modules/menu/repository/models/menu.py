"""菜单管理数据模型。"""
from typing import Optional, List
from datetime import datetime, timezone

from beanie import Document, before_event, Save, Insert
from pydantic import BaseModel, Field, ConfigDict
from pymongo import IndexModel, ASCENDING


class MenuDoc(Document):
    """菜单实体（后台可配置）。"""

    menu_id: str = Field(..., description="菜单业务ID")
    name: str = Field(..., description="菜单名称")
    path: str = Field(..., description="前端路由路径")
    icon: Optional[str] = Field(None, description="图标名")
    parent_menu_id: Optional[str] = Field(None, description="父菜单ID")
    order: int = Field(default=0, description="排序，越小越靠前")
    required_permissions: List[str] = Field(default_factory=list, description="可见所需权限")
    is_active: bool = Field(default=True, description="是否启用")
    is_deleted: bool = Field(default=False, description="逻辑删除")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "menus"
        indexes = [
            IndexModel("menu_id", unique=True),
            IndexModel("path"),
            IndexModel("parent_menu_id"),
            IndexModel("is_active"),
            IndexModel("is_deleted"),
            IndexModel([("parent_menu_id", ASCENDING), ("order", ASCENDING)]),
        ]


class MenuModel(BaseModel):
    id: Optional[str] = None
    menu_id: str
    name: str
    path: str
    icon: Optional[str] = None
    parent_menu_id: Optional[str] = None
    order: int
    required_permissions: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
