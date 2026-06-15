"""Redis 模块 API 路由。"""

from typing import Any

from fastapi import APIRouter, Depends

from app.modules.redis.schemas.redis import KeyValueResponse, PingResponse, PublishRequest
from app.modules.redis.service import build_key, publish_event, redis_conn, redis_read
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter(prefix="/api/v1/redis", tags=["Redis"])


@router.get("/ping", response_model=APIResponse[PingResponse])
async def ping(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Redis 连接健康检查。"""
    import time

    start = time.perf_counter()
    redis_conn.ping()
    elapsed = (time.perf_counter() - start) * 1000
    return APIResponse(data=PingResponse(status="ok", latency_ms=round(elapsed, 2)))


@router.get("/get", response_model=APIResponse[KeyValueResponse])
async def get_value(
    domain: str,
    entity: str,
    key_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """读取 Redis Key 的值。"""
    key = build_key(domain, entity, key_id)
    value = redis_read.get(key)
    ttl = redis_read.ttl(key)
    return APIResponse(data=KeyValueResponse(key=key, value=value, ttl=ttl))


@router.post("/set")
async def set_value(
    domain: str,
    entity: str,
    key_id: str,
    value: str,
    ex: int | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """写入 Redis Key。"""
    key = build_key(domain, entity, key_id)
    redis_conn.set(key, value, ex=ex)
    return APIResponse(data={"key": key})


@router.delete("/del")
async def delete_key(
    domain: str,
    entity: str,
    key_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """删除 Redis Key。"""
    key = build_key(domain, entity, key_id)
    redis_conn.delete(key)
    return APIResponse(data={"key": key, "deleted": True})


@router.post("/publish")
async def publish(
    request: PublishRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """非阻塞发布消息到 Redis 频道。"""
    publish_event(request.message, request.channel)
    return APIResponse(data={"channel": request.channel})
