"""执行任务命令应用服务。"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any, Dict

from app.modules.attachments.service.attachment_service import AttachmentService
from app.modules.execution.application.case_resolver import ExecutionCaseResolver
from app.modules.test_specs.application.case_metadata_query import TestCaseMetadataQuery
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_command_helpers import (
    build_rerun_command_from_payload,
    ensure_actor_identity,
    initialize_command,
)
from app.modules.execution.application.task_dispatch_service import ExecutionDispatchService
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.schemas import DispatchTaskRequest, RerunTaskRequest
from app.modules.execution.shared.execution_context import execution_scope, set_execution_context
from app.modules.execution.shared.execution_log import ExecutionNode, elog
from app.shared.service import SequenceIdService


class ExecutionTaskCommandService:
    """处理任务创建、重跑、删除等命令。"""

    def __init__(
        self,
        dispatch_service: ExecutionDispatchService | None = None,
        case_resolver: ExecutionCaseResolver | None = None,
        attachment_service: AttachmentService | None = None,
    ) -> None:
        self._dispatch_service = dispatch_service or ExecutionDispatchService()
        self._case_resolver = case_resolver or ExecutionCaseResolver(TestCaseMetadataQuery())
        self._attachment_service = attachment_service or AttachmentService()

    @staticmethod
    async def _enrich_case_file_params(parameters: Dict[str, Any], attachment_service: AttachmentService) -> Dict[str, Any]:
        """Detect file-type parameters and enrich with download URLs."""
        result = dict(parameters)
        for key, value in result.items():
            if isinstance(value, dict) and value.get("type") == "file" and value.get("file_id"):
                enriched = await attachment_service.enrich_single(value["file_id"])
                result[key] = {**value, **enriched}
        return result

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
        elog(
            "info",
            ExecutionNode.TASK_CREATE,
            "dispatch task request received",
            actor_id=actor_id,
            dispatch_channel=request.dispatch_channel,
            schedule_type=request.schedule_type,
            planned_at=str(request.planned_at) if request.planned_at else None,
            case_count=len(request.cases),
            cases=request_case_payload,
        )

        year = datetime.now().year
        seq = await sequence_service.next(f"execution_task:{year}")
        rand = secrets.token_hex(4)
        task_id = f"ET-{year}-{str(seq).zfill(6)}-{rand}"
        set_execution_context(task_id=task_id, agent_id=request.agent_id)

        auto_case_ids = [item.auto_case_id for item in request.cases]
        case_configs = [dict(item.config) for item in request.cases]
        dispatch_bindings = await self._case_resolver.resolve_case_dispatch_bindings_by_auto_case_ids(
            auto_case_ids
        )
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
        for payload in case_payloads:
            payload["parameters"] = await self._enrich_case_file_params(payload["parameters"], self._attachment_service)
        elog(
            "debug",
            ExecutionNode.TASK_CREATE,
            "dispatch task case bindings resolved",
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            script_entity_ids=script_entity_ids,
            case_configs=case_configs,
            case_payloads=case_payloads,
        )

        command = DispatchExecutionTaskCommand(
            task_id=task_id,
            dispatch_channel=request.dispatch_channel,
            agent_id=request.agent_id,
            created_by=actor_id,
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            script_entity_ids=script_entity_ids,
            case_configs=case_configs,
            case_payloads=case_payloads,
            schedule_type=request.schedule_type,
            planned_at=request.planned_at,
            trigger_source=request.trigger_source,
            category=request.category,
            project_tag=request.project_tag,
            repo_url=request.repo_url,
            branch=request.branch,
            pytest_options=request.pytest_options,
            timeout=request.timeout,
            attachments=[],
        )
        initialize_command(command)

        async with execution_scope(task_id=task_id, agent_id=request.agent_id, node=ExecutionNode.TASK_CREATE.value):
            data = await self._dispatch_service.create_task_from_command(command, actor_id=actor_id)

        elog(
            "info",
            ExecutionNode.TASK_CREATE,
            "dispatch task request handled successfully",
            outcome="success",
            after={
                "dispatch_status": data.get("dispatch_status"),
                "overall_status": data.get("overall_status"),
                "case_count": data.get("case_count"),
            },
        )
        return data

    async def delete_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """删除执行任务（逻辑删除）。"""
        async with execution_scope(task_id=task_id, node=ExecutionNode.TASK_DELETE.value):
            task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
            if not task_doc:
                raise KeyError(f"Task not found: {task_id}")
            ensure_actor_identity(actor_id, task_doc.created_by)

            task_doc.is_deleted = True
            await task_doc.save()
            elog(
                "info",
                ExecutionNode.TASK_DELETE,
                "execution task marked deleted",
                outcome="success",
                actor_id=actor_id,
            )

        return {"task_id": task_id, "deleted": True}

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

        ensure_actor_identity(actor_id, source_task_doc.created_by)
        if request.cases is not None:
            auto_case_ids = [case.auto_case_id for case in request.cases]
        else:
            payload_cases = list(dict(source_task_doc.request_payload or {}).get("cases", []))
            auto_case_ids = [
                case["auto_case_id"] for case in payload_cases
                if case.get("auto_case_id")
            ]
        dispatch_bindings = await self._case_resolver.resolve_case_dispatch_bindings_by_auto_case_ids(
            auto_case_ids
        )
        command = build_rerun_command_from_payload(
            source_task_doc=source_task_doc,
            request=request,
            new_task_id=new_task_id,
            actor_id=actor_id,
            dispatch_bindings=dispatch_bindings,
        )
        for i in range(len(command.case_payloads)):
            params = command.case_payloads[i].get("parameters") or {}
            command.case_payloads[i]["parameters"] = await self._enrich_case_file_params(params, self._attachment_service)
        command.attachments = []

        elog(
            "info",
            ExecutionNode.TASK_RERUN,
            "rerunning execution task as new task",
            source_task_id=source_task_id,
            actor_id=actor_id,
        )
        async with execution_scope(task_id=new_task_id, node=ExecutionNode.TASK_RERUN.value):
            return await self._dispatch_service.create_task_from_command(command, actor_id=actor_id)
