"""Kafka 健康检查模块。

在 FastAPI 主服务启动时调用，确保 Kafka Broker 和 Kafka Worker 都已就绪。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

from app.modules.execution.application.worker_presence import get_kafka_worker_agent_id
from app.modules.execution.repository.models import ExecutionAgentDoc
from app.shared.kafka.config import load_kafka_config


# 心跳过期倍数 = TTL × 倍数。
# Worker 心跳间隔 = TTL / 3（见 worker_presence.get_kafka_worker_heartbeat_interval_seconds），
# 所以 2×TTL 已经远超预期周期，足以判断 Worker 失联。
HEARTBEAT_EXPIRY_MULTIPLIER = 2

# TCP 连接单次超时（秒）。
BROKER_CONNECT_TIMEOUT_SEC = 5.0


@dataclass(slots=True)
class HealthCheckResult:
    """单次检查的结果。"""

    healthy: bool
    detail: str

    @classmethod
    def ok(cls, detail: str) -> "HealthCheckResult":
        return cls(healthy=True, detail=detail)

    @classmethod
    def fail(cls, detail: str) -> "HealthCheckResult":
        return cls(healthy=False, detail=detail)


async def check_kafka_health() -> HealthCheckResult:
    """检查 Kafka 基础设施是否健康。

    包含两项检查：
    1. Kafka Broker TCP 连通性
    2. Kafka Worker 进程心跳

    Returns:
        HealthCheckResult，healthy=False 时 detail 描述失败原因。
    """
    config = load_kafka_config()
    broker = await _check_broker_connectivity(config.bootstrap_servers)
    if not broker.healthy:
        return HealthCheckResult.fail(f"Kafka Broker 不可达: {broker.detail}")

    worker = await _check_worker_heartbeat()
    if not worker.healthy:
        return HealthCheckResult.fail(f"Kafka Worker 未运行: {worker.detail}")

    return HealthCheckResult.ok(
        f"broker={broker.detail}; worker={worker.detail}"
    )


async def _check_broker_connectivity(
    bootstrap_servers: list[str],
    timeout: float = BROKER_CONNECT_TIMEOUT_SEC,
) -> HealthCheckResult:
    """通过 TCP 连接检查 Kafka Broker 是否可达。"""
    for server in bootstrap_servers:
        try:
            host, port_str = server.split(":")
            port = int(port_str)
        except ValueError:
            return HealthCheckResult.fail(f"无效的服务器地址格式: {server}")

        try:
            # StreamWriter.close() 是同步方法，wait_closed() 才是异步清理
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()
        except OSError as exc:
            return HealthCheckResult.fail(f"{server} - {exc.strerror}")
        except asyncio.TimeoutError:
            return HealthCheckResult.fail(f"{server} - 连接超时({timeout}s)")

    return HealthCheckResult.ok(f"{', '.join(bootstrap_servers)} - 全部可达")


async def _check_worker_heartbeat() -> HealthCheckResult:
    """检查 Kafka Worker 心跳是否有效。

    如果心跳记录不存在或已过期（超过 TTL × HEARTBEAT_EXPIRY_MULTIPLIER），
    则认为 Worker 不可用。
    """
    agent_id = get_kafka_worker_agent_id()
    agent = await ExecutionAgentDoc.find_one(
        ExecutionAgentDoc.agent_id == agent_id,
        ExecutionAgentDoc.is_deleted == False,
    )
    if agent is None:
        return HealthCheckResult.fail(
            f"MongoDB 中未找到 agent '{agent_id}'，请先启动 Kafka Worker"
        )

    if agent.last_heartbeat_at is None:
        return HealthCheckResult.fail(f"agent '{agent_id}' 从未上报心跳")

    ttl = agent.heartbeat_ttl_seconds or 30
    last_heartbeat = _to_naive_utc(agent.last_heartbeat_at)
    elapsed = (datetime.utcnow() - last_heartbeat).total_seconds()
    if elapsed > ttl * HEARTBEAT_EXPIRY_MULTIPLIER:
        return HealthCheckResult.fail(
            f"agent '{agent_id}' 心跳已过期 "
            f"(上次心跳: {elapsed:.0f}s 前, TTL: {ttl}s)"
        )

    return HealthCheckResult.ok(f"agent '{agent_id}' 心跳正常 ({elapsed:.0f}s 前)")


def _to_naive_utc(value: datetime) -> datetime:
    """统一把 datetime 转换为 naive UTC，便于和 datetime.utcnow() 相减。"""
    if value.tzinfo is None:
        return value
    return value.replace(tzinfo=None)
