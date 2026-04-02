from __future__ import annotations

from typing import Any

from app.modules.execution.application.constants import FINAL_CASE_STATUSES
from app.modules.execution.application.execution_service import ExecutionService
from app.shared.core.logger import log as logger


class ExecutionProgressCoordinator:
    def __init__(self, execution_service: ExecutionService | None = None) -> None:
        self._execution_service = execution_service or ExecutionService()

    async def advance_after_case_finish(
        self,
        task_doc: Any,
        case_doc: Any,
        event: Any,
        event_time: Any,
        resolved_case_status: str | None,
    ) -> None:
        if event.event_type != "progress" or event.phase != "case_finish":
            return
        if case_doc is None or resolved_case_status not in FINAL_CASE_STATUSES:
            logger.debug(
                "Skipping task auto-advance because case is not final: "
                f"task_id={task_doc.task_id}, case_id={event.case_id}, "
                f"resolved_case_status={resolved_case_status}"
            )
            return
        if event.case_id != getattr(task_doc, "current_case_id", None):
            logger.debug(
                "Skipping task auto-advance because event case is not current: "
                f"task_id={task_doc.task_id}, event_case_id={event.case_id}, "
                f"current_case_id={task_doc.current_case_id}"
            )
            return

        next_case_index = getattr(task_doc, "current_case_index", 0) + 1
        if next_case_index >= task_doc.case_count:
            task_doc.current_case_id = None
            task_doc.current_case_index = task_doc.case_count
            task_doc.finished_at = event_time
            task_doc.last_callback_at = event_time
            task_doc.overall_status = "FAILED" if task_doc.failed_case_count > 0 else "PASSED"
            if task_doc.dispatch_status != "DISPATCH_FAILED":
                task_doc.dispatch_status = "COMPLETED"
            await task_doc.save()
            logger.info(
                "Execution task completed after final case: "
                f"task_id={task_doc.task_id}, final_case_id={event.case_id}, "
                f"overall_status={task_doc.overall_status}"
            )
            return

        command = await self._execution_service._build_task_dispatch_command(task_doc, next_case_index)
        logger.info(
            "Auto-dispatching next execution case: "
            f"task_id={task_doc.task_id}, finished_case_id={event.case_id}, "
            f"next_case_id={command.dispatch_case_id}, next_case_index={next_case_index}"
        )
        await self._execution_service._dispatch_existing_task(task_doc, command)
