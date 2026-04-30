"""执行代理相关服务能力。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.modules.execution.repository.models import ExecutionAgentDoc


class ExecutionAgentMixin:
    """执行代理的注册、心跳与查询能力。

    这个 mixin 负责维护平台视角下的“执行代理当前态”：

    - 注册时保存代理的静态信息，例如主机名、IP、区域、base_url
    - 心跳时刷新代理的动态信息，例如最近心跳时间和当前声明状态
    - 查询时基于心跳时间和 TTL 推导真实在线状态，而不是盲信数据库中的 `status`

    这里的设计重点是：

    - 数据库存的是“最近一次上报状态 + 最近一次心跳时间”
    - 对外返回的是“根据 TTL 推导后的运行时状态”
    """

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
    def _resolve_agent_runtime_status(
        cls,
        status: str,
        last_heartbeat_at: datetime,
        heartbeat_ttl_seconds: int,
        now: datetime | None = None,
    ) -> tuple[str, bool]:
        """根据数据库中的静态状态和心跳时间，推导代理的真实运行状态。

        Args:
            status: 数据库中记录的代理状态，通常来自注册或心跳上报
            last_heartbeat_at: 最近一次心跳时间
            heartbeat_ttl_seconds: 心跳有效期，超过该时间未续约则视为离线
            now: 可选的当前时间，主要用于测试时注入固定时间

        Returns:
            tuple[str, bool]:
            - 第一个值是对外展示的归一化状态
            - 第二个值表示平台是否认为该代理当前在线

        判定规则：
            1. `MAINTENANCE` 永远视为非在线，但保留其状态文案
            2. 心跳过期则强制降级为 `OFFLINE`
            3. 心跳未过期且状态为 `ONLINE` 时，才认为真正在线
            4. 其他状态原样保留，但 `is_online=False`
        """
        # 统一把参与比较的时间转换为 UTC aware datetime，避免 naive/aware 混用。
        current_time = cls._ensure_utc_datetime(now or datetime.now(timezone.utc))
        heartbeat_time = cls._ensure_utc_datetime(last_heartbeat_at)
        # TTL 小于 0 时按 0 处理，防止错误配置导致过期判断异常。
        expire_time = heartbeat_time + timedelta(seconds=max(heartbeat_ttl_seconds, 0))
        normalized_status = (status or "OFFLINE").upper()
        # 维护态是显式业务状态，不应因为心跳未过期被误判为在线。
        if normalized_status == "MAINTENANCE":
            return normalized_status, False
        # 心跳到期后，无论数据库里原状态是什么，都按离线处理。
        if expire_time <= current_time:
            return "OFFLINE", False
        # 只有显式 ONLINE 且心跳未过期时，平台才把代理视为在线可调度。
        if normalized_status == "ONLINE":
            return normalized_status, True
        # 其他状态保持原文案，便于排查，但都不参与在线调度。
        return normalized_status, normalized_status == "ONLINE"

    @classmethod
    def _serialize_agent_doc(
        cls,
        agent_doc: ExecutionAgentDoc,
        now: datetime | None = None,
    ) -> Dict[str, Any]:
        """把数据库文档序列化为接口返回结构。

        这里会覆盖文档里原始 `status`，替换成运行时推导后的状态，
        并额外补一个 `is_online` 字段，方便前端或调度逻辑直接使用。
        """
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
        """注册代理，或刷新已存在代理的静态信息。

        Args:
            payload: 代理注册请求体，通常来自
                `POST /api/v1/execution/agents/register`

        Returns:
            当前代理的序列化结果，包含运行时推导后的 `status/is_online`

        行为说明：
            - 若代理不存在，则创建新记录
            - 若代理已存在，则更新静态信息并顺带刷新心跳
            - 注册行为会把 `last_heartbeat_at` 直接更新为当前时间，
              因为注册本身就代表该代理此刻是活跃的
        """
        agent_id = payload["agent_id"]
        now = datetime.now(timezone.utc)
        ttl_seconds = payload.get("heartbeat_ttl_seconds", 90)

        agent_doc = await ExecutionAgentDoc.find_one({
            "agent_id": agent_id,
            "is_deleted": False,
        })
        if not agent_doc:
            # 首次注册：直接创建代理记录，并把注册时间和心跳时间初始化为当前时刻。
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
            # 重复注册：视为刷新代理元信息，例如 IP、端口、区域或 base_url 变化。
            agent_doc.hostname = payload["hostname"]
            agent_doc.ip = payload["ip"]
            agent_doc.port = payload.get("port")
            agent_doc.base_url = payload.get("base_url")
            agent_doc.region = payload["region"]
            # 若调用方显式带了 status，则采用新状态；否则保留原状态。
            agent_doc.status = payload.get("status", agent_doc.status)
            # 注册也相当于一次活跃声明，因此刷新心跳和 TTL。
            agent_doc.last_heartbeat_at = now
            agent_doc.heartbeat_ttl_seconds = ttl_seconds
            await agent_doc.save()

        return self._serialize_agent_doc(agent_doc, now=now)

    async def heartbeat_agent(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """刷新指定代理的心跳时间，并可选更新其动态状态。

        Args:
            agent_id: 目标代理 ID
            payload: 心跳请求体，允许携带最新 `status`

        Returns:
            更新后的代理序列化结果

        Raises:
            KeyError: 目标代理不存在时抛出

        设计上，心跳接口只更新“活性相关”信息：
            - `last_heartbeat_at`
            - 可选的 `status`

        它不会修改主机名、IP、端口、区域等静态信息，
        这些信息统一由注册接口维护。
        """
        agent_doc = await ExecutionAgentDoc.find_one({
            "agent_id": agent_id,
            "is_deleted": False,
        })
        if not agent_doc:
            raise KeyError(f"Agent not found: {agent_id}")

        now = datetime.now(timezone.utc)
        # 心跳允许代理顺带声明自己当前进入了某个状态，例如 ONLINE/OFFLINE/MAINTENANCE。
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
        """查询代理列表，并按运行时状态做二次过滤。

        Args:
            region: 可选区域过滤
            status: 可选状态过滤，基于“推导后的状态”过滤，不是数据库原始值
            online_only: 是否只保留当前在线代理

        Returns:
            序列化后的代理列表

        注意：
            这里先查数据库，再逐条做运行时状态推导。
            这么做的原因是“是否在线”依赖当前时间和 TTL，
            无法只靠静态 Mongo 查询准确表达。
        """
        query: Dict[str, Any] = {"is_deleted": False}
        if region:
            query["region"] = region
        docs = await ExecutionAgentDoc.find(query).sort("-updated_at").to_list()
        # 同一轮列表查询使用同一个 now，避免边界时刻前后两条数据出现判定抖动。
        now = datetime.now(timezone.utc)
        result: List[Dict[str, Any]] = []
        for agent_doc in docs:
            item = self._serialize_agent_doc(agent_doc, now=now)
            # `status` 过滤以推导后的结果为准，例如心跳过期后会被识别为 OFFLINE。
            if status and item["status"] != status:
                continue
            # `online_only` 比状态过滤更直接，只关心是否可用。
            if online_only and not item["is_online"]:
                continue
            result.append(item)
        return result

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """查询单个代理详情。

        Args:
            agent_id: 目标代理 ID

        Returns:
            代理详情，包含推导后的状态和在线标记

        Raises:
            KeyError: 代理不存在时抛出
        """
        agent_doc = await ExecutionAgentDoc.find_one({
            "agent_id": agent_id,
            "is_deleted": False,
        })
        if not agent_doc:
            raise KeyError(f"Agent not found: {agent_id}")
        return self._serialize_agent_doc(agent_doc)
