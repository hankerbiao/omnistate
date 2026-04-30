"""执行任务命令应用服务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.modules.execution.application.case_resolver import ExecutionCaseResolver
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_command_mixin import ExecutionTaskCommandMixin
from app.modules.execution.application.task_dispatch_service import ExecutionDispatchService
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.attachments.repository.models import AttachmentDoc
from app.modules.execution.schemas import DispatchTaskRequest, RerunTaskRequest
from app.shared.core.logger import log as logger
from app.shared.service import SequenceIdService


class ExecutionTaskCommandService(ExecutionTaskCommandMixin):
    """处理任务创建、重跑、删除等命令。"""

    def __init__(
        self,
        dispatch_service: ExecutionDispatchService | None = None,
        case_resolver: ExecutionCaseResolver | None = None,
    ) -> None:
        self._dispatch_service = dispatch_service or ExecutionDispatchService()
        self._case_resolver = case_resolver or ExecutionCaseResolver()

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
            f"user_id={actor_id}, "
            f"dispatch_channel={request.dispatch_channel}, agent_id={request.agent_id}, "
            f"schedule_type={request.schedule_type}, planned_at={request.planned_at}, "
            f"cases={request_case_payload}"
        )

        year = datetime.now().year
        seq = await sequence_service.next(f"execution_task:{year}")
        task_id = f"ET-{year}-{str(seq).zfill(6)}"

        auto_case_ids = [item.auto_case_id for item in request.cases]
        case_configs = [dict(item.config) for item in request.cases]
        attachments = await self._validate_and_enrich_attachments(
            [item.model_dump(exclude_none=True) for item in request.attachments]
        )
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
        logger.debug(
            "Dispatch task case bindings resolved: "
            f"task_id={task_id}, auto_case_ids={auto_case_ids}, case_ids={case_ids}, "
            f"script_entity_ids={script_entity_ids}, case_configs={case_configs}, "
            f"case_payloads={case_payloads}"
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
            framework=request.framework,
            trigger_source=request.trigger_source,
            callback_url=request.callback_url,
            category=request.category,
            project_tag=request.project_tag,
            repo_url=request.repo_url,
            branch=request.branch,
            pytest_options=request.pytest_options,
            timeout=request.timeout,
            dut=request.dut,
            attachments=attachments,
        )

        data = await self._dispatch_service.create_task_from_command(command, actor_id=actor_id)
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
        dispatch_bindings = await self._case_resolver.resolve_case_dispatch_bindings_by_auto_case_ids(
            auto_case_ids
        )
        command = self._build_rerun_command_from_payload(
            source_task_doc=source_task_doc,
            request=request,
            new_task_id=new_task_id,
            actor_id=actor_id,
            dispatch_bindings=dispatch_bindings,
        )
        command.attachments = await self._validate_and_enrich_attachments(command.attachments or [])
        logger.info(
            "Rerunning execution task as new task: "
            f"source_task_id={source_task_id}, new_task_id={new_task_id}, actor_id={actor_id}"
        )
        return await self._dispatch_service.create_task_from_command(command, actor_id=actor_id)

    @staticmethod
    async def _validate_and_enrich_attachments(attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate task attachments and store stable MinIO metadata in the task snapshot."""
        if not attachments:
            return []

        enriched_attachments: list[dict[str, Any]] = []
        for attachment_ref in attachments:
            file_id = attachment_ref.get("file_id")
            if not file_id:
                raise ValueError("attachment missing required field: file_id")

            attachment = await AttachmentDoc.find_one({"file_id": file_id, "is_deleted": False})
            if not attachment:
                raise KeyError(f"attachment not found or deleted: {file_id}")

            enriched_attachments.append({
                "file_id": attachment.file_id,
                "original_filename": attachment.original_filename,
                "storage_path": f"{attachment.bucket}/{attachment.object_name}",
                "bucket": attachment.bucket,
                "object_name": attachment.object_name,
                "size": attachment.size,
                "content_type": attachment.content_type,
                "uploaded_at": attachment.uploaded_at.isoformat() if attachment.uploaded_at else None,
            })

        return enriched_attachments
