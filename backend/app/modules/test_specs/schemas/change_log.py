"""测试用例变更记录 Schema"""
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class TestCaseFieldChangeResponse(BaseModel):
    field: str = Field(..., description="字段名")
    old_value: Optional[Any] = Field(None, description="旧值")
    new_value: Optional[Any] = Field(None, description="新值")
    change_type: str = Field(..., description="added|removed|modified")


class TestCaseChangeLogResponse(BaseModel):
    id: str
    case_id: str
    revision_no: int
    action: str
    operator_id: str
    operator_name: Optional[str] = None
    changes: List[TestCaseFieldChangeResponse]
    remark: Optional[str] = None
    created_at: str


class TestCaseChangeLogListResponse(BaseModel):
    items: List[TestCaseChangeLogResponse]
    total: int
