"""
全局异常处理器

统一处理各类异常，返回格式化的错误响应
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..schemas.workflow import ErrorResponse
from app.services import (
    WorkflowError,
    WorkItemNotFoundError,
    PermissionDeniedError
)

from app.core.logger import log


async def workflow_exception_handler(request: Request, exc: WorkflowError):
    """业务逻辑异常处理器"""
    status_code = status.HTTP_400_BAD_REQUEST
    
    if isinstance(exc, WorkItemNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, PermissionDeniedError):
        status_code = status.HTTP_403_FORBIDDEN
    
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            detail=str(exc)
        ).model_dump()
    )


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
    """通用异常处理器，隐藏内部错误细节"""
    # 记录详细的错误日志以便后端排查
    log.exception(f"Unhandled system error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            detail="An internal error occurred. Please contact the administrator."
        ).model_dump()
    )


def setup_exception_handlers(app):
    """配置全局异常处理器"""

    # 注册异常处理器
    app.add_exception_handler(WorkflowError, workflow_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

