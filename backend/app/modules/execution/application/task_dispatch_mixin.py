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
        script_entity_ids: List[str | None],
        case_configs: List[dict],
        case_payloads: List[dict],
        dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        """构建单 case 下发命令。"""
        request_payload = dict(task_doc.request_payload)
        planned_at = request_payload["planned_at"]
        return DispatchExecutionTaskCommand(
            task_id=task_doc.task_id,
            external_task_id=task_doc.external_task_id,
            framework=task_doc.framework,
            dispatch_channel=task_doc.dispatch_channel,
            agent_id=task_doc.agent_id,
            trigger_source=request_payload["trigger_source"],
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
            planned_at=cls._ensure_utc_datetime(planned_at) if planned_at else None,
            callback_url=request_payload["callback_url"],
            category=request_payload["category"],
            project_tag=request_payload["project_tag"],
            repo_url=request_payload["repo_url"],
            branch=request_payload["branch"],
            common_parameters=request_payload["common_parameters"],
            pytest_options=request_payload["pytest_options"],
            timeout=request_payload["timeout"],
            dut=request_payload["dut"],
        )

    async def _build_task_dispatch_command(
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
        ) = await self._resolve_task_case_pairs(task_doc)
        return self._build_case_dispatch_command(
            task_doc,
            case_ids,
            auto_case_ids,
            script_entity_ids,
            case_configs,
            case_payloads,
            dispatch_case_index,
        )

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
        logger.debug(
            "Dispatching execution task case: "
            f"task_id={command.task_id}, case_id={command.dispatch_case_id}, "
            f"case_index={command.dispatch_case_index}, framework={command.framework}, "
            f"agent_id={command.agent_id}"
        )
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
            logger.debug(
                "Updated execution case dispatch state: "
                f"task_id={case_doc.task_id}, case_id={case_doc.case_id}, "
                f"dispatch_status={case_doc.dispatch_status}, attempts={case_doc.dispatch_attempts}"
            )
        else:
            logger.warning(
                "Execution case doc missing during dispatch: "
                f"task_id={task_doc.task_id}, case_id={command.dispatch_case_id}"
            )

        if dispatch_result.success:
            logger.info(
                "Successfully dispatched execution task case: "
                f"task_id={command.task_id}, case_id={command.dispatch_case_id}, "
                f"channel={dispatch_result.channel}"
            )
        else:
            logger.warning(
                "Failed to dispatch execution task case: "
                f"task_id={command.task_id}, case_id={command.dispatch_case_id}, "
                f"channel={dispatch_result.channel}, error={dispatch_result.error}"
            )
