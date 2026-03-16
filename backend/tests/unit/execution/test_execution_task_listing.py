from datetime import datetime, timezone

import pytest

from app.modules.execution.application.execution_service import ExecutionService


class _FakeQuery:
    def __init__(self, docs):
        self._docs = docs
        self.sort_value = None
        self.skip_value = None
        self.limit_value = None

    def sort(self, value):
        self.sort_value = value
        return self

    def skip(self, value):
        self.skip_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    async def to_list(self):
        return self._docs


@pytest.mark.asyncio
async def test_list_tasks_builds_filters_and_serializes(monkeypatch):
    service = ExecutionService()
    now = datetime(2026, 3, 16, tzinfo=timezone.utc)
    fake_docs = [
        type(
            "TaskDoc",
            (),
            {
                "task_id": "ET-2026-000001",
                "external_task_id": "EXT-ET-2026-000001",
                "framework": "pytest",
                "agent_id": "agent-01",
                "dispatch_channel": "HTTP",
                "dedup_key": "dedup-1",
                "schedule_type": "SCHEDULED",
                "schedule_status": "PENDING",
                "dispatch_status": "PENDING",
                "consume_status": "PENDING",
                "overall_status": "QUEUED",
                "case_count": 2,
                "planned_at": now,
                "triggered_at": None,
                "created_at": now,
                "updated_at": now,
            },
        )()
    ]
    query_holder = {}

    def fake_find(query):
        query_holder["query"] = query
        query_holder["chain"] = _FakeQuery(fake_docs)
        return query_holder["chain"]

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find",
        fake_find,
    )

    result = await service.list_tasks(
        schedule_status="pending",
        dispatch_status="pending",
        agent_id="agent-01",
        framework="pytest",
        limit=10,
        offset=5,
    )

    assert query_holder["query"]["schedule_status"] == "PENDING"
    assert query_holder["query"]["dispatch_status"] == "PENDING"
    assert query_holder["query"]["agent_id"] == "agent-01"
    assert query_holder["chain"].sort_value == "-created_at"
    assert query_holder["chain"].skip_value == 5
    assert query_holder["chain"].limit_value == 10
    assert result[0]["task_id"] == "ET-2026-000001"
    assert result[0]["framework"] == "pytest"
