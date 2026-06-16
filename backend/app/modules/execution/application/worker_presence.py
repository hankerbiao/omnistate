"""Kafka worker presence registration helpers."""

from __future__ import annotations

import socket
from datetime import datetime, timezone

from app.modules.execution.application.constants import AgentStatus
from app.modules.execution.repository.models import ExecutionAgentDoc
from app.shared.core.logger import log
from app.shared.config import get_settings


def _detect_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def get_kafka_worker_agent_id() -> str:
    return get_settings().execution.kafka_worker_agent_id


def get_kafka_worker_heartbeat_ttl_seconds() -> int:
    return max(int(get_settings().execution.kafka_worker_heartbeat_ttl_sec), 5)


def get_kafka_worker_heartbeat_interval_seconds() -> int:
    ttl_seconds = get_kafka_worker_heartbeat_ttl_seconds()
    configured_interval = max(int(get_settings().execution.kafka_worker_heartbeat_interval_sec), 1)
    return min(configured_interval, max(ttl_seconds // 3, 1))


async def upsert_kafka_worker_presence(status: str = AgentStatus.ONLINE) -> ExecutionAgentDoc:
    """使用 Beanie 的 upsert 方法避免唯一索引冲突。

    使用 update_one + upsert 模式，而不是 find-then-insert，
    这样即使存在被软删除的记录也能正确更新。
    """
    now = datetime.now(timezone.utc)
    ttl_seconds = get_kafka_worker_heartbeat_ttl_seconds()
    agent_id = get_kafka_worker_agent_id()
    hostname = socket.gethostname()
    ip = _detect_local_ip()

    agent_doc = await ExecutionAgentDoc.find_one(
        ExecutionAgentDoc.agent_id == agent_id
    ).upsert(
        {
            "$set": {
                "hostname": hostname,
                "ip": ip,
                "status": status,
                "last_heartbeat_at": now,
                "heartbeat_ttl_seconds": ttl_seconds,
                "is_deleted": False,
            },
        },
        on_insert=ExecutionAgentDoc(
            agent_id=agent_id,
            hostname=hostname,
            ip=ip,
            port=None,
            base_url=None,
            region="system",
            status=status,
            registered_at=now,
            last_heartbeat_at=now,
            heartbeat_ttl_seconds=ttl_seconds,
        ),
    )
    log.debug(f"Kafka worker presence upserted: agent_id={agent_id}, status={status}")
    return agent_doc


async def mark_kafka_worker_offline() -> None:
    agent_doc = await ExecutionAgentDoc.find_one({
        "agent_id": get_kafka_worker_agent_id(),
        "is_deleted": False,
    })
    if agent_doc is None:
        return
    agent_doc.status = AgentStatus.OFFLINE
    agent_doc.last_heartbeat_at = datetime.now(timezone.utc)
    await agent_doc.save()
