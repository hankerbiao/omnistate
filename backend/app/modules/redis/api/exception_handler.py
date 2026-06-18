"""Redis 模块异常处理器。"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.modules.redis.service.exceptions import RedisConnectionError, RedisOperationError
from app.shared.api.schemas.base import APIResponse


async def redis_connection_error_handler(request: Request, exc: RedisConnectionError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=APIResponse(code=1, message=str(exc), data=None).model_dump(),
    )


async def redis_operation_error_handler(request: Request, exc: RedisOperationError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=APIResponse(code=1, message=str(exc), data=None).model_dump(),
    )


EXCEPTION_HANDLERS = {
    RedisConnectionError: redis_connection_error_handler,
    RedisOperationError: redis_operation_error_handler,
}
