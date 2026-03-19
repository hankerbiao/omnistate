"""Kafka event schemas for the execution module."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecutionResultEvent(BaseModel):
    """Execution result event consumed from Kafka."""

    task_id: str
    status: str
    result_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    executor: str | None = None
    complete_time: str | None = None
