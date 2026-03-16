"""执行命令服务。"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Dict, List

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.repository.models import (
    ExecutionAgentDoc,
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher
from app.modules.test_specs.repository.models import TestCaseDoc
from app.shared.core.logger import log as logger
from app.shared.db.config import settings


class ExecutionService:
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

    @classmethod
    def _resolve_agent_runtime_status(
        cls,
        status: str,
        last_heartbeat_at: datetime,
        heartbeat_ttl_seconds: int,
        now: datetime | None = None,
    ) -> tuple[str, bool]:
        current_time = cls._ensure_utc_datetime(now or datetime.now(timezone.utc))
        heartbeat_time = cls._ensure_utc_datetime(last_heartbeat_at)
        expire_time = heartbeat_time + timedelta(seconds=max(heartbeat_ttl_seconds, 0))
        normalized_status = (status or "OFFLINE").upper()
        if normalized_status == "MAINTENANCE":
            return normalized_status, False
        if expire_time <= current_time:
            return "OFFLINE", False
        if normalized_status == "ONLINE":
            return normalized_status, True
        return normalized_status, normalized_status == "ONLINE"

    @classmethod
    def _serialize_agent_doc(
        cls,
        agent_doc: ExecutionAgentDoc,
        now: datetime | None = None,
    ) -> Dict[str, Any]:
        resolved_status, is_online = cls._resolve_agent_runtime_status(
            status=agent_doc.status,
            last_heartbeat_at=agent_doc.last_heartbeat_at,
            heartbeat_ttl_seconds=agent_doc.heartbeat_ttl_seconds,
            now=now,
        )
        data = agent_doc.model_dump()
        data["status"] = resolved_status
        data["is_online"] = is_online
        return data

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
    async def _replace_task_case_docs(
        task_id: str,
        case_ids: List[str],
        doc_map: Dict[str, Any],
    ) -> None:
        """重建尚未触发任务的 case 明细快照。"""
        existing_docs = await ExecutionTaskCaseDoc.find({"task_id": task_id}).to_list()
        for existing_doc in existing_docs:
            await existing_doc.delete()

        for case_id in case_ids:
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

    async def _dispatch_existing_task(
        self,
        task_doc: ExecutionTaskDoc,
        command: DispatchExecutionTaskCommand,
    ) -> None:
        """对已有任务执行真正下发。"""
        dispatch_result = await self._dispatcher.dispatch(command)
        task_doc.dispatch_channel = dispatch_result.channel
        task_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
        task_doc.dispatch_error = dispatch_result.error
        task_doc.dispatch_response = dispatch_result.response
        task_doc.schedule_status = "TRIGGERED" if dispatch_result.success else "FAILED"
        if dispatch_result.success and not task_doc.triggered_at:
            task_doc.triggered_at = datetime.now(timezone.utc)
        await task_doc.save()

        if dispatch_result.success:
            logger.info(f"Successfully dispatched task {command.task_id} via {dispatch_result.channel}")
        else:
            logger.warning(f"Failed to dispatch task {command.task_id} via {dispatch_result.channel}")

    async def register_agent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """注册或更新代理静态信息。"""
        agent_id = payload["agent_id"]
        now = datetime.now(timezone.utc)
        ttl_seconds = payload.get("heartbeat_ttl_seconds", 90)

        agent_doc = await ExecutionAgentDoc.find_one({
            "agent_id": agent_id,
            "is_deleted": False,
        })
        if not agent_doc:
            agent_doc = ExecutionAgentDoc(
                agent_id=agent_id,
                hostname=payload["hostname"],
                ip=payload["ip"],
                port=payload.get("port"),
                base_url=payload.get("base_url"),
                region=payload["region"],
                status=payload.get("status", "ONLINE"),
                registered_at=now,
                last_heartbeat_at=now,
                heartbeat_ttl_seconds=ttl_seconds,
            )
            await agent_doc.insert()
        else:
            agent_doc.hostname = payload["hostname"]
            agent_doc.ip = payload["ip"]
            agent_doc.port = payload.get("port")
            agent_doc.base_url = payload.get("base_url")
            agent_doc.region = payload["region"]
            agent_doc.status = payload.get("status", agent_doc.status)
            agent_doc.last_heartbeat_at = now
            agent_doc.heartbeat_ttl_seconds = ttl_seconds
            await agent_doc.save()

        return self._serialize_agent_doc(agent_doc, now=now)

    async def heartbeat_agent(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """更新代理心跳与动态状态。"""
        agent_doc = await ExecutionAgentDoc.find_one({
            "agent_id": agent_id,
            "is_deleted": False,
        })
        if not agent_doc:
            raise KeyError(f"Agent not found: {agent_id}")

        now = datetime.now(timezone.utc)
        agent_doc.status = payload.get("status", agent_doc.status)
        agent_doc.last_heartbeat_at = now
        await agent_doc.save()
        return self._serialize_agent_doc(agent_doc, now=now)

    async def list_agents(
        self,
        region: str | None = None,
        status: str | None = None,
        online_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """查询代理列表。"""
        query: Dict[str, Any] = {"is_deleted": False}
        if region:
            query["region"] = region
        docs = await ExecutionAgentDoc.find(query).sort("-updated_at").to_list()
        now = datetime.now(timezone.utc)
        result: List[Dict[str, Any]] = []
        for agent_doc in docs:
            item = self._serialize_agent_doc(agent_doc, now=now)
            if status and item["status"] != status:
                continue
            if online_only and not item["is_online"]:
                continue
            result.append(item)
        return result

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """查询单个代理详情。"""
        agent_doc = await ExecutionAgentDoc.find_one({
            "agent_id": agent_id,
            "is_deleted": False,
        })
        if not agent_doc:
            raise KeyError(f"Agent not found: {agent_id}")
        return self._serialize_agent_doc(agent_doc)

    async def list_tasks(
        self,
        schedule_type: str | None = None,
        schedule_status: str | None = None,
        dispatch_status: str | None = None,
        consume_status: str | None = None,
        overall_status: str | None = None,
        created_by: str | None = None,
        agent_id: str | None = None,
        framework: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出执行任务，支持按状态和时间窗口过滤。"""
        query: Dict[str, Any] = {"is_deleted": False}
        if schedule_type:
            query["schedule_type"] = schedule_type.upper()
        if schedule_status:
            query["schedule_status"] = schedule_status.upper()
        if dispatch_status:
            query["dispatch_status"] = dispatch_status.upper()
        if consume_status:
            query["consume_status"] = consume_status.upper()
        if overall_status:
            query["overall_status"] = overall_status.upper()
        if created_by:
            query["created_by"] = created_by
        if agent_id:
            query["agent_id"] = agent_id
        if framework:
            query["framework"] = framework
        if date_from or date_to:
            created_at_query: Dict[str, datetime] = {}
            if date_from:
                created_at_query["$gte"] = self._ensure_utc_datetime(date_from)
            if date_to:
                created_at_query["$lte"] = self._ensure_utc_datetime(date_to)
            query["created_at"] = created_at_query

        docs = await (
            ExecutionTaskDoc.find(query)
            .sort("-created_at")
            .skip(max(offset, 0))
            .limit(max(limit, 1))
            .to_list()
        )
        return [
            {
                "task_id": task_doc.task_id,
                "external_task_id": task_doc.external_task_id,
                "framework": task_doc.framework,
                "agent_id": task_doc.agent_id,
                "dispatch_channel": task_doc.dispatch_channel,
                "dedup_key": task_doc.dedup_key,
                "schedule_type": task_doc.schedule_type,
                "schedule_status": task_doc.schedule_status,
                "dispatch_status": task_doc.dispatch_status,
                "consume_status": task_doc.consume_status,
                "overall_status": task_doc.overall_status,
                "case_count": task_doc.case_count,
                "planned_at": task_doc.planned_at,
                "triggered_at": task_doc.triggered_at,
                "created_at": task_doc.created_at,
                "updated_at": task_doc.updated_at,
            }
            for task_doc in docs
        ]

    async def dispatch_execution_task(
        self,
        command: DispatchExecutionTaskCommand,
        actor_id: str
    ) -> Dict[str, Any]:
        """分发执行任务。"""
        validation_errors = command.validate()
        if validation_errors:
            raise ValueError(f"Command validation failed: {', '.join(validation_errors)}")

        if actor_id != command.created_by:
            logger.warning(f"Actor ID mismatch: actor={actor_id}, command.created_by={command.created_by}")
            raise ValueError("Actor identity mismatch")

        case_ids = command.case_ids
        doc_map = await self._load_case_docs(case_ids)

        now = datetime.now(timezone.utc)
        schedule_type, planned_at, schedule_status, should_dispatch_now = self._normalize_schedule(
            command.schedule_type,
            command.planned_at,
            now=now,
        )
        command.schedule_type = schedule_type
        command.planned_at = planned_at

        dedup_key = self._build_dedup_key(command)
        pending_task = await ExecutionTaskDoc.find_one({
            "dedup_key": dedup_key,
            "consume_status": "PENDING",
            "is_deleted": False,
        })
        if pending_task:
            raise ValueError(
                f"Task already dispatched and not yet consumed: existing_task_id={pending_task.task_id}"
            )

        task_doc = ExecutionTaskDoc(
            task_id=command.task_id,
            external_task_id=command.external_task_id,
            framework=command.framework,
            agent_id=command.agent_id,
            dispatch_channel=(settings.EXECUTION_DISPATCH_MODE or "kafka").strip().upper(),
            dedup_key=dedup_key,
            schedule_type=schedule_type,
            schedule_status=schedule_status,
            dispatch_status="DISPATCHING" if should_dispatch_now else "PENDING",
            consume_status="PENDING",
            overall_status="QUEUED",
            request_payload=command.kafka_task_data,
            dispatch_response={},
            dispatch_error=None,
            created_by=command.created_by,
            case_count=len(case_ids),
            reported_case_count=0,
            planned_at=planned_at,
        )
        await task_doc.insert()

        await self._replace_task_case_docs(command.task_id, case_ids, doc_map)

        if should_dispatch_now:
            await self._dispatch_existing_task(task_doc, command)

        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "agent_id": task_doc.agent_id,
            "dispatch_channel": task_doc.dispatch_channel,
            "dedup_key": task_doc.dedup_key,
            "schedule_type": task_doc.schedule_type,
            "schedule_status": task_doc.schedule_status,
            "dispatch_status": task_doc.dispatch_status,
            "consume_status": task_doc.consume_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "planned_at": task_doc.planned_at,
            "triggered_at": task_doc.triggered_at,
            "created_at": task_doc.created_at,
            "message": task_doc.dispatch_response.get("message", ""),
        }

    async def report_task_event(
        self,
        task_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """记录代理上报的原始任务事件。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        existing_event = await ExecutionEventDoc.find_one({
            "task_id": task_id,
            "event_id": payload["event_id"],
        })
        if existing_event:
            return {
                "task_id": existing_event.task_id,
                "event_id": existing_event.event_id,
                "event_type": existing_event.event_type,
                "seq": existing_event.seq,
                "received_at": existing_event.received_at,
                "processed": existing_event.processed,
            }

        source_time = payload.get("source_time")
        event_doc = ExecutionEventDoc(
            task_id=task_id,
            event_id=payload["event_id"],
            event_type=self._normalize_status(payload["event_type"], default="UNKNOWN"),
            seq=payload.get("seq", 0),
            source_time=self._ensure_utc_datetime(source_time) if source_time else None,
            raw_payload=payload.get("payload", {}),
            processed=True,
        )
        await event_doc.insert()

        task_doc.last_callback_at = datetime.now(timezone.utc)
        if event_doc.event_type in {"TASK_STARTED", "STARTED"} and not task_doc.started_at:
            task_doc.started_at = task_doc.last_callback_at
            task_doc.overall_status = "RUNNING"
        await task_doc.save()

        return {
            "task_id": event_doc.task_id,
            "event_id": event_doc.event_id,
            "event_type": event_doc.event_type,
            "seq": event_doc.seq,
            "received_at": event_doc.received_at,
            "processed": event_doc.processed,
        }

    async def report_case_status(
        self,
        task_id: str,
        case_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新单个测试用例执行状态。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        case_doc = await ExecutionTaskCaseDoc.find_one({"task_id": task_id, "case_id": case_id})
        if not case_doc:
            raise KeyError(f"Task case not found: {task_id}/{case_id}")

        seq = payload.get("seq", 0)
        accepted = seq >= case_doc.last_seq
        if accepted:
            status = self._normalize_status(payload["status"], default=case_doc.status)
            case_doc.status = status
            if payload.get("progress_percent") is not None:
                case_doc.progress_percent = payload["progress_percent"]
            if payload.get("step_total") is not None:
                case_doc.step_total = payload["step_total"]
            if payload.get("step_passed") is not None:
                case_doc.step_passed = payload["step_passed"]
            if payload.get("step_failed") is not None:
                case_doc.step_failed = payload["step_failed"]
            if payload.get("step_skipped") is not None:
                case_doc.step_skipped = payload["step_skipped"]
            if payload.get("started_at"):
                case_doc.started_at = self._ensure_utc_datetime(payload["started_at"])
            elif not case_doc.started_at and status in {"RUNNING", "PASSED", "FAILED", "SKIPPED"}:
                case_doc.started_at = datetime.now(timezone.utc)
            if payload.get("finished_at"):
                case_doc.finished_at = self._ensure_utc_datetime(payload["finished_at"])
            elif status in {"PASSED", "FAILED", "SKIPPED"} and not case_doc.finished_at:
                case_doc.finished_at = datetime.now(timezone.utc)
            if payload.get("event_id"):
                case_doc.last_event_id = payload["event_id"]
            case_doc.last_seq = seq
            case_doc.case_snapshot = self._merge_result_payload(
                case_doc.case_snapshot,
                payload.get("result_data", {}),
            )
            await case_doc.save()

            task_doc.last_callback_at = datetime.now(timezone.utc)
            if not task_doc.started_at:
                task_doc.started_at = task_doc.last_callback_at
            if task_doc.overall_status in {"QUEUED", "DISPATCHED"}:
                task_doc.overall_status = "RUNNING"
            finished_case_count = await ExecutionTaskCaseDoc.find({
                "task_id": task_id,
                "status": {"$in": ["PASSED", "FAILED", "SKIPPED"]},
            }).count()
            task_doc.reported_case_count = finished_case_count
            await task_doc.save()

        return {
            "task_id": task_id,
            "case_id": case_id,
            "status": case_doc.status,
            "progress_percent": case_doc.progress_percent,
            "step_total": case_doc.step_total,
            "step_passed": case_doc.step_passed,
            "step_failed": case_doc.step_failed,
            "step_skipped": case_doc.step_skipped,
            "last_seq": case_doc.last_seq,
            "accepted": accepted,
            "started_at": case_doc.started_at,
            "finished_at": case_doc.finished_at,
            "updated_at": case_doc.updated_at,
        }

    async def complete_task(
        self,
        task_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """接收任务最终完成结果。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        normalized_status = self._normalize_status(payload["status"], default=task_doc.overall_status)
        now = datetime.now(timezone.utc)
        finished_at = self._ensure_utc_datetime(payload["finished_at"]) if payload.get("finished_at") else now
        task_doc.overall_status = normalized_status
        task_doc.finished_at = finished_at
        task_doc.last_callback_at = now
        if not task_doc.started_at:
            task_doc.started_at = now
        if task_doc.dispatch_status != "DISPATCH_FAILED":
            task_doc.dispatch_status = "COMPLETED"
        task_doc.dispatch_response = self._merge_result_payload(task_doc.dispatch_response, payload.get("summary", {}))
        if payload.get("error_message"):
            task_doc.dispatch_error = payload["error_message"]
        if payload.get("executor"):
            task_doc.dispatch_response["executor"] = payload["executor"]
        if payload.get("event_id"):
            existing_event = await ExecutionEventDoc.find_one({
                "task_id": task_id,
                "event_id": payload["event_id"],
            })
            if not existing_event:
                await ExecutionEventDoc(
                    task_id=task_id,
                    event_id=payload["event_id"],
                    event_type="TASK_COMPLETED",
                    seq=payload.get("seq", 0),
                    source_time=finished_at,
                    raw_payload={
                        "status": normalized_status,
                        "summary": payload.get("summary", {}),
                        "error_message": payload.get("error_message"),
                    },
                    processed=True,
                ).insert()

        completed_case_count = await ExecutionTaskCaseDoc.find({
            "task_id": task_id,
            "status": {"$in": ["PASSED", "FAILED", "SKIPPED"]},
        }).count()
        task_doc.reported_case_count = completed_case_count
        await task_doc.save()

        return {
            "task_id": task_doc.task_id,
            "overall_status": task_doc.overall_status,
            "dispatch_status": task_doc.dispatch_status,
            "consume_status": task_doc.consume_status,
            "reported_case_count": task_doc.reported_case_count,
            "started_at": task_doc.started_at,
            "finished_at": task_doc.finished_at,
            "last_callback_at": task_doc.last_callback_at,
            "updated_at": task_doc.updated_at,
        }

    async def cancel_scheduled_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """取消未触发的定时任务。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")
        if actor_id != task_doc.created_by:
            raise ValueError("Actor identity mismatch")

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
        pending_task = await ExecutionTaskDoc.find_one({
            "dedup_key": dedup_key,
            "consume_status": "PENDING",
            "task_id": {"$ne": task_doc.task_id},
            "is_deleted": False,
        })
        if pending_task:
            raise ValueError(
                f"Task already dispatched and not yet consumed: existing_task_id={pending_task.task_id}"
            )

        task_doc.agent_id = agent_id
        task_doc.dedup_key = dedup_key
        task_doc.case_count = len(case_ids)
        task_doc.planned_at = normalized_planned_at
        task_doc.schedule_type = schedule_type
        task_doc.schedule_status = schedule_status
        task_doc.dispatch_status = "DISPATCHING" if should_dispatch_now else "PENDING"
        task_doc.request_payload = command.kafka_task_data
        task_doc.dispatch_error = None
        task_doc.dispatch_response = {}
        await task_doc.save()
        await self._replace_task_case_docs(task_doc.task_id, case_ids, doc_map)

        if should_dispatch_now:
            await self._dispatch_existing_task(task_doc, command)

        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "agent_id": task_doc.agent_id,
            "dispatch_channel": task_doc.dispatch_channel,
            "dedup_key": task_doc.dedup_key,
            "schedule_type": task_doc.schedule_type,
            "schedule_status": task_doc.schedule_status,
            "dispatch_status": task_doc.dispatch_status,
            "consume_status": task_doc.consume_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "planned_at": task_doc.planned_at,
            "triggered_at": task_doc.triggered_at,
            "created_at": task_doc.created_at,
            "updated_at": task_doc.updated_at,
        }

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

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息

        Raises:
            KeyError: 当任务不存在时
        """
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "agent_id": task_doc.agent_id,
            "dispatch_channel": task_doc.dispatch_channel,
            "dedup_key": task_doc.dedup_key,
            "schedule_type": task_doc.schedule_type,
            "schedule_status": task_doc.schedule_status,
            "dispatch_status": task_doc.dispatch_status,
            "consume_status": task_doc.consume_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "planned_at": task_doc.planned_at,
            "triggered_at": task_doc.triggered_at,
            "created_at": task_doc.created_at,
            "updated_at": task_doc.updated_at,
            "consumed_at": task_doc.consumed_at,
            "dispatch_response": task_doc.dispatch_response,
            "dispatch_error": task_doc.dispatch_error,
        }

    async def retry_failed_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """重试失败的任务。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        if task_doc.dispatch_status not in ["DISPATCH_FAILED", "FAILED"]:
            raise ValueError(f"Task {task_id} cannot be retried in status {task_doc.dispatch_status}")

        if actor_id != task_doc.created_by:
            logger.warning(f"Actor ID mismatch on retry: actor={actor_id}, task.created_by={task_doc.created_by}")
            raise ValueError("Actor identity mismatch")

        if task_doc.schedule_type == "SCHEDULED" and task_doc.schedule_status == "PENDING":
            raise ValueError(f"Task {task_id} cannot be retried before scheduled trigger")

        command = DispatchExecutionTaskCommand(
            task_id=task_doc.task_id,
            external_task_id=task_doc.external_task_id or f"EXT-{task_doc.task_id}",
            framework=task_doc.framework,
            agent_id=task_doc.agent_id,
            trigger_source=task_doc.request_payload.get("trigger_source", "manual"),
            created_by=task_doc.created_by,
            case_ids=[case["case_id"] for case in task_doc.request_payload.get("cases", [])],
            schedule_type=task_doc.schedule_type,
            planned_at=self._ensure_utc_datetime(task_doc.planned_at) if task_doc.planned_at else None,
            callback_url=task_doc.request_payload.get("callback_url"),
            dut=task_doc.request_payload.get("dut"),
            runtime_config=task_doc.request_payload.get("runtime_config"),
            kafka_task_data=task_doc.request_payload,
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
