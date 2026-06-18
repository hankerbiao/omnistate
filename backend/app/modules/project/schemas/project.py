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

    model_config = ConfigDict(extra="forbid")


class UpdateProjectRequest(BaseModel):
    """更新项目请求。"""

    name: Optional[str] = Field(None, description="项目名称", min_length=1, max_length=200)
    key: Optional[str] = Field(None, description="项目短标识", min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    description: Optional[str] = Field(None, description="项目描述", max_length=2000)
    status: Optional[str] = Field(None, description="项目状态 (active|archived)")

    model_config = ConfigDict(extra="forbid")


# ── 响应模型 ──────────────────────────────────────────────────────────────

class ProjectResponse(BaseModel):
    """项目响应（基本信息）。"""

    project_id: str
    key: str
    name: str
    description: Optional[str] = None
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectStatsResponse(BaseModel):
    """项目统计响应。"""

    test_case_count: int = 0
    auto_case_count: int = 0
    requirement_count: int = 0
    plan_count: int = 0
    task_count: int = 0
    task_done_count: int = 0
    task_progress: float = 0.0
    collection_count: int = 0


class ProjectListResponse(BaseModel):
    """项目列表响应。"""

    items: List[ProjectResponse]
    total: int


class ProjectDetailResponse(ProjectResponse):
    """项目详情响应（含统计）。"""

    stats: Optional[ProjectStatsResponse] = None
