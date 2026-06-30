"""审计日志 API 路由。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.modules.audit.schemas import (
    AuditLogListResponse,
    AuditLogStatsResponse,
)
from app.modules.audit.service import AuditLogService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "",
    response_model=APIResponse[AuditLogListResponse],
    summary="查询操作审计日志",
    dependencies=[Depends(require_permission("system:config"))],
)
async def list_audit_logs(
    actor_id: Optional[str] = Query(None, description="操作者 ID"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    resource_id: Optional[str] = Query(None, description="资源 ID"),
    action: Optional[str] = Query(None, description="操作类型"),
    method: Optional[str] = Query(None, description="HTTP 方法"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """分页查询操作审计日志，支持多维度筛选。"""
    data = await AuditLogService.list_logs(
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        method=method,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    return APIResponse(data=data)


@router.get(
    "/stats",
    response_model=APIResponse[AuditLogStatsResponse],
    summary="审计日志统计",
    dependencies=[Depends(require_permission("system:config"))],
)
async def get_audit_stats():
    """获取审计日志统计信息（总数、按操作/资源类型分组、Top 操作者）。"""
    data = await AuditLogService.get_stats()
    return APIResponse(data=data)
