"""执行代理相关服务能力。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.modules.execution.repository.models import ExecutionAgentDoc


class ExecutionAgentMixin:
    """执行代理的注册、心跳与查询能力。"""

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
