"""测试用例评论"""
from datetime import datetime, timezone
from typing import Optional

from beanie import Document, before_event, Insert, Save, Replace
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class TestCaseCommentDoc(Document):
    """测试用例评论数据模型"""
    case_id: str = Field(..., description="用例业务 ID")
    content: str = Field(..., description="评论内容")
    author_id: str = Field(..., description="作者 user_id")
    author_name: Optional[str] = Field(None, description="作者姓名（冗余，方便展示）")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(None, description="最后编辑时间")

    @before_event([Insert])
    def touch_created_at(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)

    @before_event([Replace, Save])
    def touch_updated_at(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "test_case_comments"
        indexes = [
            IndexModel([("case_id", ASCENDING), ("created_at", DESCENDING)]),
        ]
