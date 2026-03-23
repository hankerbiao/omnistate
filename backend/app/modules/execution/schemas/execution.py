"""测试执行 API 模型。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DispatchCaseItem(BaseModel):
    auto_case_id: str = Field(
        ...,
        description="自动化测试用例业务 ID，用于标识本次任务包含的单条 case",
    )
    script_entity_id: Optional[str] = Field(
        None,
        description="自动化脚本实体 ID，可由前端显式透传；平台也会在后端二次校准",
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="该测试用例本次执行的参数配置",
    )
    script_path: Optional[str] = Field(None, description="执行端识别的脚本路径")
    script_name: Optional[str] = Field(None, description="执行端展示的脚本名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行端用例参数")

    model_config = ConfigDict(extra="forbid")


class DispatchTaskRequest(BaseModel):
    framework: str = Field(..., description="执行框架标识，例如 pytest、robot 等")
    dispatch_channel: Optional[str] = Field(None, description="下发通道，可选 KAFKA、RABBITMQ 或 HTTP")
    agent_id: Optional[str] = Field(None, description="目标执行代理 ID；由平台路由到指定 agent 时使用")
    trigger_source: Optional[str] = Field(default="manual", description="触发来源，例如 manual、web_ui、schedule")
    schedule_type: str = Field(default="IMMEDIATE", description="调度类型，只允许 IMMEDIATE 或 SCHEDULED")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）；schedule_type 为 SCHEDULED 时必填")
    callback_url: Optional[str] = Field(None, description="执行端回调地址，用于上报任务/用例执行结果")
    category: Optional[str] = Field(None, description="任务分类，例如 bmc")
    project_tag: Optional[str] = Field(None, description="项目标签，例如 universal")
    repo_url: Optional[str] = Field(None, description="代码仓库地址")
    branch: Optional[str] = Field(None, description="代码分支")
    pytest_options: Dict[str, Any] = Field(default_factory=dict, description="pytest 扩展选项")
    timeout: Optional[int] = Field(None, description="任务超时时间，单位秒")
    dut: Dict[str, Any] = Field(default_factory=dict, description="被测对象信息快照，例如设备、环境、版本等")
    cases: List[DispatchCaseItem] = Field(default_factory=list, description="本次任务需要按顺序执行的测试用例列表")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_dispatch_request(self) -> "DispatchTaskRequest":
        auto_case_ids = [item.auto_case_id for item in self.cases]
        if not auto_case_ids:
            raise ValueError("cases cannot be empty")
        if len(auto_case_ids) != len(set(auto_case_ids)):
            raise ValueError("cases must not contain duplicate auto_case_id")
        if self.schedule_type.upper() not in {"IMMEDIATE", "SCHEDULED"}:
            raise ValueError("schedule_type must be IMMEDIATE or SCHEDULED")
        if self.dispatch_channel and self.dispatch_channel.upper() not in {"KAFKA", "RABBITMQ", "HTTP"}:
            raise ValueError("dispatch_channel must be KAFKA, RABBITMQ or HTTP")
        if (self.dispatch_channel or "").upper() == "HTTP" and not self.agent_id:
            raise ValueError("agent_id is required when dispatch_channel is HTTP")
        return self


class RerunTaskRequest(BaseModel):
    framework: Optional[str] = Field(None, description="重跑任务使用的执行框架")
    dispatch_channel: Optional[str] = Field(None, description="重跑任务使用的下发通道")
    agent_id: Optional[str] = Field(None, description="重跑任务使用的目标代理 ID")
    trigger_source: Optional[str] = Field(None, description="触发来源")
    schedule_type: Optional[str] = Field(None, description="重跑调度类型")
    planned_at: Optional[datetime] = Field(None, description="重跑计划时间（UTC）")
    callback_url: Optional[str] = Field(None, description="执行端回调地址")
    category: Optional[str] = Field(None, description="任务分类")
    project_tag: Optional[str] = Field(None, description="项目标签")
    repo_url: Optional[str] = Field(None, description="代码仓库地址")
    branch: Optional[str] = Field(None, description="代码分支")
    pytest_options: Optional[Dict[str, Any]] = Field(None, description="pytest 扩展选项")
    timeout: Optional[int] = Field(None, description="任务超时时间，单位秒")
    dut: Optional[Dict[str, Any]] = Field(None, description="被测对象信息快照")
    cases: Optional[List[DispatchCaseItem]] = Field(None, description="重跑时覆盖的测试用例列表")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_rerun_request(self) -> "RerunTaskRequest":
        if self.schedule_type and self.schedule_type.upper() not in {"IMMEDIATE", "SCHEDULED"}:
            raise ValueError("schedule_type must be IMMEDIATE or SCHEDULED")
        if self.dispatch_channel and self.dispatch_channel.upper() not in {"KAFKA", "RABBITMQ", "HTTP"}:
            raise ValueError("dispatch_channel must be KAFKA, RABBITMQ or HTTP")
        if (self.dispatch_channel or "").upper() == "HTTP" and not self.agent_id:
            raise ValueError("agent_id is required when dispatch_channel is HTTP")
        if self.cases is not None:
            auto_case_ids = [item.auto_case_id for item in self.cases]
            if not auto_case_ids:
                raise ValueError("cases cannot be empty")
            if len(auto_case_ids) != len(set(auto_case_ids)):
                raise ValueError("cases must not contain duplicate auto_case_id")
        return self


class DispatchTaskResponse(BaseModel):
    task_id: str = Field(..., description="平台内部任务 ID")
    external_task_id: Optional[str] = Field(None, description="对外暴露的任务 ID，供外部系统关联")
    source_task_id: Optional[str] = Field(None, description="重跑来源任务 ID")
    agent_id: Optional[str] = Field(None, description="当前绑定的目标代理 ID")
    dispatch_channel: str = Field(..., description="任务实际下发通道，例如 KAFKA、HTTP")
    dedup_key: Optional[str] = Field(None, description="任务去重键，用于识别语义相同的未完成任务")
    schedule_type: str = Field(..., description="调度类型：IMMEDIATE 或 SCHEDULED")
    schedule_status: str = Field(..., description="调度状态，例如 PENDING、READY、TRIGGERED、CANCELLED；不表达下发结果")
    dispatch_status: str = Field(..., description="下发状态，例如 PENDING、DISPATCHED、DISPATCH_FAILED、COMPLETED")
    consume_status: str = Field(..., description="消费状态，表示下游执行端是否已确认消费任务")
    overall_status: str = Field(..., description="任务整体状态，例如 QUEUED、RUNNING、PASSED、FAILED")
    case_count: int = Field(..., description="任务包含的测试用例总数")
    auto_case_ids: List[str] = Field(default_factory=list, description="任务包含的自动化用例 ID 列表")
    current_case_id: Optional[str] = Field(None, description="当前正在执行或最近一次下发的测试用例 ID")
    current_auto_case_id: Optional[str] = Field(None, description="当前正在执行或最近一次下发的自动化用例 ID")
    current_case_index: int = Field(0, description="当前测试用例在任务内的顺序索引，从 0 开始")
    stop_mode: str = Field(default="NONE", description="停止模式")
    stop_requested_at: Optional[datetime] = Field(None, description="请求停止时间（UTC）")
    stop_requested_by: Optional[str] = Field(None, description="请求停止的用户 ID")
    stop_reason: Optional[str] = Field(None, description="停止原因")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）")
    triggered_at: Optional[datetime] = Field(None, description="任务首次真正触发下发的时间（UTC）")
    created_at: datetime = Field(..., description="任务创建时间（UTC）")


class ExecutionTaskListItem(BaseModel):
    task_id: str = Field(..., description="平台内部任务 ID")
    external_task_id: Optional[str] = Field(None, description="对外暴露的任务 ID")
    source_task_id: Optional[str] = Field(None, description="重跑来源任务 ID")
    framework: str = Field(..., description="执行框架标识")
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    dispatch_channel: str = Field(..., description="当前任务使用的下发通道")
    dedup_key: Optional[str] = Field(None, description="任务去重键")
    schedule_type: str = Field(..., description="调度类型")
    schedule_status: str = Field(..., description="调度状态，不表达下发结果")
    dispatch_status: str = Field(..., description="下发状态")
    consume_status: str = Field(..., description="消费状态")
    overall_status: str = Field(..., description="任务整体状态")
    case_count: int = Field(..., description="任务包含的测试用例总数")
    auto_case_ids: List[str] = Field(default_factory=list, description="任务包含的自动化用例 ID 列表")
    current_case_id: Optional[str] = Field(None, description="当前游标指向的测试用例 ID")
    current_auto_case_id: Optional[str] = Field(None, description="当前游标指向的自动化用例 ID")
    current_case_index: int = Field(0, description="当前游标指向的测试用例顺序索引")
    stop_mode: str = Field(default="NONE", description="停止模式")
    stop_requested_at: Optional[datetime] = Field(None, description="请求停止时间（UTC）")
    stop_requested_by: Optional[str] = Field(None, description="请求停止的用户 ID")
    stop_reason: Optional[str] = Field(None, description="停止原因")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）")
    triggered_at: Optional[datetime] = Field(None, description="任务首次被触发执行的时间（UTC）")
    created_at: datetime = Field(..., description="任务创建时间（UTC）")
    updated_at: datetime = Field(..., description="任务最近更新时间（UTC）")
    cases: List["ExecutionTaskListCaseItem"] = Field(default_factory=list, description="任务关联测试用例当前执行情况")


class ExecutionTaskListCaseItem(BaseModel):
    task_id: str = Field(..., description="任务 ID")
    case_id: str = Field(..., description="测试用例 ID")
    auto_case_id: Optional[str] = Field(None, description="自动化测试用例 ID")
    order_no: int = Field(..., description="任务内顺序")
    title: Optional[str] = Field(None, description="用例标题快照")
    status: str = Field(..., description="当前执行状态")
    progress_percent: Optional[float] = Field(None, description="当前执行进度")
    dispatch_status: str = Field(..., description="当前下发状态")
    dispatch_attempts: int = Field(..., description="下发次数")
    event_count: int = Field(..., description="事件数量")
    failure_message: Optional[str] = Field(None, description="失败原因")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    finished_at: Optional[datetime] = Field(None, description="结束时间")
    last_event_id: Optional[str] = Field(None, description="最近事件 ID")
    last_event_at: Optional[datetime] = Field(None, description="最近事件时间")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="扩展结果")


class ScheduledTaskMutationResponse(BaseModel):
    task_id: str = Field(..., description="任务 ID")
    external_task_id: Optional[str] = Field(None, description="外部任务 ID")
    source_task_id: Optional[str] = Field(None, description="重跑来源任务 ID")
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    dispatch_channel: Optional[str] = Field(None, description="任务当前使用的下发通道")
    dedup_key: Optional[str] = Field(None, description="任务去重键")
    schedule_type: str = Field(..., description="调度类型")
    schedule_status: str = Field(..., description="调度状态，不表达下发结果")
    dispatch_status: str = Field(..., description="下发状态")
    overall_status: str = Field(..., description="任务整体状态")
    consume_status: Optional[str] = Field(None, description="消费状态")
    case_count: Optional[int] = Field(None, description="任务包含的测试用例数量")
    current_case_id: Optional[str] = Field(None, description="当前游标指向的测试用例 ID")
    current_case_index: int = Field(0, description="当前游标指向的测试用例顺序索引")
    stop_mode: str = Field(default="NONE", description="停止模式")
    stop_requested_at: Optional[datetime] = Field(None, description="请求停止时间（UTC）")
    stop_requested_by: Optional[str] = Field(None, description="请求停止的用户 ID")
    stop_reason: Optional[str] = Field(None, description="停止原因")
    planned_at: Optional[datetime] = Field(None, description="计划执行时间（UTC）")
    triggered_at: Optional[datetime] = Field(None, description="任务实际触发时间（UTC）")
    created_at: Optional[datetime] = Field(None, description="任务创建时间（UTC）")
    updated_at: datetime = Field(..., description="任务最近更新时间（UTC）")


class StopTaskRequest(BaseModel):
    reason: Optional[str] = Field(None, description="停止原因")

    model_config = ConfigDict(extra="forbid")


class StopTaskResponse(BaseModel):
    task_id: str = Field(..., description="任务 ID")
    stop_mode: str = Field(..., description="停止模式")
    stop_requested_at: Optional[datetime] = Field(None, description="请求停止时间（UTC）")
    stop_requested_by: Optional[str] = Field(None, description="请求停止的用户 ID")
    stop_reason: Optional[str] = Field(None, description="停止原因")
    overall_status: str = Field(..., description="任务整体状态")
    current_case_id: Optional[str] = Field(None, description="当前执行中的测试用例 ID")
    current_case_index: int = Field(0, description="当前执行中的测试用例顺序索引")
    updated_at: datetime = Field(..., description="任务最近更新时间（UTC）")


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
