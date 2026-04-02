"""执行任务下发应用服务。"""

from __future__ import annotations

from typing import Any, Dict

from app.modules.execution.application.task_case_mixin import ExecutionTaskCaseMixin
from app.modules.execution.application.task_command_mixin import ExecutionTaskCommandMixin
from app.modules.execution.application.task_dispatch_mixin import ExecutionTaskDispatchMixin
from app.modules.execution.application.task_query_mixin import ExecutionTaskQueryMixin
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher
from app.shared.core.logger import log as logger


class ExecutionDispatchService(
    ExecutionTaskDispatchMixin,
    ExecutionTaskCaseMixin,
    ExecutionTaskCommandMixin,
    ExecutionTaskQueryMixin,
):
    """统一封装任务创建后的下发与重建能力。"""

    def __init__(self, dispatcher: ExecutionTaskDispatcher | None = None) -> None:
        self._dispatcher = dispatcher or ExecutionTaskDispatcher()

    async def create_task_from_command(
        self,
        command: DispatchExecutionTaskCommand,
        actor_id: str,
    ) -> Dict[str, Any]:
        """创建执行任务，并在需要时立即触发首条 case 下发。"""
        self._ensure_actor_identity(actor_id, command.created_by)
        logger.info(
            "Creating execution task: "
            f"task_id={command.task_id}, framework={command.framework}, agent_id={command.agent_id}, "
            f"case_count={len(command.case_ids)}, schedule_type={command.schedule_type}"
        )
        doc_map = await self._load_case_docs(command.case_ids)
        schedule_type, planned_at, schedule_status, should_dispatch_now = self._normalize_schedule(
            command.schedule_type,
            command.planned_at,
        )
        dispatch_channel = self._normalize_dispatch_channel(command.dispatch_channel)
        command.schedule_type = schedule_type
        command.planned_at = planned_at
        command.dispatch_channel = dispatch_channel
        dedup_key = self._build_dedup_key(command)
        await self._ensure_no_active_duplicate(dedup_key)

        task_doc = ExecutionTaskDoc(
            task_id=command.task_id,
            framework=command.framework,
            created_by=command.created_by,
            dispatch_channel=dispatch_channel,
        )
        self._apply_task_command_to_doc(
            task_doc=task_doc,
            command=command,
            dedup_key=dedup_key,
            schedule_type=schedule_type,
            schedule_status=schedule_status,
            dispatch_status="DISPATCHING" if should_dispatch_now else "PENDING",
        )
        await task_doc.insert()
        await self._replace_task_case_docs(
            task_doc.task_id,
            command.case_ids,
            command.auto_case_ids,
            command.case_configs or [{} for _ in command.case_ids],
            doc_map,
        )
        await task_doc.save()
        await self._dispatch_task_if_needed(task_doc, should_dispatch_now)
        logger.info(
            "Execution task created: "
            f"task_id={task_doc.task_id}, schedule_status={task_doc.schedule_status}, "
            f"dispatch_status={task_doc.dispatch_status}, should_dispatch_now={should_dispatch_now}"
        )
        return self._serialize_task_doc(task_doc)

    async def build_task_dispatch_command(
        self,
        task_doc: ExecutionTaskDoc,
        dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        """根据任务快照重建指定 case 的下发命令。"""
        return await self._build_task_dispatch_command(task_doc, dispatch_case_index)

    async def dispatch_existing_task(
        self,
        task_doc: ExecutionTaskDoc,
        command: DispatchExecutionTaskCommand,
    ) -> None:
        """对已有任务执行一次真正下发。"""
        await self._dispatch_existing_task(task_doc, command)
