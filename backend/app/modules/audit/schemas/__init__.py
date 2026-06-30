"""审计日志 Schema 定义。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditLogItem(BaseModel):
    """单条审计日志。"""
    id: str = Field(..., description="记录 ID")
    actor_id: str
    username: str
    role_ids: list[str] = []
    client_ip: str
    request_id: str
    method: str
    path: str
    query_params: dict[str, Any] = {}
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    request_body: Optional[dict[str, Any]] = None
    status_code: int
    response_summary: Optional[dict[str, Any]] = None
    duration_ms: int
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """审计日志分页列表。"""
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


class AuditLogStatsResponse(BaseModel):
    """审计日志统计。"""
    total: int = 0
    by_action: dict[str, int] = {}
    by_resource_type: dict[str, int] = {}
    top_actors: list[dict[str, Any]] = []
