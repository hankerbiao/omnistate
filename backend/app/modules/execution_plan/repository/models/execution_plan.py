"""执行计划 MongoDB 文档模型。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from beanie import Document, Insert, Save, before_event
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class ExecutionPlanDoc(Document):
    """测试执行计划。"""

    plan_id: str = Field(..., description="计划业务 ID")
    title: str = Field(..., description="计划标题")
    description: str = Field(default="", description="计划说明")
    status: str = Field(default="draft", description="draft|active|done|archived")
    start_date: Optional[str] = Field(None, description="计划开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="计划结束日期 YYYY-MM-DD")
    trigger_at: Optional[str] = Field(None, description="触发时间描述")
    created_by: str = Field(..., description="创建人 user_id")
    item_count: int = Field(default=0, description="条目总数")
    done_count: int = Field(default=0, description="已完成条目数")
    progress_percent: int = Field(default=0, description="进度 0-100")
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def _touch_updated_at(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_plans"
        indexes = [
            IndexModel("plan_id", unique=True),
            IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),
            IndexModel("is_deleted"),
        ]


class ExecutionPlanItemDoc(Document):
    """计划内单条用例执行项。"""

    item_id: str = Field(..., description="计划条目 ID")
    plan_id: str = Field(..., description="所属计划 ID")
    ref_type: str = Field(..., description="manual|auto")
    case_id: str = Field(..., description="manual: case_id; auto: auto_case_id")
    manual_case_id: Optional[str] = Field(None, description="auto 时关联的手工 case_id")
    case_title: str = Field(default="", description="用例标题快照")
    component: str = Field(default="", description="组件/分组标签")
    priority: str = Field(default="", description="优先级快照")
    assignee_id: Optional[str] = Field(None, description="执行人 user_id")
    status: str = Field(default="pending", description="pending|running|done|fail")
    order_no: int = Field(default=0, description="排序")
    execution_task_id: Optional[str] = Field(None, description="关联自动化任务 ID")
    result_id: Optional[str] = Field(None, description="关联手工结果 ID")
    archived_at: Optional[datetime] = Field(None, description="归档时间，null=未归档")
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def _touch_updated_at(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_plan_items"
        indexes = [
            IndexModel("item_id", unique=True),
            IndexModel([("plan_id", ASCENDING), ("order_no", ASCENDING)]),
            IndexModel([("assignee_id", ASCENDING), ("status", ASCENDING), ("updated_at", DESCENDING)]),
            IndexModel("execution_task_id"),
            IndexModel("is_deleted"),
        ]


class ManualExecutionResultDoc(Document):
    """手工执行回填结果。"""

    result_id: str = Field(..., description="结果 ID")
    item_id: str = Field(..., description="计划条目 ID")
    plan_id: str = Field(..., description="计划 ID")
    case_id: str = Field(..., description="手工用例 ID")
    passed: bool = Field(default=True)
    notes: str = Field(default="")
    severity: str = Field(default="normal")
    actual: str = Field(default="")
    expected: str = Field(default="")
    env: str = Field(default="")
    test_data: str = Field(default="")
    bug_id: str = Field(default="")
    actual_duration: str = Field(default="")
    attachments: List[str] = Field(default_factory=list)
    executed_by: str = Field(..., description="执行人 user_id")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def _touch_updated_at(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "manual_execution_results"
        indexes = [
            IndexModel("result_id", unique=True),
            IndexModel("item_id"),
            IndexModel([("plan_id", ASCENDING), ("case_id", ASCENDING)]),
            IndexModel("is_deleted"),
        ]
