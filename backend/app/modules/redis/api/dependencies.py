"""Redis 模块 API 依赖注入。"""

from typing import Annotated, Any

from fastapi import Depends


async def get_redis_service() -> Any:
    """获取 Redis 服务（注入点预留）。"""
    from app.modules.redis.service import redis_conn

    return redis_conn


RedisServiceDep = Annotated[Any, Depends(get_redis_service)]
