"""执行任务调度器。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.modules.execution.application.task_dispatch_service import ExecutionDispatchService
from app.modules.execution.repository.schedule_repository import ExecutionTaskScheduleRepository
from app.modules.execution.shared.execution_context import execution_scope
from app.modules.execution.shared.execution_log import ExecutionNode, elog
from app.shared.context import trace_scope

DEFAULT_LEASE_SECONDS = 600
MAX_RECOVER_PER_TICK = 100


class ExecutionTaskScheduler:
    """扫描、claim 并下发到期的定时执行任务。"""

    def __init__(
        self,
        dispatch_service: ExecutionDispatchService | None = None,
        schedule_repository: ExecutionTaskScheduleRepository | None = None,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> None:
        self._dispatch_service = dispatch_service or ExecutionDispatchService()
        self._repository = schedule_repository or ExecutionTaskScheduleRepository()
        self._lease_seconds = lease_seconds
        self._owner = uuid.uuid4().hex

    async def dispatch_due_tasks(self, limit: int = 50) -> int:
        """回收过期租约，扫描并下发本轮到期任务。"""
        now = datetime.now(timezone.utc)
        recovered = await self._repository.recover_expired_leases(now, MAX_RECOVER_PER_TICK)
        if recovered:
            elog(
                "info",
                ExecutionNode.SCHEDULER_TICK,
                "recovered stuck scheduled tasks",
                outcome="recovered",
                recovered_count=recovered,
            )

        docs = await self._repository.list_due_tasks(now, limit)
        async with trace_scope(request_id=f"scheduler:{now.isoformat()}"):
            elog(
                "debug",
                ExecutionNode.SCHEDULER_TICK,
                "scanned scheduled execution tasks",
                due_count=len(docs),
                limit=limit,
                now=now.isoformat(),
            )

            dispatched_count = 0
            for candidate in docs:
                task = await self._repository.claim_due_task(
                    candidate.task_id,
                    now=now,
                    owner=self._owner,
                    lease_seconds=self._lease_seconds,
                )
                if task is None:
                    continue
                dispatched_count += await self._dispatch_claimed_task(task)

            if dispatched_count:
                elog(
                    "info",
                    ExecutionNode.SCHEDULER_TICK,
                    "dispatched scheduled execution tasks",
                    outcome="success",
                    dispatched_count=dispatched_count,
                )
        return dispatched_count

    async def _dispatch_claimed_task(self, task) -> int:
        """下发已取得租约的任务；失败时保留租约，等待超时回收。"""
        async with execution_scope(
            task_id=task.task_id,
            agent_id=task.agent_id,
            node=ExecutionNode.SCHEDULER_TICK.value,
        ):
            try:
                command = await self._dispatch_service.build_task_dispatch_command(task, 0)
                elog(
                    "info",
                    ExecutionNode.SCHEDULER_TICK,
                    "dispatching due scheduled execution task",
                    outcome="started",
                    planned_at=str(task.planned_at),
                    case_id=command.dispatch_case_id,
                )
                task.current_case_id = command.dispatch_case_id
                task.current_case_index = 0
                await self._dispatch_service.dispatch_existing_task(task, command)
                return 1
            except Exception as exc:  # noqa: BLE001 - 单任务失败不能中断整批调度
                elog(
                    "error",
                    ExecutionNode.SCHEDULER_TICK,
                    "dispatch failed, will retry after lease expiry",
                    outcome="failed",
                    task_id=task.task_id,
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )
                return 0
