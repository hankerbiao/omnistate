"""执行任务下发能力。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.shared.core.logger import log as logger


class ExecutionTaskDispatchMixin:
    """处理命令构造与任务下发。"""

    @classmethod
    def _build_case_dispatch_command(
        cls,
        task_doc: ExecutionTaskDoc,
        case_ids: List[str],
        auto_case_ids: List[str],
        dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        """构建单 case 下发命令。"""
        request_payload = dict(task_doc.request_payload or {})
        planned_at = request_payload.get("planned_at")
        return DispatchExecutionTaskCommand(
            task_id=task_doc.task_id,
            external_task_id=task_doc.external_task_id or f"EXT-{task_doc.task_id}",
            framework=task_doc.framework,
            agent_id=task_doc.agent_id,
            trigger_source=request_payload.get("trigger_source", "manual"),
            created_by=task_doc.created_by,
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            dispatch_case_id=case_ids[dispatch_case_index],
            dispatch_auto_case_id=auto_case_ids[dispatch_case_index],
            dispatch_case_index=dispatch_case_index,
            schedule_type=task_doc.schedule_type,
            planned_at=cls._ensure_utc_datetime(planned_at) if planned_at else None,
            callback_url=request_payload.get("callback_url"),
            dut=request_payload.get("dut"),
        )

    async def _build_task_dispatch_command(
        self,
        task_doc: ExecutionTaskDoc,
        dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        case_ids, auto_case_ids = await self._resolve_task_case_pairs(task_doc)
        return self._build_case_dispatch_command(task_doc, case_ids, auto_case_ids, dispatch_case_index)

    async def _dispatch_task_if_needed(
        self,
        task_doc: ExecutionTaskDoc,
        should_dispatch_now: bool,
        dispatch_case_index: int = 0,
    ) -> None:
        """按需下发指定索引的 case。"""
        if not should_dispatch_now:
            return
        await self._dispatch_existing_task(
            task_doc,
            await self._build_task_dispatch_command(task_doc, dispatch_case_index),
        )

    async def _dispatch_existing_task(
        self,
        task_doc: ExecutionTaskDoc,
        command: DispatchExecutionTaskCommand,
    ) -> None:
        """对已有任务执行真正下发。"""
        dispatch_result = await self._dispatcher.dispatch(command)
        case_doc = await ExecutionTaskCaseDoc.find_one({
            "task_id": task_doc.task_id,
            "case_id": command.dispatch_case_id,
        })
        dispatch_time = datetime.now(timezone.utc)
        task_doc.dispatch_channel = dispatch_result.channel
        task_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
        task_doc.dispatch_error = dispatch_result.error
        task_doc.dispatch_response = dispatch_result.response
        task_doc.schedule_status = "TRIGGERED"
        task_doc.current_case_id = command.dispatch_case_id
        task_doc.current_case_index = command.dispatch_case_index
        if not task_doc.triggered_at:
            task_doc.triggered_at = dispatch_time
        if dispatch_result.success:
            task_doc.overall_status = "QUEUED"
            task_doc.finished_at = None
        else:
            task_doc.overall_status = "FAILED"
            task_doc.finished_at = dispatch_time
        await task_doc.save()

        if case_doc:
            case_doc.dispatch_attempts += 1
            case_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
            case_doc.dispatched_at = dispatch_time
            await case_doc.save()

        if dispatch_result.success:
            logger.info(f"Successfully dispatched task {command.task_id} via {dispatch_result.channel}")
        else:
            logger.warning(f"Failed to dispatch task {command.task_id} via {dispatch_result.channel}")
