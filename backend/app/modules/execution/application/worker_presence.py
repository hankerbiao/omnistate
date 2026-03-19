"""Kafka worker presence registration and startup gate helpers."""

from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone

from app.modules.execution.repository.models import ExecutionAgentDoc
from app.shared.db.config import settings


def _detect_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_kafka_worker_agent_id() -> str:
    return settings.EXECUTION_KAFKA_WORKER_AGENT_ID


def get_kafka_worker_heartbeat_ttl_seconds() -> int:
    return max(int(settings.EXECUTION_KAFKA_WORKER_HEARTBEAT_TTL_SEC), 5)


def get_kafka_worker_heartbeat_interval_seconds() -> int:
    ttl_seconds = get_kafka_worker_heartbeat_ttl_seconds()
    configured_interval = max(int(settings.EXECUTION_KAFKA_WORKER_HEARTBEAT_INTERVAL_SEC), 1)
    return min(configured_interval, max(ttl_seconds // 3, 1))


async def upsert_kafka_worker_presence(status: str = "ONLINE") -> ExecutionAgentDoc:
    now = datetime.now(timezone.utc)
    ttl_seconds = get_kafka_worker_heartbeat_ttl_seconds()
    agent_id = get_kafka_worker_agent_id()
    agent_doc = await ExecutionAgentDoc.find_one({
        "agent_id": agent_id,
        "is_deleted": False,
    })
    if agent_doc is None:
        agent_doc = ExecutionAgentDoc(
            agent_id=agent_id,
            hostname=socket.gethostname(),
            ip=_detect_local_ip(),
            port=None,
            base_url=None,
            region="system",
            status=status,
            registered_at=now,
            last_heartbeat_at=now,
            heartbeat_ttl_seconds=ttl_seconds,
        )
        await agent_doc.insert()
        return agent_doc

    agent_doc.hostname = socket.gethostname()
    agent_doc.ip = _detect_local_ip()
    agent_doc.status = status
    agent_doc.last_heartbeat_at = now
    agent_doc.heartbeat_ttl_seconds = ttl_seconds
    await agent_doc.save()
    return agent_doc


async def mark_kafka_worker_offline() -> None:
    agent_doc = await ExecutionAgentDoc.find_one({
        "agent_id": get_kafka_worker_agent_id(),
        "is_deleted": False,
    })
    if agent_doc is None:
        return
    agent_doc.status = "OFFLINE"
    agent_doc.last_heartbeat_at = datetime.now(timezone.utc)
    await agent_doc.save()


async def ensure_kafka_worker_available() -> None:
    health = await get_kafka_worker_health()
    if health["status"] != "ONLINE":
        raise RuntimeError(health["message"])


async def get_kafka_worker_health() -> dict[str, str]:
    agent_doc = await ExecutionAgentDoc.find_one({
        "agent_id": get_kafka_worker_agent_id(),
        "is_deleted": False,
    })
    if agent_doc is None:
        return {
            "status": "OFFLINE",
            "message": (
                "execution kafka worker is required but not registered; "
                f"start `python -m app.workers.kafka_worker_main` first "
                f"(agent_id={get_kafka_worker_agent_id()})"
            ),
        }

    last_heartbeat_at = _ensure_utc_datetime(agent_doc.last_heartbeat_at)
    expire_at = last_heartbeat_at + timedelta(seconds=max(agent_doc.heartbeat_ttl_seconds, 0))
    now = datetime.now(timezone.utc)
    if (agent_doc.status or "").upper() != "ONLINE" or expire_at <= now:
        return {
            "status": "OFFLINE",
            "message": (
                "execution kafka worker is required but offline; "
                f"start `python -m app.workers.kafka_worker_main` first "
                f"(agent_id={agent_doc.agent_id})"
            ),
        }
    return {
        "status": "ONLINE",
        "message": f"execution kafka worker is online (agent_id={agent_doc.agent_id})",
    }
