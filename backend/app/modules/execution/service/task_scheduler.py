"""执行任务调度器。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
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
            command = DispatchExecutionTaskCommand(
                task_id=task_doc.task_id,
                external_task_id=task_doc.external_task_id or f"EXT-{task_doc.task_id}",
                framework=task_doc.framework,
                agent_id=task_doc.agent_id,
                trigger_source=task_doc.request_payload.get("trigger_source", "scheduled"),
                created_by=task_doc.created_by,
                case_ids=[case["case_id"] for case in task_doc.request_payload.get("cases", [])],
                schedule_type=task_doc.schedule_type,
                planned_at=self._service._ensure_utc_datetime(task_doc.planned_at) if task_doc.planned_at else None,
                callback_url=task_doc.request_payload.get("callback_url"),
                dut=task_doc.request_payload.get("dut"),
                runtime_config=task_doc.request_payload.get("runtime_config"),
                kafka_task_data=task_doc.request_payload,
            )
            task_doc.schedule_status = "READY"
            await task_doc.save()
            await self._service._dispatch_existing_task(task_doc, command)
            dispatched_count += 1

        return dispatched_count
