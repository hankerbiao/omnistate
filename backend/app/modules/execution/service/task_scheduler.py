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
            case_ids = self._service._extract_case_ids_from_payload(task_doc.request_payload)
            auto_case_ids = self._service._extract_auto_case_ids_from_payload(task_doc.request_payload)
            if not auto_case_ids:
                auto_case_ids = await self._service.resolve_auto_case_ids_by_case_ids(case_ids)
            command = self._service._build_case_dispatch_command(
                task_doc=task_doc,
                case_ids=case_ids,
                auto_case_ids=auto_case_ids,
                dispatch_case_id=case_ids[0],
                dispatch_auto_case_id=auto_case_ids[0],
                dispatch_case_index=0,
            )
            task_doc.current_case_id = case_ids[0]
            task_doc.current_case_index = 0
            task_doc.schedule_status = "READY"
            await task_doc.save()
            await self._service._dispatch_existing_task(task_doc, command)
            dispatched_count += 1

        return dispatched_count
