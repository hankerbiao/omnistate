"""测试执行 API 模型。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    planned_at: Optional[datetime] = None
    triggered_at: Optional[datetime] = None
    created_at: datetime


class UpdateScheduledTaskRequest(BaseModel):
    agent_id: Optional[str] = Field(None, description="目标代理 ID")
    planned_at: Optional[datetime] = Field(None, description="新的计划执行时间（UTC）")
    callback_url: Optional[str] = Field(None, description="框架回调地址")
    dut: Optional[Dict[str, Any]] = Field(None)
    cases: Optional[List[DispatchCaseItem]] = Field(None, description="新的测试用例列表")
    runtime_config: Optional[Dict[str, Any]] = Field(None)

    model_config = ConfigDict(extra="forbid")


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
