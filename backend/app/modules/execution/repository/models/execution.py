"""测试执行域数据模型（Beanie ODM）。"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import Document, Insert, Save, before_event
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class ExecutionTaskDoc(Document):
    """执行任务主表。

    这是任务“当前态”的主记录，保存调度、下发、消费和整体执行状态，
    也保存当前推进到哪一条 case。
    """

    task_id: str = Field(..., description="平台任务唯一 ID")
    source_task_id: Optional[str] = Field(None, description="重跑来源任务 ID")
    framework: str = Field(..., description="外部框架标识")
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    dispatch_channel: str = Field(default="RABBITMQ", description="下发通道")
    dedup_key: Optional[str] = Field(None, description="业务去重键")
    schedule_type: str = Field(default="IMMEDIATE", description="调度类型")
    schedule_status: str = Field(default="READY", description="调度状态，仅描述是否已到触发阶段")
    dispatch_status: str = Field(default="PENDING", description="下发状态")
    consume_status: str = Field(default="PENDING", description="消费状态")
    overall_status: str = Field(default="QUEUED", description="总体执行状态")
    request_payload: Dict[str, Any] = Field(default_factory=dict, description="下发请求快照")
    dispatch_response: Dict[str, Any] = Field(default_factory=dict, description="下发响应快照")
    dispatch_error: Optional[str] = Field(None, description="下发失败原因")
    created_by: str = Field(..., description="创建者 user_id")
    case_count: int = Field(default=0, description="任务包含用例数量")
    reported_case_count: int = Field(default=0, description="已上报进度的用例数")
    started_case_count: int = Field(default=0, description="已开始执行的用例数")
    finished_case_count: int = Field(default=0, description="已完成执行的用例数")
    passed_case_count: int = Field(default=0, description="已通过的用例数")
    failed_case_count: int = Field(default=0, description="已失败的用例数")
    progress_percent: Optional[float] = Field(default=None, description="任务进度百分比")
    current_case_id: Optional[str] = Field(None, description="当前下发中的测试用例 ID")
    current_case_index: int = Field(default=0, description="当前下发中的测试用例序号")
    planned_at: Optional[datetime] = Field(None, description="计划触发时间（UTC），定时任务使用")
    triggered_at: Optional[datetime] = Field(None, description="任务首次真正触发下发的时间（UTC）")
    started_at: Optional[datetime] = Field(None, description="任务开始执行时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="任务结束时间（UTC）")
    last_callback_at: Optional[datetime] = Field(None, description="最近一次收到执行端回调的时间（UTC）")
    last_event_at: Optional[datetime] = Field(None, description="最近一次 Kafka 事件时间（UTC）")
    last_event_id: Optional[str] = Field(None, description="最近一次 Kafka 事件 ID")
    last_event_type: Optional[str] = Field(None, description="最近一次 Kafka 事件类型")
    last_event_phase: Optional[str] = Field(None, description="最近一次 Kafka 事件阶段")
    consumed_at: Optional[datetime] = Field(None, description="下游消费者确认消费该任务的时间（UTC）")
    is_deleted: bool = Field(default=False, description="逻辑删除标记")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="记录创建时间（UTC）",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="记录最近更新时间（UTC）",
    )

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_tasks"
        indexes = [
            IndexModel("task_id", unique=True),
            IndexModel("source_task_id"),
            IndexModel("framework"),
            IndexModel("agent_id"),
            IndexModel("dispatch_channel"),
            IndexModel("dedup_key"),
            IndexModel("schedule_type"),
            IndexModel("schedule_status"),
            IndexModel("dispatch_status"),
            IndexModel("consume_status"),
            IndexModel("overall_status"),
            IndexModel("created_by"),
            IndexModel("is_deleted"),
            IndexModel([("dedup_key", ASCENDING), ("consume_status", ASCENDING)]),
            IndexModel([("schedule_status", ASCENDING), ("planned_at", ASCENDING)]),
            IndexModel([("created_by", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("overall_status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("dispatch_status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("task_id", ASCENDING), ("current_case_index", ASCENDING)]),
        ]


class ExecutionTaskCaseDoc(Document):
    """执行任务-用例明细。

    这是任务“当前态”的 case 工作表，保存每条 case 的顺序、即时状态和推进信息，
    供平台串行编排使用。
    """

    task_id: str = Field(..., description="平台任务 ID")
    case_id: str = Field(..., description="测试用例业务 ID")
    case_snapshot: Dict[str, Any] = Field(default_factory=dict, description="用例快照")
    order_no: int = Field(default=0, description="用例在任务中的顺序")
    dispatch_status: str = Field(default="PENDING", description="平台下发状态")
    dispatch_attempts: int = Field(default=0, description="平台下发次数")
    status: str = Field(default="QUEUED", description="用例执行状态")
    progress_percent: Optional[float] = Field(None, description="当前 case 执行进度百分比")
    step_total: int = Field(default=0, description="当前 case 总步骤数")
    step_passed: int = Field(default=0, description="当前 case 已通过步骤数")
    step_failed: int = Field(default=0, description="当前 case 已失败步骤数")
    step_skipped: int = Field(default=0, description="当前 case 已跳过步骤数")
    last_seq: int = Field(0, description="当前 case 已接受的最后一个事件序号")
    last_event_id: Optional[str] = Field(None, description="当前 case 最近一次处理的事件 ID")
    last_event_at: Optional[datetime] = Field(None, description="当前 case 最近一次事件时间（UTC）")
    event_count: int = Field(default=0, description="当前 case 事件数量")
    started_at: Optional[datetime] = Field(None, description="当前 case 开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="当前 case 结束时间（UTC）")
    dispatched_at: Optional[datetime] = Field(None, description="当前 case 最近一次被平台下发的时间（UTC）")
    failure_message: Optional[str] = Field(None, description="当前 case 失败信息")
    nodeid: Optional[str] = Field(None, description="测试节点标识")
    project_tag: Optional[str] = Field(None, description="项目标签")
    case_title_snapshot: Optional[str] = Field(None, description="用例标题快照")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="当前 case 扩展结果")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="记录创建时间（UTC）",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="记录最近更新时间（UTC）",
    )

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_task_cases"
        indexes = [
            IndexModel([("task_id", ASCENDING), ("case_id", ASCENDING)], unique=True),
            IndexModel([("task_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("task_id", ASCENDING), ("order_no", ASCENDING)]),
            IndexModel("task_id"),
            IndexModel("case_id"),
        ]


class ExecutionAgentDoc(Document):
    """执行代理注册表。

    保存可接收执行任务的 agent 注册信息和心跳状态。
    """

    agent_id: str = Field(..., description="代理唯一标识")
    hostname: str = Field(..., description="主机名")
    ip: str = Field(..., description="代理IP")
    port: Optional[int] = Field(None, description="代理服务端口")
    base_url: Optional[str] = Field(None, description="代理服务基地址")
    region: str = Field(..., description="所属区域")
    status: str = Field(default="ONLINE", description="代理状态")
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="首次注册或最近一次注册时间（UTC）",
    )
    last_heartbeat_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="最近一次心跳时间（UTC）",
    )
    heartbeat_ttl_seconds: int = Field(default=90, description="心跳过期阈值（秒）")
    is_deleted: bool = Field(default=False, description="逻辑删除标记")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="记录创建时间（UTC）",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="记录最近更新时间（UTC）",
    )

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
