"""测试执行 API 模型。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DispatchCaseItem(BaseModel):
    case_id: str = Field(..., description="测试用例业务 ID")


class DispatchTaskRequest(BaseModel):
    framework: str = Field(..., description="执行框架标识")
    trigger_source: Optional[str] = Field(default="manual", description="触发来源")
    callback_url: Optional[str] = Field(None, description="框架回调地址")
    dut: Dict[str, Any] = Field(default_factory=dict)
    cases: List[DispatchCaseItem] = Field(default_factory=list)
    runtime_config: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class DispatchTaskResponse(BaseModel):
    task_id: str
    external_task_id: Optional[str] = None
    dispatch_status: str
    overall_status: str
    case_count: int
    created_at: datetime

