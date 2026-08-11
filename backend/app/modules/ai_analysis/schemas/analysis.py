"""AI 分析 Pydantic Schemas"""

from pydantic import BaseModel, Field


class PendingTaskAnalysisItem(BaseModel):
    """待处理任务分析项。"""

    id: str
    kind: str
    title: str
    category: str
    status: str
    next_step: str
    period: str
    period_label: str
    period_detail: str


class PendingTaskAnalysisStats(BaseModel):
    """待处理任务统计快照。"""

    total: int = 0
    plan_count: int = 0
    workflow_count: int = 0
    risk_count: int = 0
    risk_percent: int = 0
    overdue_count: int = 0
    today_count: int = 0
    soon_count: int = 0
    normal_count: int = 0
    unset_count: int = 0


class PendingTaskAnalysisRequest(BaseModel):
    """待处理任务 AI 分析请求。"""

    user_id: str
    stats: PendingTaskAnalysisStats
    category_stats: list[dict] = Field(default_factory=list)
    items: list[PendingTaskAnalysisItem] = Field(default_factory=list)


class PendingTaskAnomaly(BaseModel):
    """待处理任务异常。"""

    severity: str = Field(default="info", description="critical/warning/info")
    title: str
    detail: str
    related_ids: list[str] = Field(default_factory=list)


class PendingTaskPriorityItem(BaseModel):
    """建议优先处理的任务。"""

    id: str
    title: str
    reason: str
    priority: str = Field(default="P2")


class PendingTaskAnalysisResult(BaseModel):
    """待处理任务 AI 分析结果。"""

    summary: str
    health_score: int = Field(..., ge=0, le=100)
    anomalies: list[PendingTaskAnomaly] = Field(default_factory=list)
    priority_items: list[PendingTaskPriorityItem] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
