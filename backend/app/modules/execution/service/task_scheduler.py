"""执行任务调度器。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.execution.application.execution_service import ExecutionService
from app.modules.execution.repository.models import ExecutionTaskDoc


class ExecutionTaskScheduler:
    """扫描并触发到期的定时执行任务。"""

    def __init__(self) -> None:
        self._service = ExecutionService()

    async def dispatch_due_tasks(self, limit: int = 50) -> int:
        now = datetime.now(timezone.utc)
        docs = await ExecutionTaskDoc.find({
            "schedule_type": "SCHEDULED",
            "schedule_status": "PENDING",
            "planned_at": {"$lte": now},
            "is_deleted": False,
        }).sort("planned_at").limit(limit).to_list()

        dispatched_count = 0
        for task_doc in docs:
            command = await self._service._build_task_dispatch_command(task_doc, 0)
            task_doc.current_case_id = command.dispatch_case_id
            task_doc.current_case_index = 0
            task_doc.schedule_status = "READY"
            await task_doc.save()
            await self._service._dispatch_existing_task(task_doc, command)
            dispatched_count += 1

        return dispatched_count
