"""Execution 平台侧业务轨迹日志。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from beanie import Document, Insert, Save, before_event
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class ExecutionBizLogDoc(Document):
    """平台侧 execution 业务节点时间线（非 Kafka 原始事件）。"""

    task_id: str = Field(..., description="任务 ID")
    case_id: str | None = Field(default=None, description="用例 ID")
    event_id: str | None = Field(default=None, description="事件 ID")
    node: str = Field(..., description="业务节点")
    action: str = Field(..., description="动作描述")
    outcome: str | None = Field(default=None, description="结果：success/failed/skipped 等")
    status_before: dict[str, Any] | None = Field(default=None, description="变更前状态快照")
    status_after: dict[str, Any] | None = Field(default=None, description="变更后状态快照")
    operator_id: str | None = Field(default=None, description="操作人 ID")
    request_id: str | None = Field(default=None, description="链路 request_id")
    detail: dict[str, Any] = Field(default_factory=dict, description="附加摘要")
    level: str = Field(default="INFO", description="日志级别")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="记录时间（UTC）",
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "execution_biz_logs"
        indexes = [
            IndexModel([("task_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("request_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel("node"),
            IndexModel("created_at"),
        ]
