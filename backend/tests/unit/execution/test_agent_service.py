"""执行代理服务单元测试。"""

from datetime import datetime, timezone

from app.modules.execution.application.agent_service import ExecutionAgentService


def test_resolve_agent_runtime_status_accepts_aware_datetimes() -> None:
    """代理服务应能独立解析心跳状态，不依赖任务服务 mixin。"""
    status, is_online = ExecutionAgentService._resolve_agent_runtime_status(
        status="ONLINE",
        last_heartbeat_at=datetime(2026, 4, 30, 8, 0, 0, tzinfo=timezone.utc),
        heartbeat_ttl_seconds=90,
        now=datetime(2026, 4, 30, 8, 0, 30, tzinfo=timezone.utc),
    )

    assert status == "ONLINE"
    assert is_online is True
