"""执行计划模块异常处理工具。

统一将领域异常转为 HTTPException，避免每个路由 handler 重复 try/except。
"""
from __future__ import annotations

from fastapi import HTTPException

from app.modules.execution_plan.domain.exceptions import (
    ExecutionPlanError,
    ItemNotFoundError,
    PlanNotFoundError,
    ResultNotFoundError,
)
from app.shared.core.logger import log as logger


def handle_service_error(exc: Exception) -> None:
    """统一处理领域异常为 HTTP 错误，无返回值（总是 raise）。"""
    if isinstance(exc, (PlanNotFoundError, ItemNotFoundError, ResultNotFoundError)):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ExecutionPlanError):
        raise HTTPException(status_code=400, detail=str(exc))
    logger.error(f"执行计划未处理异常: {exc}", exc_info=True)
    raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}")
