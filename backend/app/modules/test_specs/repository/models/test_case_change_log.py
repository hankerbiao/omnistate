"""测试用例变更记录"""
from datetime import datetime, timezone
from typing import Any, Optional

from beanie import Document, before_event, Insert, Save
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class TestCaseChangeLogDoc(Document):
    """测试用例字段级变更审计"""
    case_id: str = Field(..., description="用例业务 ID")
    revision_no: int = Field(..., description="用例维度递增版本号")
    action: str = Field(..., description="CREATE|UPDATE|ASSIGN_OWNERS|MOVE_REQUIREMENT|LINK_AUTOMATION|DELETE")
    operator_id: str = Field(..., description="操作人 user_id")
    changes: list[dict[str, Any]] = Field(default_factory=list, description="字段 diff 列表")
    remark: Optional[str] = Field(None, description="版本说明等备注")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def touch_created_at(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)

    class Settings:
        name = "test_case_change_logs"
        indexes = [
            IndexModel([("case_id", ASCENDING), ("created_at", ASCENDING)]),
            IndexModel(
                [("case_id", ASCENDING), ("revision_no", ASCENDING)],
                unique=True,
            ),
        ]
