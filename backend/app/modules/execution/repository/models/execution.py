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
    external_task_id: Optional[str] = Field(None, description="外部框架任务 ID")
    framework: str = Field(..., description="外部框架标识")
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    dispatch_channel: str = Field(default="KAFKA", description="下发通道")
    dedup_key: Optional[str] = Field(None, description="业务去重键")
    schedule_type: str = Field(default="IMMEDIATE", description="调度类型")
    schedule_status: str = Field(default="READY", description="调度状态")
    dispatch_status: str = Field(default="PENDING", description="下发状态")
    consume_status: str = Field(default="PENDING", description="消费状态")
    overall_status: str = Field(default="QUEUED", description="总体执行状态")
    request_payload: Dict[str, Any] = Field(default_factory=dict, description="下发请求快照")
    dispatch_response: Dict[str, Any] = Field(default_factory=dict, description="下发响应快照")
    dispatch_error: Optional[str] = Field(None, description="下发失败原因")
    created_by: str = Field(..., description="创建者 user_id")
    case_count: int = Field(default=0, description="任务包含用例数量")
    reported_case_count: int = Field(default=0, description="已上报进度的用例数")
    latest_run_no: int = Field(default=0, description="最近一次执行轮次")
    current_run_no: int = Field(default=0, description="当前正在执行的轮次")
    current_case_id: Optional[str] = Field(None, description="当前下发中的测试用例 ID")
    current_case_index: int = Field(default=0, description="当前下发中的测试用例序号")
    stop_mode: str = Field(default="NONE", description="停止模式")
    stop_requested_at: Optional[datetime] = Field(None, description="请求停止时间（UTC）")
    stop_requested_by: Optional[str] = Field(None, description="请求停止的用户 ID")
    stop_reason: Optional[str] = Field(None, description="停止原因")
    orchestration_lock: Optional[str] = Field(None, description="平台串行推进锁")
    planned_at: Optional[datetime] = Field(None, description="计划触发时间（UTC），定时任务使用")
    triggered_at: Optional[datetime] = Field(None, description="任务首次真正触发下发的时间（UTC）")
    started_at: Optional[datetime] = Field(None, description="任务开始执行时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="任务结束时间（UTC）")
    last_callback_at: Optional[datetime] = Field(None, description="最近一次收到执行端回调的时间（UTC）")
    consumed_at: Optional[datetime] = Field(None, description="下游消费者确认消费该任务的时间（UTC）")
    is_deleted: bool = Field(default=False, description="逻辑删除标记")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="记录创建时间（UTC）")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="记录最近更新时间（UTC）")

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
            IndexModel([("stop_mode", ASCENDING), ("created_at", DESCENDING)]),
        ]


class ExecutionTaskRunDoc(Document):
    """执行任务轮次记录。

    一个 task 可以执行多轮；该表保存某一轮 run 的任务级结果，
    用于区分“当前态”和“历史态”。
    """

    task_id: str = Field(..., description="平台任务 ID")
    run_no: int = Field(..., description="执行轮次，从 1 开始递增")
    trigger_type: str = Field(default="INITIAL", description="触发类型")
    triggered_by: str = Field(..., description="触发人 user_id")
    overall_status: str = Field(default="QUEUED", description="本轮总体状态")
    dispatch_status: str = Field(default="PENDING", description="本轮下发状态")
    dispatch_channel: str = Field(default="KAFKA", description="本轮下发通道")
    dispatch_response: Dict[str, Any] = Field(default_factory=dict, description="本轮最近一次下发响应")
    dispatch_error: Optional[str] = Field(None, description="本轮下发失败原因")
    case_count: int = Field(default=0, description="本轮用例数量")
    reported_case_count: int = Field(default=0, description="本轮已完成回报的用例数量")
    stop_mode: str = Field(default="NONE", description="本轮停止模式")
    stop_requested_at: Optional[datetime] = Field(None, description="本轮请求停止时间（UTC）")
    stop_requested_by: Optional[str] = Field(None, description="本轮请求停止的用户 ID")
    stop_reason: Optional[str] = Field(None, description="本轮停止原因")
    started_at: Optional[datetime] = Field(None, description="本轮任务开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="本轮任务结束时间（UTC）")
    last_callback_at: Optional[datetime] = Field(None, description="本轮最近一次回调时间（UTC）")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="本轮记录创建时间（UTC）")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="本轮记录最近更新时间（UTC）")

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_task_runs"
        indexes = [
            IndexModel([("task_id", ASCENDING), ("run_no", ASCENDING)], unique=True),
            IndexModel([("task_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("task_id", ASCENDING), ("overall_status", ASCENDING)]),
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
    last_seq: int = Field(0, description="当前 case 已接受的最后一个事件序号")
    last_event_id: Optional[str] = Field(None, description="当前 case 最近一次处理的事件 ID")
    started_at: Optional[datetime] = Field(None, description="当前 case 开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="当前 case 结束时间（UTC）")
    dispatched_at: Optional[datetime] = Field(None, description="当前 case 最近一次被平台下发的时间（UTC）")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="记录创建时间（UTC）")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="记录最近更新时间（UTC）")

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


class ExecutionTaskRunCaseDoc(Document):
    """执行任务轮次-用例结果。

    保存某个 task 在某一轮 run 中，每条 case 的历史执行结果。
    与 `ExecutionTaskCaseDoc` 不同，这里是历史快照，不承担当前编排职责。
    """

    task_id: str = Field(..., description="平台任务 ID")
    run_no: int = Field(..., description="执行轮次")
    case_id: str = Field(..., description="测试用例业务 ID")
    order_no: int = Field(default=0, description="用例顺序")
    case_snapshot: Dict[str, Any] = Field(default_factory=dict, description="用例快照")
    dispatch_status: str = Field(default="PENDING", description="本轮下发状态")
    dispatch_attempts: int = Field(default=0, description="本轮下发次数")
    status: str = Field(default="QUEUED", description="本轮执行状态")
    progress_percent: Optional[float] = Field(None, description="本轮该 case 的进度百分比")
    started_at: Optional[datetime] = Field(None, description="本轮该 case 开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="本轮该 case 结束时间（UTC）")
    dispatched_at: Optional[datetime] = Field(None, description="本轮该 case 最近一次被下发的时间（UTC）")
    last_seq: int = Field(default=0, description="本轮最后事件序号")
    last_event_id: Optional[str] = Field(None, description="本轮最后事件 ID")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="本轮扩展结果")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="本轮 case 结果记录创建时间（UTC）")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="本轮 case 结果记录最近更新时间（UTC）")

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_task_run_cases"
        indexes = [
            IndexModel([("task_id", ASCENDING), ("run_no", ASCENDING), ("case_id", ASCENDING)], unique=True),
            IndexModel([("task_id", ASCENDING), ("run_no", ASCENDING), ("order_no", ASCENDING)]),
            IndexModel([("task_id", ASCENDING), ("run_no", ASCENDING), ("status", ASCENDING)]),
        ]


class ExecutionEventDoc(Document):
    """回调事件审计表。

    保存执行端回调的原始事件，用于审计、排障和幂等处理。
    """

    task_id: str = Field(..., description="平台任务 ID")
    event_id: str = Field(..., description="事件唯一 ID")
    event_type: str = Field(..., description="事件类型")
    seq: int = Field(..., description="事件序号")
    source_time: Optional[datetime] = Field(None, description="事件在源端产生的时间（UTC）")
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="平台接收到该事件的时间（UTC）")
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="事件原始载荷")
    processed: bool = Field(default=False, description="该事件是否已被平台处理")
    process_error: Optional[str] = Field(None, description="事件处理失败时记录的错误信息")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="事件记录创建时间（UTC）")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="事件记录最近更新时间（UTC）")

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
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="首次注册或最近一次注册时间（UTC）")
    last_heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="最近一次心跳时间（UTC）")
    heartbeat_ttl_seconds: int = Field(default=90, description="心跳过期阈值（秒）")
    is_deleted: bool = Field(default=False, description="逻辑删除标记")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="记录创建时间（UTC）")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="记录最近更新时间（UTC）")

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
