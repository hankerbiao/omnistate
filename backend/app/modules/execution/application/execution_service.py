"""执行命令服务。"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List

from app.modules.execution.application.agent_mixin import ExecutionAgentMixin
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.constants import FINAL_TASK_STATUSES
from app.modules.execution.application.progress_mixin import ExecutionProgressMixin
from app.modules.execution.application.query_mixin import ExecutionTaskQueryMixin
from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher
from app.modules.test_specs.repository.models import TestCaseDoc
from app.shared.core.logger import log as logger


class ExecutionService(ExecutionProgressMixin, ExecutionTaskQueryMixin, ExecutionAgentMixin):
    """执行任务分发服务。"""

    def __init__(self) -> None:
        self._dispatcher = ExecutionTaskDispatcher()

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
            "runtime_config": command.runtime_config or {},
            "case_ids": sorted(command.case_ids),
        }
        normalized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _ensure_utc_datetime(value: datetime) -> datetime:
        """将 naive/aware datetime 统一规范为 UTC aware datetime。"""
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
    def _normalize_status(value: str, default: str = "UNKNOWN") -> str:
        """统一状态字符串格式。"""
        return (value or default).strip().upper()

    @staticmethod
    def _merge_result_payload(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
        """合并执行结果扩展信息。"""
        merged = dict(base or {})
        merged.update(extra or {})
        return merged

    @staticmethod
    async def _load_case_docs(case_ids: List[str]) -> Dict[str, Any]:
        """加载并校验任务关联的测试用例。"""
        docs = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False,
        }).to_list()
        doc_map = {doc.case_id: doc for doc in docs}
        missing = [cid for cid in case_ids if cid not in doc_map]
        if missing:
            raise KeyError(f"Test cases not found: {missing}")
        return doc_map

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
            "cases": [{"case_id": cid} for cid in command.case_ids],
            "runtime_config": command.runtime_config or {},
            "created_by": command.created_by,
        }

    @staticmethod
    def _extract_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        return [case["case_id"] for case in payload.get("cases", [])]

    @classmethod
    def _build_case_dispatch_command(
            cls,
            task_doc: ExecutionTaskDoc,
            case_ids: List[str],
            dispatch_case_id: str,
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
            case_ids=case_ids,
            dispatch_case_id=dispatch_case_id,
            dispatch_case_index=dispatch_case_index,
            schedule_type=task_doc.schedule_type,
            planned_at=cls._ensure_utc_datetime(planned_at) if planned_at else None,
            callback_url=request_payload.get("callback_url"),
            dut=request_payload.get("dut"),
            runtime_config=request_payload.get("runtime_config"),
        )

    @staticmethod
    async def _replace_task_case_docs(
            task_id: str,
            case_ids: List[str],
            doc_map: Dict[str, Any],
    ) -> None:
        """重建尚未触发任务的 case 明细快照。"""
        existing_docs = await ExecutionTaskCaseDoc.find({"task_id": task_id}).to_list()
        for existing_doc in existing_docs:
            await existing_doc.delete()

        for order_no, case_id in enumerate(case_ids):
            case_doc = doc_map[case_id]
            snapshot = {
                "case_id": case_doc.case_id,
                "title": case_doc.title,
                "version": case_doc.version,
                "priority": case_doc.priority,
                "status": getattr(case_doc, "status", "待执行"),
            }
            await ExecutionTaskCaseDoc(
                task_id=task_id,
                case_id=case_id,
                case_snapshot=snapshot,
                order_no=order_no,
                dispatch_status="PENDING",
                status="QUEUED",
                last_seq=0,
            ).insert()

    @staticmethod
    def _ensure_pending_scheduled_task(task_doc: ExecutionTaskDoc) -> None:
        """限制取消/修改仅作用于未触发的定时任务。"""
        if task_doc.schedule_type != "SCHEDULED":
            raise ValueError(f"Task {task_doc.task_id} is not a scheduled task")
        if task_doc.schedule_status != "PENDING":
            raise ValueError(
                f"Task {task_doc.task_id} cannot be changed in schedule_status {task_doc.schedule_status}"
            )

    @staticmethod
    def _ensure_actor_identity(actual_actor_id: str, expected_actor_id: str) -> None:
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

    @staticmethod
    def _apply_task_command_to_doc(
            task_doc: ExecutionTaskDoc,
            command: DispatchExecutionTaskCommand,
            dedup_key: str,
            schedule_type: str,
            schedule_status: str,
            dispatch_status: str,
    ) -> None:
        """把任务命令映射到任务文档，复用创建/修改路径。"""
        task_doc.agent_id = command.agent_id
        task_doc.dedup_key = dedup_key
        task_doc.case_count = len(command.case_ids)
        task_doc.current_case_id = command.case_ids[0]
        task_doc.current_case_index = 0
        task_doc.planned_at = command.planned_at
        task_doc.schedule_type = schedule_type
        task_doc.schedule_status = schedule_status
        task_doc.dispatch_status = dispatch_status
        task_doc.request_payload = ExecutionService._build_task_request_payload(command)
        task_doc.dispatch_error = None
        task_doc.dispatch_response = {}

    async def _dispatch_first_case_if_needed(
            self,
            task_doc: ExecutionTaskDoc,
            should_dispatch_now: bool,
    ) -> None:
        """统一处理首条 case 的实际下发。"""
        if not should_dispatch_now:
            return
        case_ids = self._extract_case_ids_from_payload(task_doc.request_payload)
        await self._dispatch_existing_task(
            task_doc,
            self._build_case_dispatch_command(
                task_doc=task_doc,
                case_ids=case_ids,
                dispatch_case_id=case_ids[0],
                dispatch_case_index=0,
            ),
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
        task_doc.dispatch_channel = dispatch_result.channel
        task_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
        task_doc.dispatch_error = dispatch_result.error
        task_doc.dispatch_response = dispatch_result.response
        task_doc.schedule_status = "TRIGGERED" if dispatch_result.success else "FAILED"
        task_doc.current_case_id = command.dispatch_case_id
        task_doc.current_case_index = command.dispatch_case_index
        if dispatch_result.success and not task_doc.triggered_at:
            task_doc.triggered_at = datetime.now(timezone.utc)
        await task_doc.save()

        if case_doc:
            case_doc.dispatch_attempts += 1
            case_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
            case_doc.dispatched_at = datetime.now(timezone.utc)
            await case_doc.save()

        if dispatch_result.success:
            logger.info(f"Successfully dispatched task {command.task_id} via {dispatch_result.channel}")
        else:
            logger.warning(f"Failed to dispatch task {command.task_id} via {dispatch_result.channel}")

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

        return {
            "task_id": task_doc.task_id,
            "schedule_type": task_doc.schedule_type,
            "schedule_status": task_doc.schedule_status,
            "dispatch_status": task_doc.dispatch_status,
            "overall_status": task_doc.overall_status,
            "planned_at": task_doc.planned_at,
            "triggered_at": task_doc.triggered_at,
            "updated_at": task_doc.updated_at,
        }

    async def update_scheduled_task(
            self,
            task_id: str,
            actor_id: str,
            payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """修改未触发的定时任务。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")
        if actor_id != task_doc.created_by:
            raise ValueError("Actor identity mismatch")

        self._ensure_pending_scheduled_task(task_doc)

        request_payload = dict(task_doc.request_payload or {})
        case_items = payload.get("cases")
        case_ids = [item["case_id"] for item in case_items] if case_items is not None else [
            case["case_id"] for case in request_payload.get("cases", [])
        ]
        if not case_ids:
            raise ValueError("cases cannot be empty")

        doc_map = await self._load_case_docs(case_ids)
        planned_at = payload.get("planned_at", task_doc.planned_at)
        agent_id = payload.get("agent_id", task_doc.agent_id)
        callback_url = payload.get("callback_url", request_payload.get("callback_url"))
        dut = payload.get("dut", request_payload.get("dut", {}))
        runtime_config = payload.get("runtime_config", request_payload.get("runtime_config", {}))
        trigger_source = request_payload.get("trigger_source", "manual")

        schedule_type, normalized_planned_at, schedule_status, should_dispatch_now = self._normalize_schedule(
            task_doc.schedule_type,
            planned_at,
        )

        command = DispatchExecutionTaskCommand(
            task_id=task_doc.task_id,
            external_task_id=task_doc.external_task_id or f"EXT-{task_doc.task_id}",
            framework=task_doc.framework,
            agent_id=agent_id,
            trigger_source=trigger_source,
            created_by=task_doc.created_by,
            case_ids=case_ids,
            schedule_type=schedule_type,
            planned_at=normalized_planned_at,
            callback_url=callback_url,
            dut=dut,
            runtime_config=runtime_config,
        )
        dedup_key = self._build_dedup_key(command)
        await self._ensure_no_active_duplicate(dedup_key, excluded_task_id=task_doc.task_id)

        self._apply_task_command_to_doc(
            task_doc=task_doc,
            command=command,
            dedup_key=dedup_key,
            schedule_type=schedule_type,
            schedule_status=schedule_status,
            dispatch_status="DISPATCHING" if should_dispatch_now else "PENDING",
        )
        await task_doc.save()
        await self._replace_task_case_docs(task_doc.task_id, case_ids, doc_map)
        await self._dispatch_first_case_if_needed(task_doc, should_dispatch_now)

        return self._serialize_task_doc(task_doc)

    async def ack_task_consumed(self, task_id: str, consumer_id: str | None = None) -> Dict[str, Any]:
        """标记任务已被消费者消费。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        now = datetime.now(timezone.utc)
        task_doc.consume_status = "CONSUMED"
        task_doc.consumed_at = now
        if consumer_id:
            task_doc.dispatch_response["consumer_id"] = consumer_id
        await task_doc.save()

        return {
            "task_id": task_doc.task_id,
            "consume_status": task_doc.consume_status,
            "consumed_at": task_doc.consumed_at,
        }

    async def retry_failed_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """重试失败的任务。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        if task_doc.dispatch_status not in ["DISPATCH_FAILED", "FAILED"]:
            raise ValueError(f"Task {task_id} cannot be retried in status {task_doc.dispatch_status}")

        self._ensure_actor_identity(actor_id, task_doc.created_by)

        if task_doc.schedule_type == "SCHEDULED" and task_doc.schedule_status == "PENDING":
            raise ValueError(f"Task {task_id} cannot be retried before scheduled trigger")

        case_ids = self._extract_case_ids_from_payload(task_doc.request_payload)
        current_case_id = task_doc.current_case_id or case_ids[min(task_doc.current_case_index, len(case_ids) - 1)]
        current_case_index = case_ids.index(current_case_id)
        command = self._build_case_dispatch_command(
            task_doc=task_doc,
            case_ids=case_ids,
            dispatch_case_id=current_case_id,
            dispatch_case_index=current_case_index,
        )
        task_doc.schedule_status = "READY"
        task_doc.triggered_at = None
        await self._dispatch_existing_task(task_doc, command)
        task_doc.consume_status = "PENDING"
        task_doc.consumed_at = None
        await task_doc.save()

        if task_doc.dispatch_status == "DISPATCHED":
            logger.info(f"Task {task_id} retried successfully")
        else:
            logger.warning(f"Task {task_id} retry failed")

        return {
            "task_id": task_doc.task_id,
            "status": "retried" if task_doc.dispatch_status == "DISPATCHED" else "retry_failed",
            "message": task_doc.dispatch_response["message"],
        }
