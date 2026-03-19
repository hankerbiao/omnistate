"""执行任务命令公共能力。"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.constants import FINAL_TASK_STATUSES, STOP_MODE_NONE
from app.modules.execution.repository.models import ExecutionTaskDoc
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
            "framework": command.framework,
            "agent_id": command.agent_id,
            "trigger_source": command.trigger_source,
            "schedule_type": command.schedule_type,
            "planned_at": command.planned_at.isoformat() if command.planned_at else None,
            "callback_url": command.callback_url,
            "dut": command.dut or {},
            "case_ids": sorted(command.case_ids),
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
            "external_task_id": command.external_task_id,
            "framework": command.framework,
            "trigger_source": command.trigger_source,
            "agent_id": command.agent_id,
            "schedule_type": command.schedule_type,
            "planned_at": command.planned_at.isoformat() if command.planned_at else None,
            "callback_url": command.callback_url,
            "dut": command.dut or {},
            "cases": [
                {"case_id": case_id, "auto_case_id": auto_case_id}
                for case_id, auto_case_id in zip(command.case_ids, command.auto_case_ids)
            ],
            "created_by": command.created_by,
        }

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
            dedup_key=dedup_key,
            case_count=len(command.case_ids),
            reported_case_count=0,
            current_case_id=command.case_ids[0],
            current_case_index=0,
            stop_mode=STOP_MODE_NONE,
            stop_requested_at=None,
            stop_requested_by=None,
            stop_reason=None,
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
            orchestration_lock=None,
        )
