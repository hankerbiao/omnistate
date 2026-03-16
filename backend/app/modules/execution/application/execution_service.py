"""执行命令服务。"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Dict, List

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.repository.models import (
    ExecutionAgentDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.execution.service import ExecutionTaskDispatcher
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
        docs = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False
        }).to_list()

        doc_map = {doc.case_id: doc for doc in docs}
        missing = [cid for cid in case_ids if cid not in doc_map]
        if missing:
            raise KeyError(f"Test cases not found: {missing}")

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
            dispatch_status="DISPATCHING",
            consume_status="PENDING",
            overall_status="QUEUED",
            request_payload=command.kafka_task_data,
            dispatch_response={},
            dispatch_error=None,
            created_by=command.created_by,
            case_count=len(case_ids),
            reported_case_count=0,
        )
        await task_doc.insert()

        for cid in case_ids:
            case_doc = doc_map[cid]
            snapshot = {
                "case_id": case_doc.case_id,
                "title": case_doc.title,
                "version": case_doc.version,
                "priority": case_doc.priority,
                "status": getattr(case_doc, "status", "待执行"),
            }

            await ExecutionTaskCaseDoc(
                task_id=command.task_id,
                case_id=cid,
                case_snapshot=snapshot,
                status="QUEUED",
                last_seq=0,
            ).insert()

        dispatch_result = await self._dispatcher.dispatch(command)
        task_doc.dispatch_channel = dispatch_result.channel
        task_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
        task_doc.dispatch_error = dispatch_result.error
        task_doc.dispatch_response = dispatch_result.response

        if dispatch_result.success:
            logger.info(f"Successfully dispatched task {command.task_id} via {dispatch_result.channel}")
        else:
            logger.warning(f"Failed to dispatch task {command.task_id} via {dispatch_result.channel}")

        await task_doc.save()
        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "agent_id": task_doc.agent_id,
            "dispatch_channel": task_doc.dispatch_channel,
            "dedup_key": task_doc.dedup_key,
            "dispatch_status": task_doc.dispatch_status,
            "consume_status": task_doc.consume_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "created_at": task_doc.created_at,
            "message": task_doc.dispatch_response.get("message", ""),
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
            "dispatch_status": task_doc.dispatch_status,
            "consume_status": task_doc.consume_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
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

        command = DispatchExecutionTaskCommand(
            task_id=task_doc.task_id,
            external_task_id=task_doc.external_task_id or f"EXT-{task_doc.task_id}",
            framework=task_doc.framework,
            agent_id=task_doc.agent_id,
            trigger_source=task_doc.request_payload.get("trigger_source", "manual"),
            created_by=task_doc.created_by,
            case_ids=[case["case_id"] for case in task_doc.request_payload.get("cases", [])],
            callback_url=task_doc.request_payload.get("callback_url"),
            dut=task_doc.request_payload.get("dut"),
            runtime_config=task_doc.request_payload.get("runtime_config"),
            kafka_task_data=task_doc.request_payload,
        )
        dispatch_result = await self._dispatcher.dispatch(command)

        task_doc.dispatch_channel = dispatch_result.channel
        task_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
        task_doc.consume_status = "PENDING"
        task_doc.consumed_at = None
        task_doc.dispatch_error = dispatch_result.error
        task_doc.dispatch_response = dispatch_result.response
        await task_doc.save()

        if dispatch_result.success:
            logger.info(f"Task {task_id} retried successfully")
        else:
            logger.warning(f"Task {task_id} retry failed")

        return {
            "task_id": task_doc.task_id,
            "status": "retried" if dispatch_result.success else "retry_failed",
            "message": task_doc.dispatch_response["message"],
        }
