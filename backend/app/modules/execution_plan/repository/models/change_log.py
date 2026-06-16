"""执行计划条目变更审计日志模型。"""
from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class ExecutionPlanChangeLogDoc(Document):
    """执行计划条目变更审计日志。

    记录执行计划条目的关键变更操作（改派、状态变更等），
    用于操作追溯和审计。
    """

    item_id: str = Field(..., description="计划条目 ID")
    plan_id: str = Field(..., description="所属计划 ID")
    action: str = Field(..., description="操作类型，如 REASSIGN")
    operator_id: str = Field(..., description="操作人 user_id")
    old_value: Optional[str] = Field(None, description="变更前值（如旧 assignee_id）")
    new_value: Optional[str] = Field(None, description="变更后值（如新 assignee_id）")
    remark: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "execution_plan_change_logs"
        indexes = [
            "item_id",
            "plan_id",
            "operator_id",
            [("item_id", -1), ("created_at", -1)],
        ]
