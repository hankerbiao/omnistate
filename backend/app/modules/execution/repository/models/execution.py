"""测试执行域数据模型（Beanie ODM）。"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import Document, Insert, Save, before_event
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class ExecutionTaskDoc(Document):
    """执行任务主表。"""

    task_id: str = Field(..., description="平台任务唯一 ID")
    external_task_id: Optional[str] = Field(None, description="外部框架任务 ID")
    framework: str = Field(..., description="外部框架标识")
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    dispatch_channel: str = Field(default="KAFKA", description="下发通道")
    dedup_key: Optional[str] = Field(None, description="业务去重键")
    dispatch_status: str = Field(default="PENDING", description="下发状态")
    consume_status: str = Field(default="PENDING", description="消费状态")
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
    consumed_at: Optional[datetime] = None
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
            IndexModel("agent_id"),
            IndexModel("dispatch_channel"),
            IndexModel("dedup_key"),
            IndexModel("dispatch_status"),
            IndexModel("consume_status"),
            IndexModel("overall_status"),
            IndexModel("created_by"),
            IndexModel("is_deleted"),
            IndexModel([("dedup_key", ASCENDING), ("consume_status", ASCENDING)]),
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


class ExecutionAgentDoc(Document):
    """执行代理注册表。"""

    agent_id: str = Field(..., description="代理唯一标识")
    hostname: str = Field(..., description="主机名")
    ip: str = Field(..., description="代理IP")
    port: Optional[int] = Field(None, description="代理服务端口")
    base_url: Optional[str] = Field(None, description="代理服务基地址")
    region: str = Field(..., description="所属区域")
    status: str = Field(default="ONLINE", description="代理状态")
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    heartbeat_ttl_seconds: int = Field(default=90, description="心跳过期阈值（秒）")
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_agents"
        indexes = [
            IndexModel("agent_id", unique=True),
            IndexModel("status"),
            IndexModel("region"),
            IndexModel("last_heartbeat_at"),
            IndexModel("is_deleted"),
            IndexModel([("status", ASCENDING), ("last_heartbeat_at", DESCENDING)]),
            IndexModel([("region", ASCENDING), ("status", ASCENDING)]),
        ]
