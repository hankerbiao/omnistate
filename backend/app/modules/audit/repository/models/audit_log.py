"""操作审计日志文档模型。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel


class AuditLogDoc(Document):
    """操作审计日志。

    每条记录代表一次用户写操作（POST/PUT/PATCH/DELETE），
    存储到 MongoDB audit_logs 集合，90 天后自动过期。
    """

    # ── 操作者信息 ──
    actor_id: Indexed(str) = Field(..., description="操作者用户 ID")
    actor_type: str = Field(default="human", description="操作者类型: human/ai")
    username: str = Field(default="", description="操作者用户名")
    role_ids: list[str] = Field(default_factory=list, description="操作者角色列表")
    client_ip: str = Field(default="", description="客户端 IP")

    # ── 请求信息 ──
    request_id: str = Field(default="-", description="请求 ID（关联 TraceContext）")
    method: str = Field(..., description="HTTP 方法")
    path: str = Field(..., description="请求路径")
    query_params: dict[str, Any] = Field(default_factory=dict, description="查询参数")

    # ── 业务信息 ──
    action: str = Field(default="", description="操作类型: create/update/delete/dispatch/...")
    resource_type: str = Field(default="unknown", description="资源类型")
    resource_id: Optional[str] = Field(default=None, description="资源 ID")

    # ── 请求/响应 ──
    request_body: Optional[dict[str, Any]] = Field(default=None, description="请求体（敏感字段已脱敏）")
    status_code: int = Field(default=0, description="HTTP 响应状态码")
    response_summary: Optional[dict[str, Any]] = Field(default=None, description="响应摘要")

    # ── 元信息 ──
    duration_ms: int = Field(default=0, description="耗时（毫秒）")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "audit_logs"
        indexes = [
            IndexModel("actor_id"),
            IndexModel("resource_type"),
            IndexModel("action"),
            IndexModel([("actor_id", 1), ("created_at", -1)]),
            IndexModel([("resource_type", 1), ("resource_id", 1)]),
            IndexModel(
                "created_at",
                expireAfterSeconds=90 * 24 * 60 * 60,  # 90 天 TTL
            ),
        ]
