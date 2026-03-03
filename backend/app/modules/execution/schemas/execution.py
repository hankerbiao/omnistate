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


class ExecutionTaskStatsResponse(BaseModel):
    queued: int = 0
    running: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    blocked: int = 0
    error: int = 0


class ExecutionTaskResponse(BaseModel):
    id: str
    task_id: str
    external_task_id: Optional[str] = None
    framework: str
    dispatch_status: str
    overall_status: str
    created_by: str
    case_count: int
    reported_case_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_callback_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    stats: Optional[ExecutionTaskStatsResponse] = None


class ExecutionTaskCaseResponse(BaseModel):
    id: str
    task_id: str
    case_id: str
    status: str
    progress_percent: Optional[float] = None
    step_total: int
    step_passed: int
    step_failed: int
    step_skipped: int
    last_seq: int
    last_event_id: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProgressCasePayload(BaseModel):
    case_id: str
    status: Optional[str] = None
    progress_percent: Optional[float] = None
    step_total: Optional[int] = None
    step_passed: Optional[int] = None
    step_failed: Optional[int] = None
    step_skipped: Optional[int] = None


class ProgressStepPayload(BaseModel):
    case_id: str
    step_id: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    message: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)


class ProgressCallbackRequest(BaseModel):
    task_id: str
    external_task_id: Optional[str] = None
    event_type: str
    seq: int = Field(..., ge=1)
    event_time: Optional[datetime] = None
    overall_status: Optional[str] = None
    case: Optional[ProgressCasePayload] = None
    step: Optional[ProgressStepPayload] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ProgressCallbackResponse(BaseModel):
    accepted: bool
    deduplicated: bool = False
