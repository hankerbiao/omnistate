"""项目 Pydantic 请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


# ── 请求模型 ──────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    """创建项目请求。"""

    name: str = Field(..., description="项目名称", min_length=1, max_length=200)
    key: str = Field(..., description="项目短标识", min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    description: Optional[str] = Field(None, description="项目描述", max_length=2000)
    priority: Optional[str] = Field("P2", description="优先级 P0/P1/P2")
    owner_id: Optional[str] = Field(None, description="项目负责人 user_id")
    start_date: Optional[datetime] = Field(None, description="计划开始时间")
    end_date: Optional[datetime] = Field(None, description="计划结束时间")
    target_version: Optional[str] = Field(None, description="目标版本号")
    tags: List[str] = Field(default_factory=list, description="项目标签")

    model_config = ConfigDict(extra="forbid")


class UpdateProjectRequest(BaseModel):
    """更新项目请求。"""

    name: Optional[str] = Field(None, description="项目名称", min_length=1, max_length=200)
    key: Optional[str] = Field(None, description="项目短标识", min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    description: Optional[str] = Field(None, description="项目描述", max_length=2000)
    status: Optional[str] = Field(None, description="项目状态 (active|archived)")
    priority: Optional[str] = Field(None, description="优先级 P0/P1/P2")
    owner_id: Optional[str] = Field(None, description="项目负责人 user_id")
    start_date: Optional[datetime] = Field(None, description="计划开始时间")
    end_date: Optional[datetime] = Field(None, description="计划结束时间")
    target_version: Optional[str] = Field(None, description="目标版本号")
    tags: Optional[List[str]] = Field(None, description="项目标签")

    model_config = ConfigDict(extra="forbid")


# ── 响应模型 ──────────────────────────────────────────────────────────────

class OwnerBrief(BaseModel):
    """负责人简要信息。"""

    user_id: str
    username: str = ""


class ProjectResponse(BaseModel):
    """项目响应（基本信息）。"""

    project_id: str
    key: str
    name: str
    description: Optional[str] = None
    status: str
    priority: str = "P2"
    owner_id: Optional[str] = None
    owner: Optional[OwnerBrief] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StatsBreakdown(BaseModel):
    """统计明细。"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0


class ExecutionTaskBreakdown(BaseModel):
    """执行任务统计明细。"""

    total: int = 0
    done: int = 0
    running: int = 0
    failed: int = 0
    pending: int = 0
    progress: float = 0.0


class AssigneeDistribution(BaseModel):
    """执行人分布。"""

    assignee_id: Optional[str] = None
    assignee_name: str = ""
    item_count: int = 0
    done_count: int = 0
    progress: float = 0.0


class ProjectStatsResponse(BaseModel):
    """项目统计响应。"""

    # 基础计数
    test_case_count: int = 0
    auto_case_count: int = 0
    requirement_count: int = 0
    plan_count: int = 0
    collection_count: int = 0

    # 执行进度
    task: ExecutionTaskBreakdown = Field(default_factory=ExecutionTaskBreakdown)
    task_progress: float = 0.0

    # 通过率
    manual_pass: StatsBreakdown = Field(default_factory=StatsBreakdown)
    auto_pass: StatsBreakdown = Field(default_factory=StatsBreakdown)
    coverage_rate: float = 0.0  # 需求覆盖率

    # 人员分布
    assignee_distribution: List[AssigneeDistribution] = Field(default_factory=list)


class ProjectListResponse(BaseModel):
    """项目列表响应。"""

    items: List[ProjectResponse]
    total: int


class ProjectDetailResponse(ProjectResponse):
    """项目详情响应（含统计）。"""

    stats: Optional[ProjectStatsResponse] = None
