from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from app.modules.execution.application.worker_presence import (  # noqa: E402
    ensure_kafka_worker_available,
    get_kafka_worker_health,
)


@pytest.mark.asyncio
async def test_get_kafka_worker_health_returns_offline_when_missing(monkeypatch):
    class FakeExecutionAgentDoc:
        @staticmethod
        async def find_one(query):
            return None

    import app.modules.execution.application.worker_presence as worker_presence_module

    monkeypatch.setattr(worker_presence_module, "ExecutionAgentDoc", FakeExecutionAgentDoc)

    health = await get_kafka_worker_health()

    assert health["status"] == "OFFLINE"
    assert "not registered" in health["message"]


@pytest.mark.asyncio
async def test_ensure_kafka_worker_available_raises_when_heartbeat_expired(monkeypatch):
    expired_doc = SimpleNamespace(
        agent_id="execution-kafka-worker",
        status="ONLINE",
        last_heartbeat_at=datetime.now(timezone.utc) - timedelta(seconds=120),
        heartbeat_ttl_seconds=30,
    )

    class FakeExecutionAgentDoc:
        @staticmethod
        async def find_one(query):
            return expired_doc

    import app.modules.execution.application.worker_presence as worker_presence_module

    monkeypatch.setattr(worker_presence_module, "ExecutionAgentDoc", FakeExecutionAgentDoc)

    with pytest.raises(RuntimeError, match="offline"):
        await ensure_kafka_worker_available()


@pytest.mark.asyncio
async def test_ensure_kafka_worker_available_accepts_online_worker(monkeypatch):
    online_doc = SimpleNamespace(
        agent_id="execution-kafka-worker",
        status="ONLINE",
        last_heartbeat_at=datetime.now(timezone.utc),
        heartbeat_ttl_seconds=30,
    )

    class FakeExecutionAgentDoc:
        @staticmethod
        async def find_one(query):
            return online_doc

    import app.modules.execution.application.worker_presence as worker_presence_module

    monkeypatch.setattr(worker_presence_module, "ExecutionAgentDoc", FakeExecutionAgentDoc)

    await ensure_kafka_worker_available()


@pytest.mark.asyncio
async def test_get_kafka_worker_health_accepts_naive_heartbeat(monkeypatch):
    naive_online_doc = SimpleNamespace(
        agent_id="execution-kafka-worker",
        status="ONLINE",
        last_heartbeat_at=datetime.now(timezone.utc).replace(tzinfo=None),
        heartbeat_ttl_seconds=30,
    )

    class FakeExecutionAgentDoc:
        @staticmethod
        async def find_one(query):
            return naive_online_doc

    import app.modules.execution.application.worker_presence as worker_presence_module

    monkeypatch.setattr(worker_presence_module, "ExecutionAgentDoc", FakeExecutionAgentDoc)

    health = await get_kafka_worker_health()

    assert health["status"] == "ONLINE"
