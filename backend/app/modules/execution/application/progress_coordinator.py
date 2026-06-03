"""任务执行进度协调器。

负责当前 case 完成后决定：任务收口，还是自动推进下一条 case。
"""
from __future__ import annotations

from typing import Any

from app.modules.execution.application.constants import (
    FINAL_CASE_STATUSES,
    DispatchStatus,
    OverallStatus,
)
from app.modules.execution.application.task_dispatch_service import ExecutionDispatchService
from app.modules.execution.shared.execution_log import ExecutionNode, elog


class ExecutionProgressCoordinator:
    """串行编排的核心协调器。"""

    def __init__(self, dispatch_service: ExecutionDispatchService | None = None) -> None:
        self._dispatch_service = dispatch_service or ExecutionDispatchService()

    async def advance_after_case_finish(
        self,
        task_doc: Any,
        case_doc: Any,
        event: Any,
        event_time: Any,
        resolved_case_status: str | None,
    ) -> None:
        """当前 case 完成后自动推进或收口。"""
        if event.event_type != "progress" or event.phase != "case_finish":
            return
        if case_doc is None or resolved_case_status not in FINAL_CASE_STATUSES:
            elog(
                "debug",
                ExecutionNode.TASK_ADVANCE,
                "skipping task auto-advance because case is not final",
                outcome="skipped",
                resolved_case_status=resolved_case_status,
                event_case_id=event.case_id,
            )
            return
        if event.case_id != getattr(task_doc, "current_case_id", None):
            elog(
                "debug",
                ExecutionNode.TASK_ADVANCE,
                "skipping task auto-advance because event case is not current",
                outcome="skipped",
                event_case_id=event.case_id,
                current_case_id=task_doc.current_case_id,
            )
            return

        next_case_index = getattr(task_doc, "current_case_index", 0) + 1
        if next_case_index >= task_doc.case_count:
            task_doc.current_case_id = None
            task_doc.current_case_index = task_doc.case_count
            task_doc.finished_at = event_time
            task_doc.last_callback_at = event_time
            task_doc.overall_status = OverallStatus.FAILED if task_doc.failed_case_count > 0 else OverallStatus.PASSED
            if getattr(task_doc, "dispatch_status", None) not in {DispatchStatus.DISPATCH_FAILED, DispatchStatus.PENDING}:
                task_doc.dispatch_status = DispatchStatus.COMPLETED
            await task_doc.save()
            elog(
                "info",
                ExecutionNode.TASK_COMPLETE,
                "execution task completed after final case",
                outcome=task_doc.overall_status,
                final_case_id=event.case_id,
                after={"overall_status": task_doc.overall_status},
            )
            return

        try:
            command = await self._dispatch_service.build_task_dispatch_command(
                task_doc, next_case_index
            )
        except Exception as exc:
            elog(
                "error",
                ExecutionNode.TASK_ADVANCE,
                "failed to build dispatch command for auto-advance",
                outcome="failed",
                next_case_index=next_case_index,
                error=str(exc),
            )
            task_doc.dispatch_status = DispatchStatus.DISPATCH_FAILED
            task_doc.dispatch_error = f"Auto-advance build failed: {exc}"
            task_doc.overall_status = OverallStatus.FAILED
            task_doc.finished_at = event_time
            await task_doc.save()
            return

        try:
            elog(
                "info",
                ExecutionNode.TASK_ADVANCE,
                "auto-dispatching next execution case",
                outcome="started",
                finished_case_id=event.case_id,
                next_case_id=command.dispatch_case_id,
                next_case_index=next_case_index,
            )
            await self._dispatch_service.dispatch_existing_task(task_doc, command)
        except Exception as exc:
            elog(
                "error",
                ExecutionNode.TASK_ADVANCE,
                "failed to dispatch next case during auto-advance",
                outcome="failed",
                next_case_id=command.dispatch_case_id,
                error=str(exc),
            )
            task_doc.dispatch_status = DispatchStatus.DISPATCH_FAILED
            task_doc.dispatch_error = f"Auto-advance dispatch failed: {exc}"
            task_doc.overall_status = OverallStatus.FAILED
            task_doc.finished_at = event_time
            await task_doc.save()
