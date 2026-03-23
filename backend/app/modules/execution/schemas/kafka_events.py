"""Kafka event schemas for the execution module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExecutionResultEvent(BaseModel):
    """Execution result event consumed from Kafka."""

    task_id: str
    status: str
    result_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    executor: str | None = None
    complete_time: str | None = None


class TestEvent(BaseModel):
    """Single test execution event from Kafka."""

    schema_name: str = Field(alias="schema")
    event_id: str
    task_id: str
    timestamp: datetime
    event_type: str
    phase: str | None = None
    status: str | None = None
    event_seq: int | None = Field(default=None, alias="seq")
    assert_name: str | None = Field(default=None, alias="name")
    total_cases: int = 0
    started_cases: int = 0
    finished_cases: int = 0
    failed_cases: int = 0
    case_id: str | None = None
    case_title: str | None = None
    project_tag: str | None = None
    nodeid: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(populate_by_name=True)

    @field_validator("schema_name")
    @classmethod
    def validate_schema_name(cls, value: str) -> str:
        if not value.endswith("-test-event@1"):
            raise ValueError("test event schema must end with -test-event@1")
        return value


class RawTestEventEnvelope(BaseModel):
    """Raw Kafka payload for test-events topic, supporting single and batch envelopes."""

    payload: dict[str, Any]
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def wrap_raw_payload(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("Kafka test event payload must be a JSON object")
        return {"payload": value}
