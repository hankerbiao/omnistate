"""Redis 模块 API 依赖注入。"""

from typing import Annotated, Any

from fastapi import Depends


async def get_redis_service() -> Any:
    """获取 Redis 服务（注入点预留）。"""
    import app.modules.redis.service as redis_service

    return redis_service.redis_conn


RedisServiceDep = Annotated[Any, Depends(get_redis_service)]
