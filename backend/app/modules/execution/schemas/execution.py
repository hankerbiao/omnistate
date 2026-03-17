"""测试执行 API 模型。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DispatchCaseItem(BaseModel):
    case_id: str = Field(..., description="测试用例业务 ID")


class DispatchTaskRequest(BaseModel):
    framework: str = Field(..., description="执行框架标识")
    agent_id: Optional[str] = Field(None, description="目标代理 ID，HTTP 直连模式下必填")
    trigger_source: Optional[str] = Field(default="manual", description="触发来源")
    schedule_type: str = Field(default="IMMEDIATE", description="调度类型：IMMEDIATE/SCHEDULED")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）")
    callback_url: Optional[str] = Field(None, description="框架回调地址")
    dut: Dict[str, Any] = Field(default_factory=dict)
    cases: List[DispatchCaseItem] = Field(default_factory=list)
    runtime_config: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_dispatch_request(self) -> "DispatchTaskRequest":
        case_ids = [item.case_id for item in self.cases]
        if not case_ids:
            raise ValueError("cases cannot be empty")
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("cases must not contain duplicate case_id")
        if self.schedule_type.upper() not in {"IMMEDIATE", "SCHEDULED"}:
            raise ValueError("schedule_type must be IMMEDIATE or SCHEDULED")
        return self


class DispatchTaskResponse(BaseModel):
    task_id: str
    external_task_id: Optional[str] = None
    agent_id: Optional[str] = None
    dispatch_channel: str
    dedup_key: Optional[str] = None
    schedule_type: str
    schedule_status: str
    dispatch_status: str
    consume_status: str
    overall_status: str
    case_count: int
    current_case_id: Optional[str] = None
    current_case_index: int = 0
    planned_at: Optional[datetime] = None
    triggered_at: Optional[datetime] = None
    created_at: datetime


class ExecutionTaskListItem(BaseModel):
    task_id: str
    external_task_id: Optional[str] = None
    framework: str
    agent_id: Optional[str] = None
    dispatch_channel: str
    dedup_key: Optional[str] = None
    schedule_type: str
    schedule_status: str
    dispatch_status: str
    consume_status: str
    overall_status: str
    case_count: int
    latest_run_no: int = 0
    current_run_no: int = 0
    current_case_id: Optional[str] = None
    current_case_index: int = 0
    planned_at: Optional[datetime] = None
    triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ExecutionEventReportRequest(BaseModel):
    event_id: str = Field(..., min_length=1, description="事件唯一标识")
    event_type: str = Field(..., min_length=1, description="事件类型")
    seq: int = Field(default=0, ge=0, description="事件序号")
    source_time: Optional[datetime] = Field(None, description="事件源时间（UTC）")
    payload: Dict[str, Any] = Field(default_factory=dict, description="原始事件载荷")

    model_config = ConfigDict(extra="forbid")


class ExecutionEventReportResponse(BaseModel):
    task_id: str
    event_id: str
    event_type: str
    seq: int
    received_at: datetime
    processed: bool


class ExecutionCaseStatusReportRequest(BaseModel):
    status: str = Field(..., min_length=1, description="用例执行状态")
    event_id: Optional[str] = Field(None, description="事件唯一标识")
    seq: int = Field(default=0, ge=0, description="事件序号")
    progress_percent: Optional[float] = Field(None, ge=0, le=100, description="进度百分比")
    step_total: Optional[int] = Field(None, ge=0)
    step_passed: Optional[int] = Field(None, ge=0)
    step_failed: Optional[int] = Field(None, ge=0)
    step_skipped: Optional[int] = Field(None, ge=0)
    started_at: Optional[datetime] = Field(None, description="用例开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="用例结束时间（UTC）")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="执行结果扩展信息")

    model_config = ConfigDict(extra="forbid")


class ExecutionCaseStatusReportResponse(BaseModel):
    task_id: str
    case_id: str
    status: str
    progress_percent: Optional[float] = None
    step_total: int
    step_passed: int
    step_failed: int
    step_skipped: int
    last_seq: int
    accepted: bool
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: datetime


class ExecutionTaskCompleteRequest(BaseModel):
    status: str = Field(..., min_length=1, description="任务最终状态")
    event_id: Optional[str] = Field(None, description="完成事件ID")
    seq: int = Field(default=0, ge=0, description="完成事件序号")
    finished_at: Optional[datetime] = Field(None, description="任务结束时间（UTC）")
    summary: Dict[str, Any] = Field(default_factory=dict, description="任务结果摘要")
    error_message: Optional[str] = Field(None, description="失败原因")
    executor: Optional[str] = Field(None, description="执行器标识")

    model_config = ConfigDict(extra="forbid")


class ExecutionTaskCompleteResponse(BaseModel):
    task_id: str
    overall_status: str
    dispatch_status: str
    consume_status: str
    reported_case_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_callback_at: Optional[datetime] = None
    updated_at: datetime


class ExecutionTaskRunSummary(BaseModel):
    task_id: str
    run_no: int
    trigger_type: str
    triggered_by: str
    overall_status: str
    dispatch_status: str
    case_count: int
    reported_case_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ExecutionTaskRunCaseResult(BaseModel):
    case_id: str
    order_no: int
    status: str
    dispatch_status: str
    dispatch_attempts: int
    progress_percent: Optional[float] = None
    step_total: int
    step_passed: int
    step_failed: int
    step_skipped: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_data: Dict[str, Any] = Field(default_factory=dict)


class ExecutionTaskRunDetail(ExecutionTaskRunSummary):
    dispatch_channel: str
    dispatch_response: Dict[str, Any] = Field(default_factory=dict)
    dispatch_error: Optional[str] = None
    last_callback_at: Optional[datetime] = None
    cases: List[ExecutionTaskRunCaseResult] = Field(default_factory=list)


class UpdateScheduledTaskRequest(BaseModel):
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    planned_at: Optional[datetime] = Field(None, description="新的计划执行时间（UTC）")
    callback_url: Optional[str] = Field(None, description="框架回调地址")
    dut: Optional[Dict[str, Any]] = Field(None)
    cases: Optional[List[DispatchCaseItem]] = Field(None, description="新的测试用例列表")
    runtime_config: Optional[Dict[str, Any]] = Field(None)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_schedule_update(self) -> "UpdateScheduledTaskRequest":
        if self.cases is None:
            return self
        case_ids = [item.case_id for item in self.cases]
        if not case_ids:
            raise ValueError("cases cannot be empty")
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("cases must not contain duplicate case_id")
        return self


class ScheduledTaskMutationResponse(BaseModel):
    task_id: str
    external_task_id: Optional[str] = None
    agent_id: Optional[str] = None
    dispatch_channel: Optional[str] = None
    dedup_key: Optional[str] = None
    schedule_type: str
    schedule_status: str
    dispatch_status: str
    overall_status: str
    consume_status: Optional[str] = None
    case_count: Optional[int] = None
    current_case_id: Optional[str] = None
    current_case_index: int = 0
    planned_at: Optional[datetime] = None
    triggered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: datetime


class ConsumeAckRequest(BaseModel):
    consumer_id: Optional[str] = Field(None, description="消费者标识")

    model_config = ConfigDict(extra="forbid")


class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, description="代理唯一标识")
    hostname: str = Field(..., min_length=1, description="主机名")
    ip: str = Field(..., min_length=1, description="代理IP")
    port: Optional[int] = Field(None, ge=1, le=65535, description="代理端口")
    base_url: Optional[str] = Field(None, description="代理基地址")
    region: str = Field(..., min_length=1, description="区域")
    status: str = Field(default="ONLINE", description="代理状态")
    heartbeat_ttl_seconds: int = Field(default=90, ge=10, le=3600, description="心跳租约秒数")

    model_config = ConfigDict(extra="forbid")


class AgentHeartbeatRequest(BaseModel):
    status: str = Field(default="ONLINE", description="代理状态")

    model_config = ConfigDict(extra="forbid")


class ExecutionAgentResponse(BaseModel):
    agent_id: str
    hostname: str
    ip: str
    port: Optional[int] = None
    base_url: Optional[str] = None
    region: str
    status: str
    registered_at: datetime
    last_heartbeat_at: datetime
    heartbeat_ttl_seconds: int
    is_online: bool
    created_at: datetime
    updated_at: datetime
