"""用例集合 Beanie ODM 文档模型。"""
from typing import List, Optional
from datetime import datetime, timezone

from pydantic import Field
from beanie import Document, before_event, Save
from pymongo import IndexModel


class TestCaseCollectionDoc(Document):
    """用例集合 - 数据库模型。"""

    collection_id: str = Field(..., description="集合唯一 ID，如 CC-001")
    name: str = Field(..., description="集合名称")
    description: Optional[str] = Field(None, description="集合说明/描述")
    tags: List[str] = Field(default_factory=list, description="标签")
    case_ids: List[str] = Field(default_factory=list, description="包含的手工用例 case_id 列表")
    auto_case_ids: List[str] = Field(default_factory=list, description="包含的自动化用例 auto_case_id 列表")
    project_ids: List[str] = Field(default_factory=list, description="关联的项目 ID 列表")
    created_by: str = Field(..., description="创建人 user_id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event(Save)
    def _set_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "test_case_collections"
        use_state_management = True
        indexes = [
            IndexModel("project_ids"),
        ]
