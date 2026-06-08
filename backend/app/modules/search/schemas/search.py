"""全局搜索 Schema。"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SearchItem(BaseModel):
    """搜索结果中的单个条目。"""
    id: str
    title: str
    subtitle: Optional[str] = None
    type: str          # requirement | test_case | automation_case | execution_task | comment | lab | plan_task
    type_label: str    # 中文类型名称
    highlight: Optional[str] = None   # 带有高亮标记的匹配片段
    url: str           # 前端导航路径
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SearchGroup(BaseModel):
    """搜索结果的一个分组。"""
    type: str
    type_label: str
    items: List[SearchItem]
    total: int         # 该分组的总匹配数（可能多于 items 的长度）


class SearchResponse(BaseModel):
    """搜索响应。"""
    query: str
    total: int
    results: List[SearchGroup]
