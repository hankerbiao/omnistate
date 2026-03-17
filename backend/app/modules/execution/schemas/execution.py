"""测试执行 API 模型。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DispatchCaseItem(BaseModel):
    case_id: str = Field(..., description="测试用例业务 ID，用于标识本次任务包含的单条 case")


class DispatchTaskRequest(BaseModel):
    framework: str = Field(..., description="执行框架标识，例如 pytest、robot 等")
    agent_id: Optional[str] = Field(None, description="目标执行代理 ID；由平台路由到指定 agent 时使用")
    trigger_source: Optional[str] = Field(default="manual", description="触发来源，例如 manual、web_ui、schedule")
    schedule_type: str = Field(default="IMMEDIATE", description="调度类型，只允许 IMMEDIATE 或 SCHEDULED")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）；schedule_type 为 SCHEDULED 时必填")
    callback_url: Optional[str] = Field(None, description="执行端回调地址，用于上报任务/用例执行结果")
    dut: Dict[str, Any] = Field(default_factory=dict, description="被测对象信息快照，例如设备、环境、版本等")
    cases: List[DispatchCaseItem] = Field(default_factory=list, description="本次任务需要按顺序执行的测试用例列表")

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
    task_id: str = Field(..., description="平台内部任务 ID")
    external_task_id: Optional[str] = Field(None, description="对外暴露的任务 ID，供外部系统关联")
    agent_id: Optional[str] = Field(None, description="当前绑定的目标代理 ID")
    dispatch_channel: str = Field(..., description="任务实际下发通道，例如 KAFKA、HTTP")
    dedup_key: Optional[str] = Field(None, description="任务去重键，用于识别语义相同的未完成任务")
    schedule_type: str = Field(..., description="调度类型：IMMEDIATE 或 SCHEDULED")
    schedule_status: str = Field(..., description="调度状态，例如 PENDING、READY、TRIGGERED、CANCELLED")
    dispatch_status: str = Field(..., description="下发状态，例如 PENDING、DISPATCHED、DISPATCH_FAILED、COMPLETED")
    consume_status: str = Field(..., description="消费状态，表示下游执行端是否已确认消费任务")
    overall_status: str = Field(..., description="任务整体状态，例如 QUEUED、RUNNING、PASSED、FAILED")
    case_count: int = Field(..., description="任务包含的测试用例总数")
    current_case_id: Optional[str] = Field(None, description="当前正在执行或最近一次下发的测试用例 ID")
    current_case_index: int = Field(0, description="当前测试用例在任务内的顺序索引，从 0 开始")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）")
    triggered_at: Optional[datetime] = Field(None, description="任务首次真正触发下发的时间（UTC）")
    created_at: datetime = Field(..., description="任务创建时间（UTC）")


class ExecutionTaskListItem(BaseModel):
    task_id: str = Field(..., description="平台内部任务 ID")
    external_task_id: Optional[str] = Field(None, description="对外暴露的任务 ID")
    framework: str = Field(..., description="执行框架标识")
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    dispatch_channel: str = Field(..., description="当前任务使用的下发通道")
    dedup_key: Optional[str] = Field(None, description="任务去重键")
    schedule_type: str = Field(..., description="调度类型")
    schedule_status: str = Field(..., description="调度状态")
    dispatch_status: str = Field(..., description="下发状态")
    consume_status: str = Field(..., description="消费状态")
    overall_status: str = Field(..., description="任务整体状态")
    case_count: int = Field(..., description="任务包含的测试用例总数")
    latest_run_no: int = Field(0, description="该任务历史上最新的执行轮次编号")
    current_run_no: int = Field(0, description="当前正在查看或运行中的执行轮次编号")
    current_case_id: Optional[str] = Field(None, description="当前游标指向的测试用例 ID")
    current_case_index: int = Field(0, description="当前游标指向的测试用例顺序索引")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）")
    triggered_at: Optional[datetime] = Field(None, description="任务首次被触发执行的时间（UTC）")
    created_at: datetime = Field(..., description="任务创建时间（UTC）")
    updated_at: datetime = Field(..., description="任务最近更新时间（UTC）")


class ExecutionEventReportRequest(BaseModel):
    event_id: str = Field(..., min_length=1, description="事件唯一标识")
    event_type: str = Field(..., min_length=1, description="事件类型")
    seq: int = Field(default=0, ge=0, description="事件序号")
    source_time: Optional[datetime] = Field(None, description="事件源时间（UTC）")
    payload: Dict[str, Any] = Field(default_factory=dict, description="原始事件载荷")

    model_config = ConfigDict(extra="forbid")


class ExecutionEventReportResponse(BaseModel):
    task_id: str = Field(..., description="事件归属的任务 ID")
    event_id: str = Field(..., description="事件唯一标识")
    event_type: str = Field(..., description="事件类型，已做标准化处理")
    seq: int = Field(..., description="事件序号")
    received_at: datetime = Field(..., description="平台接收事件的时间（UTC）")
    processed: bool = Field(..., description="该事件是否已被平台处理")


class ExecutionCaseStatusReportRequest(BaseModel):
    status: str = Field(..., min_length=1, description="用例执行状态")
    event_id: Optional[str] = Field(None, description="事件唯一标识")
    seq: int = Field(default=0, ge=0, description="事件序号")
    progress_percent: Optional[float] = Field(None, ge=0, le=100, description="进度百分比")
    step_total: Optional[int] = Field(None, ge=0, description="当前 case 总步骤数")
    step_passed: Optional[int] = Field(None, ge=0, description="当前 case 已通过步骤数")
    step_failed: Optional[int] = Field(None, ge=0, description="当前 case 已失败步骤数")
    step_skipped: Optional[int] = Field(None, ge=0, description="当前 case 已跳过步骤数")
    started_at: Optional[datetime] = Field(None, description="用例开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="用例结束时间（UTC）")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="执行结果扩展信息")

    model_config = ConfigDict(extra="forbid")


class ExecutionCaseStatusReportResponse(BaseModel):
    task_id: str = Field(..., description="任务 ID")
    case_id: str = Field(..., description="测试用例 ID")
    status: str = Field(..., description="平台当前记录的用例状态")
    progress_percent: Optional[float] = Field(None, description="当前记录的进度百分比")
    step_total: int = Field(..., description="当前记录的总步骤数")
    step_passed: int = Field(..., description="当前记录的通过步骤数")
    step_failed: int = Field(..., description="当前记录的失败步骤数")
    step_skipped: int = Field(..., description="当前记录的跳过步骤数")
    last_seq: int = Field(..., description="平台已接受的最后一个事件序号")
    accepted: bool = Field(..., description="本次上报是否被接受；旧序号事件会被拒绝覆盖")
    started_at: Optional[datetime] = Field(None, description="用例开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="用例结束时间（UTC）")
    updated_at: datetime = Field(..., description="当前状态最近更新时间（UTC）")


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
    task_id: str = Field(..., description="任务 ID")
    overall_status: str = Field(..., description="任务最终整体状态")
    dispatch_status: str = Field(..., description="任务最终下发状态")
    consume_status: str = Field(..., description="任务最终消费状态")
    reported_case_count: int = Field(..., description="已进入终态并被平台统计到的 case 数量")
    started_at: Optional[datetime] = Field(None, description="任务开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="任务结束时间（UTC）")
    last_callback_at: Optional[datetime] = Field(None, description="最近一次回调到达平台的时间（UTC）")
    updated_at: datetime = Field(..., description="任务记录最近更新时间（UTC）")


class ExecutionTaskRunSummary(BaseModel):
    task_id: str = Field(..., description="任务 ID")
    run_no: int = Field(..., description="执行轮次编号，从 1 开始递增")
    trigger_type: str = Field(..., description="触发类型，例如 INITIAL、RETRY")
    triggered_by: str = Field(..., description="触发本轮执行的用户或系统标识")
    overall_status: str = Field(..., description="本轮执行整体状态")
    dispatch_status: str = Field(..., description="本轮执行下发状态")
    case_count: int = Field(..., description="本轮执行包含的测试用例数量")
    reported_case_count: int = Field(..., description="本轮执行中已完成回报的 case 数量")
    started_at: Optional[datetime] = Field(None, description="本轮执行开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="本轮执行结束时间（UTC）")
    created_at: datetime = Field(..., description="本轮历史记录创建时间（UTC）")
    updated_at: datetime = Field(..., description="本轮历史记录最近更新时间（UTC）")


class ExecutionTaskRunCaseResult(BaseModel):
    case_id: str = Field(..., description="测试用例 ID")
    order_no: int = Field(..., description="测试用例在任务中的执行顺序，从 0 开始")
    status: str = Field(..., description="该 case 在本轮执行中的状态")
    dispatch_status: str = Field(..., description="该 case 在本轮执行中的下发状态")
    dispatch_attempts: int = Field(..., description="该 case 在本轮中累计下发尝试次数")
    progress_percent: Optional[float] = Field(None, description="该 case 当前或最终进度百分比")
    step_total: int = Field(..., description="该 case 总步骤数")
    step_passed: int = Field(..., description="该 case 已通过步骤数")
    step_failed: int = Field(..., description="该 case 已失败步骤数")
    step_skipped: int = Field(..., description="该 case 已跳过步骤数")
    started_at: Optional[datetime] = Field(None, description="该 case 开始时间（UTC）")
    finished_at: Optional[datetime] = Field(None, description="该 case 结束时间（UTC）")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="该 case 的扩展结果数据")


class ExecutionTaskRunDetail(ExecutionTaskRunSummary):
    dispatch_channel: str = Field(..., description="本轮执行实际使用的下发通道")
    dispatch_response: Dict[str, Any] = Field(default_factory=dict, description="下发返回的扩展响应数据")
    dispatch_error: Optional[str] = Field(None, description="下发失败或执行阶段记录的错误信息")
    last_callback_at: Optional[datetime] = Field(None, description="本轮最近一次回调时间（UTC）")
    cases: List[ExecutionTaskRunCaseResult] = Field(default_factory=list, description="本轮各测试用例的执行结果明细")


class UpdateScheduledTaskRequest(BaseModel):
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    planned_at: Optional[datetime] = Field(None, description="新的计划执行时间（UTC）")
    callback_url: Optional[str] = Field(None, description="框架回调地址")
    dut: Optional[Dict[str, Any]] = Field(None, description="新的被测对象信息快照")
    cases: Optional[List[DispatchCaseItem]] = Field(None, description="新的测试用例列表")

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
    task_id: str = Field(..., description="任务 ID")
    external_task_id: Optional[str] = Field(None, description="外部任务 ID")
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    dispatch_channel: Optional[str] = Field(None, description="任务当前使用的下发通道")
    dedup_key: Optional[str] = Field(None, description="任务去重键")
    schedule_type: str = Field(..., description="调度类型")
    schedule_status: str = Field(..., description="调度状态")
    dispatch_status: str = Field(..., description="下发状态")
    overall_status: str = Field(..., description="任务整体状态")
    consume_status: Optional[str] = Field(None, description="消费状态")
    case_count: Optional[int] = Field(None, description="任务包含的测试用例数量")
    current_case_id: Optional[str] = Field(None, description="当前游标指向的测试用例 ID")
    current_case_index: int = Field(0, description="当前游标指向的测试用例顺序索引")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）")
    triggered_at: Optional[datetime] = Field(None, description="任务实际触发时间（UTC）")
    created_at: Optional[datetime] = Field(None, description="任务创建时间（UTC）")
    updated_at: datetime = Field(..., description="任务最近更新时间（UTC）")


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
    agent_id: str = Field(..., description="代理唯一标识")
    hostname: str = Field(..., description="代理所在主机名")
    ip: str = Field(..., description="代理 IP 地址")
    port: Optional[int] = Field(None, description="代理监听端口")
    base_url: Optional[str] = Field(None, description="代理对外服务基地址")
    region: str = Field(..., description="代理所在区域")
    status: str = Field(..., description="代理当前状态，例如 ONLINE、OFFLINE")
    registered_at: datetime = Field(..., description="代理首次注册或最近一次注册时间（UTC）")
    last_heartbeat_at: datetime = Field(..., description="最近一次心跳时间（UTC）")
    heartbeat_ttl_seconds: int = Field(..., description="心跳租约时长，超过后可判定离线")
    is_online: bool = Field(..., description="平台根据心跳和租约推导的在线状态")
    created_at: datetime = Field(..., description="代理记录创建时间（UTC）")
    updated_at: datetime = Field(..., description="代理记录最近更新时间（UTC）")
