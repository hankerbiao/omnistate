"""定时任务调度 Repository 测试。"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from beanie import UpdateResponse

from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.repository.schedule_repository import (
    PENDING,
    READY,
    ExecutionTaskScheduleRepository,
)


def _query_with_to_list(result):
    query = MagicMock()
    query.sort.return_value = query
    query.limit.return_value = query
    query.to_list = AsyncMock(return_value=result)
    return query


async def test_claim_due_task_uses_full_filter_and_lease():
    repository = ExecutionTaskScheduleRepository()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    query = MagicMock()
    query.update = AsyncMock(return_value=SimpleNamespace(task_id="T1"))

    with patch.object(ExecutionTaskDoc, "find_one", return_value=query) as find_one:
        result = await repository.claim_due_task(
            "T1",
            now=now,
            owner="worker-1",
            lease_seconds=600,
        )

    assert result.task_id == "T1"
    filters = find_one.call_args.args[0]
    assert filters == {
        "task_id": "T1",
        "schedule_type": "SCHEDULED",
        "schedule_status": PENDING,
        "planned_at": {"$lte": now},
        "is_deleted": False,
    }
    update = query.update.await_args.args[0]["$set"]
    assert update == {
        "schedule_status": READY,
        "claim_owner": "worker-1",
        "lease_until": now + timedelta(seconds=600),
        "last_claimed_at": now,
    }
    assert query.update.await_args.kwargs["response_type"] == UpdateResponse.NEW_DOCUMENT


async def test_recover_expired_leases_updates_selected_ids_in_one_batch():
    repository = ExecutionTaskScheduleRepository()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    docs = [SimpleNamespace(id="id-1"), SimpleNamespace(id="id-2")]
    collection = MagicMock()
    collection.update_many = AsyncMock(return_value=SimpleNamespace(modified_count=2))

    with patch.object(ExecutionTaskDoc, "find", return_value=_query_with_to_list(docs)), \
         patch.object(ExecutionTaskDoc, "get_pymongo_collection", return_value=collection):
        count = await repository.recover_expired_leases(now, limit=100)

    assert count == 2
    filters, update = collection.update_many.await_args.args
    assert filters["_id"] == {"$in": ["id-1", "id-2"]}
    assert filters["schedule_status"] == READY
    assert filters["lease_until"] == {"$lt": now}
    assert update["$set"] == {
        "schedule_status": PENDING,
        "claim_owner": None,
        "lease_until": None,
    }


async def test_recover_expired_leases_skips_update_when_nothing_found():
    repository = ExecutionTaskScheduleRepository()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    collection = MagicMock()
    collection.update_many = AsyncMock()

    with patch.object(ExecutionTaskDoc, "find", return_value=_query_with_to_list([])), \
         patch.object(ExecutionTaskDoc, "get_pymongo_collection", return_value=collection):
        assert await repository.recover_expired_leases(now, limit=100) == 0

    collection.update_many.assert_not_awaited()
