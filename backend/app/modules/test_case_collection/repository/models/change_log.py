"""用例集合变更日志模型。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel, ASCENDING, DESCENDING


class TestCaseCollectionChangeLogDoc(Document):
    """用例集合审计日志。"""

    collection_id: str = Field(..., description="集合 ID")
    action: str = Field(..., description="动作类型")
    operator_id: str = Field(..., description="操作者 ID")
    operator_name: Optional[str] = Field(None, description="操作者名称")
    case_changes: List[Dict[str, Any]] = Field(default_factory=list, description="用例增删变更")
    field_changes: List[Dict[str, Any]] = Field(default_factory=list, description="字段变更")
    export_format: Optional[str] = Field(None, description="导出格式")
    remark: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "test_case_collection_change_logs"
        indexes = [
            IndexModel([("collection_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel("action"),
            IndexModel("operator_id"),
        ]
