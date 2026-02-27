"""菜单管理 API schemas。"""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


class CreateMenuRequest(BaseModel):
    menu_id: str = Field(..., description="菜单业务ID")
    name: str = Field(..., description="菜单名称")
    path: str = Field(..., description="前端路由路径")
    icon: Optional[str] = None
    parent_menu_id: Optional[str] = None
    order: int = 0
    required_permissions: List[str] = Field(default_factory=list)
    is_active: bool = True


class UpdateMenuRequest(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    icon: Optional[str] = None
    parent_menu_id: Optional[str] = None
    order: Optional[int] = None
    required_permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class MenuResponse(BaseModel):
    id: str
    menu_id: str
    name: str
    path: str
    icon: Optional[str]
    parent_menu_id: Optional[str]
    order: int
    required_permissions: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MyMenusResponse(BaseModel):
    user_id: str
    permissions: List[str]
    menus: List[MenuResponse]
