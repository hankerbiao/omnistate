"""执行计划 API 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanTaskResultPayload(BaseModel):
    """对齐前端 PlanTaskResult。"""

    passed: bool = True
    notes: str = ""
    severity: str = "normal"
    actual: str = ""
    expected: str = ""
    env: str = ""
    test_data: str = ""
    bug_id: str = ""
    actual_duration: str = ""
    attachments: List[str] = Field(default_factory=list)
    executed_at: Optional[datetime] = None

    model_config = ConfigDict(extra="forbid")


class CreatePlanRequest(BaseModel):
    title: str = Field(..., description="计划标题")
    description: str = ""
    status: str = Field(default="draft", description="draft|active|done|archived")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    trigger_at: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class UpdatePlanRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    trigger_at: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class PlanListItem(BaseModel):
    plan_id: str
    title: str
    description: str = ""
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    trigger_at: Optional[str] = None
    created_by: str
    item_count: int = 0
    done_count: int = 0
    progress_percent: int = 0
    created_at: datetime
    updated_at: datetime


class PlanItemInput(BaseModel):
    ref_type: str = Field(..., description="manual|auto")
    case_id: str = Field(..., description="manual: case_id; auto: auto_case_id")
    assignee_id: Optional[str] = None
    component: str = ""
    order_no: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class AddPlanItemsRequest(BaseModel):
    items: List[PlanItemInput] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class UpdatePlanItemRequest(BaseModel):
    assignee_id: Optional[str] = None
    status: Optional[str] = None
    component: Optional[str] = None
    order_no: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class PlanItemResponse(BaseModel):
    """对齐前端 PlanTask。"""

    item_id: str
    plan_id: str
    plan_title: str = ""
    case_id: str
    case_title: str = ""
    ref_type: str
    component: str = ""
    priority: str = ""
    assignee_id: Optional[str] = None
    status: str
    order_no: int = 0
    execution_task_id: Optional[str] = None
    result: Optional[PlanTaskResultPayload] = None


class PlanDetailResponse(PlanListItem):
    items: List[PlanItemResponse] = Field(default_factory=list)


class SubmitManualResultRequest(PlanTaskResultPayload):
    model_config = ConfigDict(extra="forbid")


class ManualResultResponse(PlanTaskResultPayload):
    result_id: str
    item_id: str
    plan_id: str
    case_id: str
    executed_by: str


class PlanItemDispatchRequest(BaseModel):
    """计划内单条自动化下发，字段对齐 DispatchTaskRequest 子集。"""

    agent_id: Optional[str] = None
    schedule_type: str = "IMMEDIATE"
    planned_at: Optional[datetime] = None
    category: Optional[str] = None
    project_tag: Optional[str] = None
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    pytest_options: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class BatchDispatchRequest(BaseModel):
    item_ids: List[str] = Field(default_factory=list)
    agent_id: Optional[str] = None
    schedule_type: str = "IMMEDIATE"
    planned_at: Optional[datetime] = None
    category: Optional[str] = None
    project_tag: Optional[str] = None
    pytest_options: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
