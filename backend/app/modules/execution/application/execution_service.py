"""执行任务应用服务门面。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.modules.execution.schemas import DispatchTaskRequest, RerunTaskRequest
from app.modules.execution.application.agent_mixin import ExecutionAgentMixin
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_case_mixin import ExecutionTaskCaseMixin
from app.modules.execution.application.task_command_mixin import ExecutionTaskCommandMixin
from app.modules.execution.application.task_dispatch_mixin import ExecutionTaskDispatchMixin
from app.modules.execution.application.task_query_mixin import ExecutionTaskQueryMixin
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher
from app.shared.core.logger import log as logger
from app.shared.service import SequenceIdService


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

    async def create_and_dispatch_task(
        self,
        request: DispatchTaskRequest,
        actor_id: str,
        sequence_service: SequenceIdService,
    ) -> Dict[str, Any]:
        """根据接口请求构造命令并创建执行任务。"""
        request_case_payload = [
            {
                "auto_case_id": item.auto_case_id,
                "parameters": dict(item.parameters),
            }
            for item in request.cases
        ]
        logger.info(
            "Dispatch task request received: "
            f"user_id={actor_id}, framework={request.framework}, "
            f"dispatch_channel={request.dispatch_channel}, agent_id={request.agent_id}, "
            f"schedule_type={request.schedule_type}, planned_at={request.planned_at}, "
            f"cases={request_case_payload}"
        )

        year = datetime.now().year
        seq = await sequence_service.next(f"execution_task:{year}")
        task_id = f"ET-{year}-{str(seq).zfill(6)}"

        auto_case_ids = [item.auto_case_id for item in request.cases]
        case_configs = [dict(item.config) for item in request.cases]
        dispatch_bindings = await self.resolve_case_dispatch_bindings_by_auto_case_ids(auto_case_ids)
        case_ids = [binding.case_id for binding in dispatch_bindings]
        script_entity_ids = [binding.script_entity_id for binding in dispatch_bindings]
        case_payloads = [
            {
                "case_id": binding.case_id,
                "script_path": binding.script_path,
                "script_name": binding.script_name,
                "parameters": dict(item.parameters),
            }
            for item, binding in zip(request.cases, dispatch_bindings)
        ]
        logger.debug(
            "Dispatch task case bindings resolved: "
            f"task_id={task_id}, auto_case_ids={auto_case_ids}, case_ids={case_ids}, "
            f"script_entity_ids={script_entity_ids}, case_configs={case_configs}, "
            f"case_payloads={case_payloads}"
        )

        command = DispatchExecutionTaskCommand(
            task_id=task_id,
            framework=request.framework,
            dispatch_channel=request.dispatch_channel,
            agent_id=request.agent_id,
            trigger_source=request.trigger_source,
            created_by=actor_id,
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            script_entity_ids=script_entity_ids,
            case_configs=case_configs,
            case_payloads=case_payloads,
            schedule_type=request.schedule_type,
            planned_at=request.planned_at,
            callback_url=request.callback_url,
            category=request.category,
            project_tag=request.project_tag,
            repo_url=request.repo_url,
            branch=request.branch,
            pytest_options=request.pytest_options,
            timeout=request.timeout,
            dut=request.dut,
        )

        data = await self.dispatch_execution_task(command, actor_id=actor_id)
        logger.info(
            "Dispatch task request handled successfully: "
            f"task_id={task_id}, "
            f"dispatch_status={data.get('dispatch_status')}, overall_status={data.get('overall_status')}, "
            f"case_count={data.get('case_count')}"
        )
        return data

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
            actor_id=actor_id,
            dispatch_bindings=dispatch_bindings,
        )
        logger.info(
            "Rerunning execution task as new task: "
            f"source_task_id={source_task_id}, new_task_id={new_task_id}, actor_id={actor_id}"
        )
        return await self.dispatch_execution_task(command, actor_id=actor_id)
