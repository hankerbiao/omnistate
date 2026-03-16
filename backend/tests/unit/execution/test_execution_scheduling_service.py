from datetime import datetime, timezone

import pytest

from app.modules.execution.application.execution_service import ExecutionService


def test_normalize_schedule_defaults_to_immediate():
    schedule_type, planned_at, schedule_status, should_dispatch_now = ExecutionService._normalize_schedule(
        None,
        None,
        now=datetime(2026, 3, 16, tzinfo=timezone.utc),
    )

    assert schedule_type == "IMMEDIATE"
    assert planned_at is None
    assert schedule_status == "READY"
    assert should_dispatch_now is True


def test_normalize_schedule_requires_planned_at_for_scheduled():
    with pytest.raises(ValueError, match="planned_at is required"):
        ExecutionService._normalize_schedule(
            "SCHEDULED",
            None,
            now=datetime(2026, 3, 16, tzinfo=timezone.utc),
        )


def test_normalize_schedule_keeps_future_task_pending():
    schedule_type, planned_at, schedule_status, should_dispatch_now = ExecutionService._normalize_schedule(
        "SCHEDULED",
        datetime(2026, 3, 17, tzinfo=timezone.utc),
        now=datetime(2026, 3, 16, tzinfo=timezone.utc),
    )

    assert schedule_type == "SCHEDULED"
    assert planned_at == datetime(2026, 3, 17, tzinfo=timezone.utc)
    assert schedule_status == "PENDING"
    assert should_dispatch_now is False
