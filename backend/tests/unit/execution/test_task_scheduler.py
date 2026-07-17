"""执行任务调度器编排测试。"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.execution.service.task_scheduler import ExecutionTaskScheduler


def _task(task_id: str):
    return SimpleNamespace(
        task_id=task_id,
        agent_id="agent-x",
        planned_at=datetime.now(timezone.utc),
        current_case_id=None,
        current_case_index=0,
    )


def _scheduler(*, candidates, claims, dispatch_error: Exception | None = None):
    repository = AsyncMock()
    repository.recover_expired_leases.return_value = 0
    repository.list_due_tasks.return_value = candidates
    repository.claim_due_task.side_effect = claims

    dispatch_service = AsyncMock()
    dispatch_service.build_task_dispatch_command.return_value = SimpleNamespace(dispatch_case_id="C1")
    if dispatch_error:
        dispatch_service.dispatch_existing_task.side_effect = dispatch_error

    scheduler = ExecutionTaskScheduler(
        dispatch_service=dispatch_service,
        schedule_repository=repository,
    )
    return scheduler, repository, dispatch_service


async def test_dispatches_only_tasks_claimed_by_current_instance():
    scheduler, repository, dispatch_service = _scheduler(
        candidates=[_task("T1"), _task("T2")],
        claims=[_task("T1"), None],
    )

    count = await scheduler.dispatch_due_tasks()

    assert count == 1
    assert repository.claim_due_task.await_count == 2
    dispatch_service.dispatch_existing_task.assert_awaited_once()


async def test_dispatch_failure_is_isolated_and_not_counted():
    scheduler, _, _ = _scheduler(
        candidates=[_task("T1")],
        claims=[_task("T1")],
        dispatch_error=RuntimeError("broker down"),
    )

    assert await scheduler.dispatch_due_tasks() == 0


async def test_failure_of_one_task_does_not_block_following_tasks():
    first = _task("T1")
    second = _task("T2")
    scheduler, _, dispatch_service = _scheduler(
        candidates=[first, second],
        claims=[first, second],
    )
    dispatch_service.dispatch_existing_task.side_effect = [RuntimeError("broker down"), None]

    assert await scheduler.dispatch_due_tasks() == 1
    assert dispatch_service.dispatch_existing_task.await_count == 2
