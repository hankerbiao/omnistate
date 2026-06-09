"""
全局异常处理器

统一收敛业务异常与 HTTP 异常，返回结构化的错误响应：
- 业务类错误：WorkflowError / TestSpecsError / ExecutionPlanError 体系
- AppError 体系（NotFoundError / ConflictError / ValidationError / PermissionDenied）
- HTTP 协议错误：StarletteHTTPException
- 未预料异常：统一映射为 InternalServerError，隐藏内部细节

异常日志自动附加追踪上下文（request_id, user_id）。
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.modules.workflow.domain import (
    PermissionDeniedError,
    WorkflowError,
    WorkItemNotFoundError,
)
from app.modules.test_specs.domain.exceptions import (
    TestSpecsError,
    RequirementNotFoundError,
    TestCaseNotFoundError,
    LabConflictError,
)
from app.modules.execution_plan.domain.exceptions import (
    ExecutionPlanError,
    PlanNotFoundError,
    ItemNotFoundError,
    ResultNotFoundError,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.api.schemas.error import ErrorResponse
from app.shared.context import get_operation_context, get_trace_context, reset_context
from app.shared.core.logger import log


async def _make_error_response(status_code: int, exc: Exception) -> JSONResponse:
    """构造统一的错误响应 JSON。"""
    return JSONResponse(
        status_code=status_code,
        content=APIResponse(
            code=status_code,
            message=exc.__class__.__name__,
            data=ErrorResponse(
                error=exc.__class__.__name__,
                detail=str(exc),
            ),
        ).model_dump(),
    )


async def workflow_exception_handler(request: Request, exc: WorkflowError):
    """Workflow 业务逻辑异常处理器"""
    status_code = status.HTTP_400_BAD_REQUEST

    if isinstance(exc, WorkItemNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, PermissionDeniedError):
        status_code = status.HTTP_403_FORBIDDEN

    return await _make_error_response(status_code, exc)


async def test_specs_exception_handler(request: Request, exc: TestSpecsError):
    """TestSpecs 业务逻辑异常处理器"""
    status_code = status.HTTP_400_BAD_REQUEST

    if isinstance(exc, (RequirementNotFoundError, TestCaseNotFoundError)):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, LabConflictError):
        status_code = status.HTTP_409_CONFLICT

    return await _make_error_response(status_code, exc)


async def execution_plan_exception_handler(request: Request, exc: ExecutionPlanError):
    """ExecutionPlan 业务逻辑异常处理器"""
    status_code = status.HTTP_400_BAD_REQUEST

    if isinstance(exc, (PlanNotFoundError, ItemNotFoundError, ResultNotFoundError)):
        status_code = status.HTTP_404_NOT_FOUND

    return await _make_error_response(status_code, exc)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            code=exc.status_code,
            message=f"HTTP Error {exc.status_code}",
            data=ErrorResponse(
                error=f"HTTP Error {exc.status_code}",
                detail=str(exc.detail) if exc.detail else None
            )
        ).model_dump()
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """通用异常处理器，隐藏内部错误细节"""
    try:
        ctx = get_trace_context()
        operation = get_operation_context()
        log.exception(
            "Unhandled system error: {error} | request_id={request_id} | user_id={user_id} | path={path}",
            error=exc,
            request_id=ctx.request_id,
            user_id=operation.actor_id,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="InternalServerError",
                data=ErrorResponse(
                    error="InternalServerError",
                    detail="An internal error occurred. Please contact the administrator."
                )
            ).model_dump()
        )
    finally:
        reset_context()


def setup_exception_handlers(app: FastAPI) -> None:
    """配置全局异常处理器"""

    app.add_exception_handler(WorkflowError, workflow_exception_handler)
    app.add_exception_handler(TestSpecsError, test_specs_exception_handler)
    app.add_exception_handler(ExecutionPlanError, execution_plan_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
