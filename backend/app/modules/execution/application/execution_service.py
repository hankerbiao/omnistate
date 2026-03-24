"""执行任务应用服务门面。"""

from __future__ import annotations

from typing import Any, Dict

from app.modules.execution.application.agent_mixin import ExecutionAgentMixin
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_case_mixin import ExecutionTaskCaseMixin
from app.modules.execution.application.task_command_mixin import ExecutionTaskCommandMixin
from app.modules.execution.application.task_dispatch_mixin import ExecutionTaskDispatchMixin
from app.modules.execution.application.task_query_mixin import ExecutionTaskQueryMixin
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.schemas import RerunTaskRequest
from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher
from app.shared.core.logger import log as logger


class ExecutionService(
    ExecutionTaskDispatchMixin,
    ExecutionTaskCaseMixin,
    ExecutionTaskCommandMixin,
    ExecutionTaskQueryMixin,
    ExecutionAgentMixin,
):
    """执行任务命令服务门面。"""

    def __init__(self) -> None:
        self._dispatcher = ExecutionTaskDispatcher()

    @staticmethod
    def _ensure_pending_scheduled_task(task_doc: ExecutionTaskDoc) -> None:
        """限制取消/修改仅作用于未触发的定时任务。"""
        if task_doc.schedule_type != "SCHEDULED":
            raise ValueError(f"Task {task_doc.task_id} is not a scheduled task")
        if task_doc.schedule_status != "PENDING":
            raise ValueError(
                f"Task {task_doc.task_id} cannot be changed in schedule_status {task_doc.schedule_status}"
            )

    async def delete_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """删除执行任务（逻辑删除）。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")
        self._ensure_actor_identity(actor_id, task_doc.created_by)

        task_doc.is_deleted = True
        await task_doc.save()
        logger.info(f"Execution task marked deleted: task_id={task_id}, actor_id={actor_id}")

        return {"task_id": task_id, "deleted": True}

    async def cancel_scheduled_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """取消未触发的定时任务。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")
        self._ensure_actor_identity(actor_id, task_doc.created_by)

        self._ensure_pending_scheduled_task(task_doc)
        task_doc.schedule_status = "CANCELLED"
        task_doc.dispatch_status = "CANCELLED"
        task_doc.overall_status = "CANCELLED"
        await task_doc.save()
        logger.info(f"Scheduled execution task cancelled: task_id={task_id}, actor_id={actor_id}")

        return self._serialize_task_doc(task_doc)

    async def dispatch_execution_task(
        self,
        command: DispatchExecutionTaskCommand,
        actor_id: str,
    ) -> Dict[str, Any]:
        """创建任务并启动首轮执行。"""
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
            external_task_id=command.external_task_id,
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

    async def rerun_task(
        self,
        source_task_id: str,
        new_task_id: str,
        external_task_id: str,
        actor_id: str,
        request: RerunTaskRequest,
    ) -> Dict[str, Any]:
        """基于已有任务快照创建一个新的执行任务。"""
        source_task_doc = await ExecutionTaskDoc.find_one({"task_id": source_task_id, "is_deleted": False})
        if not source_task_doc:
            raise KeyError(f"Task not found: {source_task_id}")

        self._ensure_actor_identity(actor_id, source_task_doc.created_by)
        if request.cases is not None:
            auto_case_ids = [case.auto_case_id for case in request.cases]
        else:
            payload_cases = list(dict(source_task_doc.request_payload or {}).get("cases", []))
            auto_case_ids = [case["auto_case_id"] for case in payload_cases]
        dispatch_bindings = await self.resolve_case_dispatch_bindings_by_auto_case_ids(auto_case_ids)
        command = self._build_rerun_command_from_payload(
            source_task_doc=source_task_doc,
            request=request,
            new_task_id=new_task_id,
            external_task_id=external_task_id,
            actor_id=actor_id,
            dispatch_bindings=dispatch_bindings,
        )
        logger.info(
            "Rerunning execution task as new task: "
            f"source_task_id={source_task_id}, new_task_id={new_task_id}, actor_id={actor_id}"
        )
        return await self.dispatch_execution_task(command, actor_id=actor_id)
