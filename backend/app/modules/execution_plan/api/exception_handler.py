"""执行计划模块 FastAPI 异常处理器。

注册在 router 上，统一将领域异常转为 HTTP 响应，
避免每个 handler 重复 try/except。"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.modules.execution_plan.domain.exceptions import (
    ExecutionPlanError,
    ItemNotFoundError,
    PlanNotFoundError,
    ResultNotFoundError,
)
from app.shared.core.logger import log as logger


async def _execution_plan_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """统一处理执行计划领域异常。"""
    status_code = 400
    detail = str(exc)

    if isinstance(exc, (PlanNotFoundError, ItemNotFoundError, ResultNotFoundError)):
        status_code = 404
    elif isinstance(exc, (ValueError, ExecutionPlanError)):
        status_code = 400
    elif isinstance(exc, HTTPException):
        raise  # 让 FastAPI 默认处理器处理
    else:
        logger.error(f"执行计划未处理异常: {exc}", exc_info=True)
        detail = f"{type(exc).__name__}: {exc}"

    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": detail, "data": None} as Dict[str, Any],
    )


def register_exception_handlers(router: Any) -> None:
    """在 router 上注册异常处理器。"""
    router.exception_handler(Exception)(_execution_plan_exception_handler)
