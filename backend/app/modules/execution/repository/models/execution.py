"""测试执行域数据模型（Beanie ODM）。"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie import Document, Insert, Save, before_event
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class ExecutionTaskDoc(Document):
    """执行任务主表。"""

    task_id: str = Field(..., description="平台任务唯一 ID")
    external_task_id: Optional[str] = Field(None, description="外部框架任务 ID")
    framework: str = Field(..., description="外部框架标识")
    dispatch_status: str = Field(default="PENDING", description="下发状态")
    overall_status: str = Field(default="QUEUED", description="总体执行状态")
    request_payload: Dict[str, Any] = Field(default_factory=dict, description="下发请求快照")
    dispatch_response: Dict[str, Any] = Field(default_factory=dict, description="下发响应快照")
    dispatch_error: Optional[str] = Field(None, description="下发失败原因")
    created_by: str = Field(..., description="创建者 user_id")
    case_count: int = Field(default=0, description="任务包含用例数量")
    reported_case_count: int = Field(default=0, description="已上报进度的用例数")
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_callback_at: Optional[datetime] = None
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_tasks"
        indexes = [
            IndexModel("task_id", unique=True),
            IndexModel("external_task_id"),
            IndexModel("framework"),
            IndexModel("dispatch_status"),
            IndexModel("overall_status"),
            IndexModel("created_by"),
            IndexModel("is_deleted"),
            IndexModel([("created_by", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("overall_status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("dispatch_status", ASCENDING), ("created_at", DESCENDING)]),
        ]


class ExecutionTaskCaseDoc(Document):
    """执行任务-用例明细。"""

    task_id: str = Field(..., description="平台任务 ID")
    case_id: str = Field(..., description="测试用例业务 ID")
    case_snapshot: Dict[str, Any] = Field(default_factory=dict, description="用例快照")
    status: str = Field(default="QUEUED", description="用例执行状态")
    progress_percent: Optional[float] = None
    step_total: int = 0
    step_passed: int = 0
    step_failed: int = 0
    step_skipped: int = 0
    last_seq: int = 0
    last_event_id: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_task_cases"
        indexes = [
            IndexModel([("task_id", ASCENDING), ("case_id", ASCENDING)], unique=True),
            IndexModel([("task_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel("task_id"),
            IndexModel("case_id"),
        ]


class ExecutionEventDoc(Document):
    """回调事件审计表。"""

    task_id: str = Field(..., description="平台任务 ID")
    event_id: str = Field(..., description="事件唯一 ID")
    event_type: str = Field(..., description="事件类型")
    seq: int = Field(..., description="事件序号")
    source_time: Optional[datetime] = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    processed: bool = Field(default=False)
    process_error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_events"
        indexes = [
            IndexModel([("task_id", ASCENDING), ("event_id", ASCENDING)], unique=True),
            IndexModel([("task_id", ASCENDING), ("seq", ASCENDING)]),
            IndexModel("received_at"),
        ]


class ExecutionTaskModel(BaseModel):
    id: Optional[str] = None
    task_id: str
    external_task_id: Optional[str] = None
    framework: str
    dispatch_status: str
    overall_status: str
    request_payload: Dict[str, Any]
    dispatch_response: Dict[str, Any]
    dispatch_error: Optional[str] = None
    created_by: str
    case_count: int
    reported_case_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_callback_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionTaskCaseModel(BaseModel):
    id: Optional[str] = None
    task_id: str
    case_id: str
    case_snapshot: Dict[str, Any]
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

    model_config = ConfigDict(from_attributes=True)


class ExecutionEventModel(BaseModel):
    id: Optional[str] = None
    task_id: str
    event_id: str
    event_type: str
    seq: int
    source_time: Optional[datetime] = None
    received_at: datetime
    raw_payload: Dict[str, Any]
    processed: bool
    process_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
