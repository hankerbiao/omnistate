"""执行任务命令公共能力。"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.constants import FINAL_TASK_STATUSES
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.schemas import RerunTaskRequest
from app.shared.core.logger import log as logger


class ExecutionTaskCommandMixin:
    """提供任务命令相关的通用能力。"""

    @staticmethod
    def _assign_fields(target: Any, **values: Any) -> None:
        for field_name, field_value in values.items():
            setattr(target, field_name, field_value)

    @staticmethod
    def _build_dedup_key(command: DispatchExecutionTaskCommand) -> str:
        """基于业务载荷构建稳定去重键。"""
        payload = {
            "dispatch_channel": command.dispatch_channel,
            "agent_id": command.agent_id,
            "framework": command.framework,
            "trigger_source": command.trigger_source,
            "schedule_type": command.schedule_type,
            "planned_at": command.planned_at.isoformat() if command.planned_at else None,
            "callback_url": command.callback_url,
            "category": command.category,
            "project_tag": command.project_tag,
            "repo_url": command.repo_url,
            "branch": command.branch,
            "pytest_options": command.pytest_options,
            "timeout": command.timeout,
            "dut": command.dut,
            "attachments": command.attachments,
            "cases": sorted(
                [
                    {
                        "case_id": case_id,
                        "script_path": case_payload.get("script_path"),
                        "script_name": case_payload.get("script_name"),
                        "parameters": case_payload.get("parameters"),
                        "config": case_config,
                    }
                    for case_id, case_config, case_payload in zip(
                        command.case_ids,
                        command.case_configs,
                        command.case_payloads,
                    )
                ],
                key=lambda item: (
                    item["case_id"],
                    item.get("script_path") or "",
                    item.get("script_name") or "",
                    json.dumps(
                        item.get("parameters") or {},
                        ensure_ascii=True,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ),
            ),
        }
        normalized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _ensure_utc_datetime(value: datetime | str) -> datetime:
        """将 naive/aware datetime 或 ISO 时间字符串统一规范为 UTC aware datetime。"""
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.endswith("Z"):
                normalized = f"{normalized[:-1]}+00:00"
            value = datetime.fromisoformat(normalized)
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _normalize_schedule(
        cls,
        schedule_type: str | None,
        planned_at: datetime | None,
        now: datetime | None = None,
    ) -> tuple[str, datetime | None, str, bool]:
        """统一调度类型和状态。"""
        current_time = cls._ensure_utc_datetime(now or datetime.now(timezone.utc))
        normalized_type = (schedule_type or "IMMEDIATE").upper()
        normalized_planned_at = cls._ensure_utc_datetime(planned_at) if planned_at else None

        if normalized_type == "SCHEDULED":
            if normalized_planned_at is None:
                raise ValueError("planned_at is required when schedule_type is SCHEDULED")
            if normalized_planned_at <= current_time:
                return normalized_type, normalized_planned_at, "READY", True
            return normalized_type, normalized_planned_at, "PENDING", False

        return "IMMEDIATE", normalized_planned_at, "READY", True

    @staticmethod
    def _build_task_request_payload(command: DispatchExecutionTaskCommand) -> Dict[str, Any]:
        """构建任务级快照，保留完整 case 列表用于后续串行推进。"""
        return {
            "task_id": command.task_id,
            "dispatch_channel": command.dispatch_channel,
            "agent_id": command.agent_id,
            "framework": command.framework,
            "trigger_source": command.trigger_source,
            "schedule_type": command.schedule_type,
            "planned_at": command.planned_at.isoformat() if command.planned_at else None,
            "callback_url": command.callback_url,
            "category": command.category,
            "project_tag": command.project_tag,
            "repo_url": command.repo_url,
            "branch": command.branch,
            "pytest_options": command.pytest_options,
            "timeout": command.timeout,
            "dut": command.dut,
            "attachments": list(command.attachments or []),
            "cases": [
                {
                    "case_id": case_id,
                    "auto_case_id": auto_case_id,
                    "script_entity_id": script_entity_id,
                    "config": case_config,
                    "payload_case_id": case_payload.get("case_id"),
                    "script_path": case_payload.get("script_path"),
                    "script_name": case_payload.get("script_name"),
                    "parameters": case_payload.get("parameters"),
                    "attachments": case_payload.get("attachments", []),  # 附件列表
                }
                for case_id, auto_case_id, script_entity_id, case_config, case_payload in zip(
                    command.case_ids,
                    command.auto_case_ids,
                    command.script_entity_ids,
                    command.case_configs,
                    command.case_payloads,
                )
            ],
            "created_by": command.created_by,
        }

    @staticmethod
    def _normalize_dispatch_channel(dispatch_channel: str | None) -> str:
        if dispatch_channel is None:
            raise ValueError("dispatch_channel is required")
        normalized = dispatch_channel.strip().upper()
        if normalized not in {"RABBITMQ", "HTTP"}:
            raise ValueError("dispatch_channel must be RABBITMQ or HTTP")
        return normalized

    @staticmethod
    def _ensure_actor_identity(actual_actor_id: str, expected_actor_id: str) -> None:
        """校验操作者是否就是任务创建者。"""
        if actual_actor_id != expected_actor_id:
            logger.warning(f"Actor ID mismatch: actor={actual_actor_id}, expected={expected_actor_id}")
            raise ValueError("Actor identity mismatch")

    async def _ensure_no_active_duplicate(self, dedup_key: str, excluded_task_id: str | None = None) -> None:
        """阻止创建或修改为相同业务载荷的未完成任务。"""
        query: Dict[str, Any] = {
            "dedup_key": dedup_key,
            "overall_status": {"$nin": list(FINAL_TASK_STATUSES)},
            "is_deleted": False,
        }
        if excluded_task_id:
            query["task_id"] = {"$ne": excluded_task_id}

        pending_task = await ExecutionTaskDoc.find_one(query)
        if pending_task:
            raise ValueError(
                f"Task already exists and is not finished: existing_task_id={pending_task.task_id}"
            )

    @classmethod
    def _build_rerun_command_from_payload(
        cls,
        source_task_doc: Any,
        request: RerunTaskRequest,
        new_task_id: str,
        actor_id: str,
        dispatch_bindings: list[Any],
    ) -> DispatchExecutionTaskCommand:
        payload = dict(getattr(source_task_doc, "request_payload", {}) or {})
        cases = cls._extract_rerun_cases(payload, request)
        case_ids = [binding.case_id for binding in dispatch_bindings]
        script_entity_ids = [binding.script_entity_id for binding in dispatch_bindings]
        auto_case_ids = [case["auto_case_id"] for case in cases]
        case_configs = [dict(case.get("config") or {}) for case in cases]
        case_payloads = [
            {
                "case_id": binding.case_id,
                "script_path": binding.script_path,
                "script_name": binding.script_name,
                "parameters": dict(case.get("parameters") or {}),
                "attachments": list(case.get("attachments", [])),
            }
            for case, binding in zip(cases, dispatch_bindings)
        ]
        attachments = cls._resolve_rerun_attachments(payload, request)
        dispatch_channel = request.dispatch_channel or payload.get("dispatch_channel")
        agent_id = request.agent_id if request.agent_id is not None else payload.get("agent_id")
        schedule_type = request.schedule_type or "IMMEDIATE"
        planned_at = request.planned_at if request.schedule_type else None
        return DispatchExecutionTaskCommand(
            task_id=new_task_id,
            source_task_id=getattr(source_task_doc, "task_id", None),
            dispatch_channel=dispatch_channel,
            agent_id=agent_id,
            created_by=actor_id,
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            script_entity_ids=script_entity_ids,
            case_configs=case_configs,
            case_payloads=case_payloads,
            schedule_type=schedule_type,
            planned_at=planned_at,
            framework=request.framework if request.framework is not None else payload.get("framework"),
            trigger_source=request.trigger_source if request.trigger_source is not None else payload.get("trigger_source"),
            callback_url=request.callback_url if request.callback_url is not None else payload.get("callback_url"),
            category=request.category if request.category is not None else payload.get("category"),
            project_tag=request.project_tag if request.project_tag is not None else payload.get("project_tag"),
            repo_url=request.repo_url if request.repo_url is not None else payload.get("repo_url"),
            branch=request.branch if request.branch is not None else payload.get("branch"),
            pytest_options=cls._resolve_override_dict(request.pytest_options, payload, "pytest_options"),
            timeout=request.timeout if request.timeout is not None else payload.get("timeout"),
            dut=cls._resolve_override_dict(request.dut, payload, "dut"),
            attachments=attachments,
        )

    @staticmethod
    def _extract_rerun_cases(payload: Dict[str, Any], request: RerunTaskRequest) -> list[dict[str, Any]]:
        if request.cases is None:
            return list(payload.get("cases", []))
        return [
            {
                "auto_case_id": item.auto_case_id,
                "config": dict(item.config),
                "parameters": dict(item.parameters),
            }
            for item in request.cases
        ]

    @staticmethod
    def _resolve_rerun_attachments(payload: Dict[str, Any], request: RerunTaskRequest) -> list[dict[str, Any]]:
        if "attachments" in request.model_fields_set:
            return [
                item.model_dump(exclude_none=True)
                for item in (request.attachments or [])
            ]
        return list(payload.get("attachments") or [])

    @staticmethod
    def _resolve_override_dict(
        override_value: dict[str, Any] | None,
        payload: Dict[str, Any],
        field_name: str,
    ) -> dict[str, Any]:
        if override_value is not None:
            return dict(override_value)
        return dict(payload.get(field_name) or {})

    @classmethod
    def _apply_task_command_to_doc(
        cls,
        task_doc: ExecutionTaskDoc,
        command: DispatchExecutionTaskCommand,
        dedup_key: str,
        schedule_type: str,
        schedule_status: str,
        dispatch_status: str,
    ) -> None:
        """把任务命令映射到任务文档，复用创建/修改路径。"""
        cls._assign_fields(
            task_doc,
            agent_id=command.agent_id,
            source_task_id=command.source_task_id,
            dispatch_channel=command.dispatch_channel,
            dedup_key=dedup_key,
            case_count=len(command.case_ids),
            reported_case_count=0,
            current_case_id=command.case_ids[0],
            current_case_index=0,
            planned_at=command.planned_at,
            schedule_type=schedule_type,
            schedule_status=schedule_status,
            dispatch_status=dispatch_status,
            request_payload=cls._build_task_request_payload(command),
            dispatch_error=None,
            dispatch_response={},
            triggered_at=None,
            started_at=None,
            finished_at=None,
            last_callback_at=None,
            consume_status="PENDING",
            consumed_at=None,
            overall_status="QUEUED",
        )
