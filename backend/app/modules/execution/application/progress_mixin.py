"""执行任务轮次同步与停止收口能力。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.execution.application.constants import (
    FINAL_CASE_STATUSES,
    STOP_MODE_NONE,
)
from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
    ExecutionTaskRunDoc,
)


class ExecutionProgressMixin:
    """处理任务停止后的收口与 run 同步。"""

    async def _mark_task_stopped_after_current_case(self, task_doc: ExecutionTaskDoc) -> None:
        """在当前 case 完成后执行优雅停止，不再继续下发下一条。"""
        completed_case_count = await ExecutionTaskCaseDoc.find({
            "task_id": task_doc.task_id,
            "status": {"$in": list(FINAL_CASE_STATUSES)},
        }).count()
        task_doc.reported_case_count = completed_case_count
        task_doc.current_case_id = None
        task_doc.current_case_index = min(task_doc.current_case_index + 1, task_doc.case_count)
        task_doc.finished_at = datetime.now(timezone.utc)
        task_doc.last_callback_at = task_doc.finished_at
        task_doc.overall_status = "STOPPED"
        if task_doc.dispatch_status != "DISPATCH_FAILED":
            task_doc.dispatch_status = "COMPLETED"
        task_doc.orchestration_lock = None
        await task_doc.save()
        await self._sync_run_from_task(task_doc)

    async def _sync_run_from_task(self, task_doc: ExecutionTaskDoc) -> None:
        """把任务当前结果同步到当前执行轮次。"""
        if task_doc.current_run_no <= 0:
            return

        run_doc = await ExecutionTaskRunDoc.find_one({
            "task_id": task_doc.task_id,
            "run_no": task_doc.current_run_no,
        })
        if not run_doc:
            return

        self._assign_fields(
            run_doc,
            overall_status=task_doc.overall_status,
            dispatch_status=task_doc.dispatch_status,
            dispatch_channel=task_doc.dispatch_channel,
            dispatch_response=dict(task_doc.dispatch_response or {}),
            dispatch_error=task_doc.dispatch_error,
            reported_case_count=task_doc.reported_case_count,
            stop_mode=getattr(task_doc, "stop_mode", STOP_MODE_NONE),
            stop_requested_at=getattr(task_doc, "stop_requested_at", None),
            stop_requested_by=getattr(task_doc, "stop_requested_by", None),
            stop_reason=getattr(task_doc, "stop_reason", None),
            started_at=task_doc.started_at,
            finished_at=task_doc.finished_at,
            last_callback_at=task_doc.last_callback_at,
        )
        await run_doc.save()
