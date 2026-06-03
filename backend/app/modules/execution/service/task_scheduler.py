"""执行任务调度器。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.execution.application.constants import ScheduleStatus
from app.modules.execution.application.task_dispatch_service import ExecutionDispatchService
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.shared.execution_context import execution_scope
from app.modules.execution.shared.execution_log import ExecutionNode, elog
from app.shared.context import trace_scope


class ExecutionTaskScheduler:
    """扫描并触发到期的定时执行任务。"""

    def __init__(self, dispatch_service: ExecutionDispatchService | None = None) -> None:
        self._dispatch_service = dispatch_service or ExecutionDispatchService()

    async def dispatch_due_tasks(self, limit: int = 50) -> int:
        now = datetime.now(timezone.utc)
        docs = await ExecutionTaskDoc.find({
            "schedule_type": "SCHEDULED",
            "schedule_status": ScheduleStatus.PENDING,
            "planned_at": {"$lte": now},
            "is_deleted": False,
        }).sort("planned_at").limit(limit).to_list()

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
            for task_doc in docs:
                async with execution_scope(
                    task_id=task_doc.task_id,
                    agent_id=task_doc.agent_id,
                    node=ExecutionNode.SCHEDULER_TICK.value,
                ):
                    command = await self._dispatch_service.build_task_dispatch_command(task_doc, 0)
                    elog(
                        "info",
                        ExecutionNode.SCHEDULER_TICK,
                        "dispatching due scheduled execution task",
                        outcome="started",
                        planned_at=str(task_doc.planned_at),
                        case_id=command.dispatch_case_id,
                    )
                    task_doc.current_case_id = command.dispatch_case_id
                    task_doc.current_case_index = 0
                    task_doc.schedule_status = ScheduleStatus.READY
                    await task_doc.save()
                    await self._dispatch_service.dispatch_existing_task(task_doc, command)
                    dispatched_count += 1

            if dispatched_count:
                elog(
                    "info",
                    ExecutionNode.SCHEDULER_TICK,
                    "dispatched scheduled execution tasks",
                    outcome="success",
                    dispatched_count=dispatched_count,
                )
        return dispatched_count
