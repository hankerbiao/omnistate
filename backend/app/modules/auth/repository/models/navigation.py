"""导航页面模型（可配置导航定义）。"""
from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Insert, Save, before_event
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ASCENDING, IndexModel


class NavigationPageDoc(Document):
    """系统导航页面定义。"""

    view: str = Field(..., description="导航视图唯一标识")
    label: str = Field(..., description="导航名称")
    permission: Optional[str] = Field(None, description="访问该页面所需权限码")
    description: Optional[str] = Field(None, description="页面说明")
    order: int = Field(default=0, description="导航排序，越小越靠前")
    is_active: bool = Field(default=True, description="是否启用")
    is_deleted: bool = Field(default=False, description="逻辑删除")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "navigation_pages"
        indexes = [
            IndexModel("view", unique=True),
            IndexModel([("order", ASCENDING), ("view", ASCENDING)]),
            IndexModel("is_active"),
            IndexModel("is_deleted"),
        ]


class NavigationPageModel(BaseModel):
    id: Optional[str] = None
    view: str
    label: str
    permission: Optional[str] = None
    description: Optional[str] = None
    order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
