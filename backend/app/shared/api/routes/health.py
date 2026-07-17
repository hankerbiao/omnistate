"""
健康检查路由

用于监控服务健康状态：
- GET /health      基础健康检查（反映基础设施概况）
- GET /health/ready 就绪检查（真实依赖探测，未就绪返回 503）
- GET /health/live  存活检查
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Response, status

from app.shared.api.schemas.base import APIResponse
from app.shared.core.mongo_client import get_mongo_client
from app.shared.infrastructure import get_infrastructure_registry
# 运行时读取 Redis 连接，避免模块导入时绑定到未初始化的 None。
# init_redis() 会在 lifespan 中重新赋值 app.shared.redis.service.redis_conn。
from app.shared.redis import service as redis_service

router = APIRouter()

_COMPONENT_MONGODB = "mongodb"
_COMPONENT_REDIS = "redis"


async def _check_mongodb() -> dict:
    """探测 MongoDB 连通性（服务处理请求的关键依赖）。"""
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        return {"status": "healthy", "message": "MongoDB 连接正常"}
    except Exception as exc:  # noqa: BLE001 - 健康检查需兜底所有异常
        return {"status": "error", "message": f"MongoDB 不可用: {exc}"}


async def _check_redis() -> dict:
    """探测 Redis 连通性。

    未启用 Redis 时返回 not_configured（不阻断就绪），
    已启用但连通失败时返回 error（阻断就绪）。
    """
    if redis_service.redis_conn is None:
        return {"status": "not_configured", "message": "Redis 未启用"}
    try:
        await asyncio.to_thread(redis_service.redis_conn.ping)
        return {"status": "healthy", "message": "Redis 连接正常"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"Redis 不可用: {exc}"}


async def _build_health_payload() -> dict:
    """构建健康检查载荷。"""
    registry = get_infrastructure_registry()
    infrastructure = await registry.health_check()
    return {
        "status": infrastructure.get("overall_status", "UNKNOWN").lower(),
        "message": "Service is running",
        "dispatch_mode": "rabbitmq",
        "warnings": [],
        "components": dict(infrastructure.get("components", {})),
        "timestamp": infrastructure.get("timestamp"),
    }


async def _build_readiness_payload() -> tuple[dict, bool]:
    """构建就绪检查载荷，并返回服务是否就绪。

    关键依赖判定：
    - MongoDB 必须健康，否则服务无法处理任何业务请求。
    - Redis 仅在已启用（global_redis_conn 非空）时必须健康；未启用视为降级而非阻断。
    - RabbitMQ / Kafka / 调度器仅反映能力可用性，不阻断整体就绪。
    """
    mongo = await _check_mongodb()
    redis = await _check_redis()
    infrastructure = await get_infrastructure_registry().health_check()
    infra_components = infrastructure.get("components", {})

    components = {
        _COMPONENT_MONGODB: mongo,
        _COMPONENT_REDIS: redis,
        "rabbitmq": infra_components.get("rabbitmq", {"status": "unknown"}),
        "kafka": infra_components.get("kafka", {"status": "unknown"}),
        "execution_scheduler": infra_components.get("execution_scheduler", {"status": "unknown"}),
    }

    critical_unhealthy = (
        mongo["status"] != "healthy"
        or redis["status"] not in ("healthy", "not_configured")
    )
    ready = not critical_unhealthy

    payload = {
        "status": "ready" if ready else "not_ready",
        "message": (
            "Service is ready to accept requests"
            if ready
            else "Service is not ready: critical dependency unavailable"
        ),
        "components": components,
        "timestamp": infrastructure.get("timestamp"),
    }
    return payload, ready


@router.get("", summary="健康检查")
async def health_check():
    """检查服务是否正常运行"""
    return APIResponse(data=await _build_health_payload())


@router.get("/ready", summary="就绪检查")
async def readiness_check(response: Response):
    """检查服务是否准备好接收请求（真实依赖探测）。"""
    payload, ready = await _build_readiness_payload()
    if not ready:
        # 真实返回 503，供 Kubernetes/网关判定 Pod 是否可接流
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return APIResponse(data=payload)


@router.get("/live", summary="存活检查")
def liveness_check():
    """检查服务是否存活"""
    return APIResponse(data={"status": "alive", "message": "Service is alive"})
