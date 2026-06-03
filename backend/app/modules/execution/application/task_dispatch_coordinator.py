"""执行任务下发 coordinator。"""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import List

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.constants import DispatchStatus, OverallStatus, ScheduleStatus
from app.modules.execution.application.task_case_coordinator import ExecutionTaskCaseCoordinator
from app.modules.execution.application.task_command_helpers import ensure_utc_datetime, initialize_command
from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher
from app.modules.execution.shared.execution_context import execution_scope
from app.modules.execution.shared.execution_log import ExecutionNode, elog


class ExecutionTaskDispatchCoordinator:
    """处理命令构造与任务下发状态更新。"""

    def __init__(
        self,
        dispatcher: ExecutionTaskDispatcher | None = None,
        case_coordinator: ExecutionTaskCaseCoordinator | None = None,
    ) -> None:
        self._dispatcher = dispatcher or ExecutionTaskDispatcher()
        self._case_coordinator = case_coordinator or ExecutionTaskCaseCoordinator()

    @staticmethod
    def build_case_dispatch_command(
        task_doc: ExecutionTaskDoc,
        case_ids: List[str],
        auto_case_ids: List[str],
        script_entity_ids: List[str | None],
        case_configs: List[dict],
        case_payloads: List[dict],
        dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        """构建单 case 下发命令。"""
        request_payload = dict(task_doc.request_payload or {})
        planned_at = request_payload.get("planned_at")
        command = DispatchExecutionTaskCommand(
            task_id=task_doc.task_id,
            dispatch_channel=task_doc.dispatch_channel,
            agent_id=task_doc.agent_id,
            created_by=task_doc.created_by,
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            script_entity_ids=script_entity_ids,
            case_configs=case_configs,
            case_payloads=case_payloads,
            dispatch_case_id=case_ids[dispatch_case_index],
            dispatch_auto_case_id=auto_case_ids[dispatch_case_index],
            dispatch_script_entity_id=script_entity_ids[dispatch_case_index],
            dispatch_case_config=case_configs[dispatch_case_index],
            dispatch_case_index=dispatch_case_index,
            schedule_type=task_doc.schedule_type,
            planned_at=ensure_utc_datetime(planned_at) if planned_at else None,
            trigger_source=request_payload.get("trigger_source"),
            category=request_payload.get("category"),
            project_tag=request_payload.get("project_tag"),
            repo_url=request_payload.get("repo_url"),
            branch=request_payload.get("branch"),
            pytest_options=request_payload.get("pytest_options"),
            timeout=request_payload.get("timeout"),
        )
        initialize_command(command)
        return command

    async def build_task_dispatch_command(
        self,
        task_doc: ExecutionTaskDoc,
        dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        (
            case_ids,
            auto_case_ids,
            script_entity_ids,
            case_configs,
            case_payloads,
        ) = await self._case_coordinator.resolve_task_case_pairs(task_doc)
        return self.build_case_dispatch_command(
            task_doc,
            case_ids,
            auto_case_ids,
            script_entity_ids,
            case_configs,
            case_payloads,
            dispatch_case_index,
        )

    async def dispatch_task_if_needed(
        self,
        task_doc: ExecutionTaskDoc,
        should_dispatch_now: bool,
        dispatch_case_index: int,
    ) -> None:
        """按需下发指定索引的 case。"""
        if not should_dispatch_now:
            return
        await self.dispatch_existing_task(
            task_doc,
            await self.build_task_dispatch_command(task_doc, dispatch_case_index),
        )

    async def dispatch_existing_task(
        self,
        task_doc: ExecutionTaskDoc,
        command: DispatchExecutionTaskCommand,
    ) -> None:
        """对已有任务执行真正下发。"""
        before_status = {
            "dispatch_status": task_doc.dispatch_status,
            "overall_status": task_doc.overall_status,
            "current_case_id": task_doc.current_case_id,
            "current_case_index": task_doc.current_case_index,
        }
        async with execution_scope(
            task_id=command.task_id,
            case_id=command.dispatch_case_id,
            agent_id=command.agent_id,
            node=ExecutionNode.TASK_DISPATCH.value,
        ):
            elog(
                "debug",
                ExecutionNode.TASK_DISPATCH,
                "dispatching execution task case",
                case_index=command.dispatch_case_index,
            )
            start = perf_counter()
            dispatch_result = await self._dispatcher.dispatch(command)
            elapsed_ms = (perf_counter() - start) * 1000

            case_doc = await ExecutionTaskCaseDoc.find_one({
                "task_id": task_doc.task_id,
                "case_id": command.dispatch_case_id,
                "is_deleted": False,
            })
            dispatch_time = datetime.now(timezone.utc)
            task_doc.dispatch_channel = dispatch_result.channel
            task_doc.dispatch_status = (
                DispatchStatus.DISPATCHED if dispatch_result.success else DispatchStatus.DISPATCH_FAILED
            )
            task_doc.dispatch_error = dispatch_result.error
            task_doc.dispatch_response = dispatch_result.response
            task_doc.schedule_status = ScheduleStatus.TRIGGERED
            task_doc.current_case_id = command.dispatch_case_id
            task_doc.current_case_index = command.dispatch_case_index
            if not task_doc.triggered_at:
                task_doc.triggered_at = dispatch_time
            if dispatch_result.success:
                task_doc.overall_status = OverallStatus.QUEUED
                task_doc.finished_at = None
            else:
                task_doc.overall_status = OverallStatus.FAILED
                task_doc.finished_at = dispatch_time
            await task_doc.save()

            after_status = {
                "dispatch_status": task_doc.dispatch_status,
                "overall_status": task_doc.overall_status,
                "current_case_id": task_doc.current_case_id,
                "current_case_index": task_doc.current_case_index,
            }

            if case_doc:
                case_doc.dispatch_attempts += 1
                case_doc.dispatch_status = (
                    DispatchStatus.DISPATCHED if dispatch_result.success else DispatchStatus.DISPATCH_FAILED
                )
                case_doc.dispatched_at = dispatch_time
                await case_doc.save()
                elog(
                    "debug",
                    ExecutionNode.TASK_DISPATCH,
                    "updated execution case dispatch state",
                    dispatch_attempts=case_doc.dispatch_attempts,
                    case_dispatch_status=case_doc.dispatch_status,
                )
            else:
                elog(
                    "warning",
                    ExecutionNode.TASK_DISPATCH,
                    "execution case doc missing during dispatch",
                    outcome="failed",
                )

            if dispatch_result.success:
                elog(
                    "info",
                    ExecutionNode.TASK_DISPATCH,
                    "successfully dispatched execution task case",
                    outcome="success",
                    channel=dispatch_result.channel,
                    before=before_status,
                    after=after_status,
                    duration_ms=elapsed_ms,
                )
            else:
                elog(
                    "warning",
                    ExecutionNode.TASK_DISPATCH,
                    "failed to dispatch execution task case",
                    outcome="failed",
                    channel=dispatch_result.channel,
                    error=dispatch_result.error,
                    before=before_status,
                    after=after_status,
                    duration_ms=elapsed_ms,
                )
