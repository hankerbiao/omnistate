from datetime import datetime, timezone

from app.modules.execution.application.execution_service import ExecutionService


def test_ensure_utc_datetime_converts_naive_datetime():
    naive_value = datetime(2026, 3, 16, 12, 0, 0)

    normalized = ExecutionService._ensure_utc_datetime(naive_value)

    assert normalized.tzinfo == timezone.utc


def test_resolve_agent_runtime_status_marks_expired_agent_offline():
    now = datetime(2026, 3, 16, tzinfo=timezone.utc)
    status, is_online = ExecutionService._resolve_agent_runtime_status(
        status="ONLINE",
        last_heartbeat_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
        heartbeat_ttl_seconds=90,
        now=now,
    )

    assert status == "OFFLINE"
    assert is_online is False


def test_resolve_agent_runtime_status_handles_naive_lease_time():
    now = datetime(2026, 3, 16, tzinfo=timezone.utc)
    status, is_online = ExecutionService._resolve_agent_runtime_status(
        status="ONLINE",
        last_heartbeat_at=datetime(2026, 3, 15, 0, 0, 0),
        heartbeat_ttl_seconds=90,
        now=now,
    )

    assert status == "OFFLINE"
    assert is_online is False


def test_resolve_agent_runtime_status_keeps_busy_agent_online():
    now = datetime(2026, 3, 16, tzinfo=timezone.utc)
    status, is_online = ExecutionService._resolve_agent_runtime_status(
        status="ONLINE",
        last_heartbeat_at=datetime(2026, 3, 16, tzinfo=timezone.utc),
        heartbeat_ttl_seconds=3600,
        now=now,
    )

    assert status == "ONLINE"
    assert is_online is True
