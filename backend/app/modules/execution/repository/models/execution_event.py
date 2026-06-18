"""Execution event archive model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.shared.core.document_mixins import TimestampedDocumentMixin


class ExecutionEventDoc(Document, TimestampedDocumentMixin):
    """Archive raw execution events from Kafka for idempotency and auditing."""

    event_id: str = Field(..., description="事件唯一 ID")
    task_id: str = Field(..., description="任务 ID")
    case_id: str | None = Field(default=None, description="测试用例 ID")
    topic: str = Field(..., description="Kafka topic")
    schema_name: str = Field(..., description="事件 schema 名称")
    event_type: str = Field(..., description="事件类型")
    phase: str | None = Field(default=None, description="事件阶段")
    event_seq: int | None = Field(default=None, description="事件顺序号")
    event_status: str | None = Field(default=None, description="事件状态")
    event_timestamp: datetime = Field(..., description="事件原始时间（UTC）")
    payload: dict[str, Any] = Field(default_factory=dict, description="原始事件载荷")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Kafka 元数据")
    processed: bool = Field(default=True, description="是否处理成功")
    process_error: str | None = Field(default=None, description="处理错误")
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="入库时间（UTC）",
    )

    class Settings:
        name = "execution_events"
        indexes = [
            IndexModel("event_id", unique=True),
            IndexModel([("task_id", ASCENDING), ("event_timestamp", DESCENDING)]),
            IndexModel([("task_id", ASCENDING), ("case_id", ASCENDING)]),
            IndexModel([("topic", ASCENDING), ("event_timestamp", DESCENDING)]),
        ]
