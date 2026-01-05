"""
全局异常处理器

统一处理各类异常，返回格式化的错误响应
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.schemas.workflow import ErrorResponse


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"HTTP Error {exc.status_code}",
            detail=str(exc.detail) if exc.detail else None
        ).model_dump()
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc) if exc else "Unknown error occurred"
        ).model_dump()
    )


def setup_exception_handlers(app):
    """配置全局异常处理器"""

    # 注册异常处理器
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)