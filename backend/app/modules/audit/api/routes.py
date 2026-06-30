"""审计日志 API 路由。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.modules.audit.repository.models.ai_feedback import AiFeedbackDoc
from app.modules.audit.schemas import (
    AuditLogListResponse,
    AuditLogStatsResponse,
)
from app.modules.audit.service import AuditLogService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission
from app.shared.core.logger import log

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


# ═══════════════════════════════════════════════════════════════════════
#  AI 输出反馈
# ═══════════════════════════════════════════════════════════════════════

class SubmitAiFeedbackRequest(BaseModel):
    """AI 输出反馈请求。"""
    ai_endpoint: str = Field(..., description="AI 端点路径")
    request_id: str = Field(default="-", description="关联请求 ID")
    feedback: str = Field(..., description="accepted / rejected / edited")
    input_summary: str = Field(default="", description="输入摘要")
    output_summary: str = Field(default="", description="输出摘要")
    edited_content: Optional[str] = Field(default=None, description="用户编辑后的内容")
    comment: str = Field(default="", description="用户评论")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="评分 1-5")


@router.post(
    "/ai-feedback",
    response_model=APIResponse,
    summary="提交 AI 输出反馈",
)
async def submit_ai_feedback(
    data: SubmitAiFeedbackRequest,
    current_user=Depends(get_current_user),
):
    """记录用户对 AI 输出的反馈（采纳/拒绝/编辑后采纳）。

    用于持续改进 AI 提示词质量和评估 AI 效果。
    """
    if data.feedback not in ("accepted", "rejected", "edited"):
        raise HTTPException(status_code=400, detail="feedback 字段必须为 accepted/rejected/edited")

    doc = AiFeedbackDoc(
        ai_endpoint=data.ai_endpoint,
        request_id=data.request_id,
        actor_id=current_user.get("user_id", "-"),
        input_summary=data.input_summary,
        output_summary=data.output_summary,
        feedback=data.feedback,
        edited_content=data.edited_content,
        comment=data.comment,
        rating=data.rating,
    )
    await doc.insert()

    log.info(
        "AI feedback: endpoint={} feedback={} user={}",
        data.ai_endpoint, data.feedback, doc.actor_id,
    )
    return APIResponse(message="反馈已记录")


@router.get(
    "/ai-feedback",
    response_model=APIResponse,
    summary="查询 AI 输出反馈统计",
    dependencies=[Depends(require_permission("system:config"))],
)
async def list_ai_feedback(
    ai_endpoint: Optional[str] = Query(None),
    feedback: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """查询 AI 输出反馈记录，支持按端点和反馈类型筛选。"""
    query: dict[str, Any] = {}
    if ai_endpoint:
        query["ai_endpoint"] = ai_endpoint
    if feedback:
        query["feedback"] = feedback

    total = await AiFeedbackDoc.find(query).count()
    docs = await AiFeedbackDoc.find(query).sort("-created_at").limit(limit).to_list()

    items = [
        {
            "id": str(d.id),
            "ai_endpoint": d.ai_endpoint,
            "feedback": d.feedback,
            "rating": d.rating,
            "comment": d.comment,
            "created_at": d.created_at,
        }
        for d in docs
    ]

    # 统计
    pipeline = [
        {"$group": {"_id": "$feedback", "count": {"$sum": 1}}},
    ]
    stats_raw = await AiFeedbackDoc.aggregate(pipeline).to_list()
    stats: dict[str, int] = {r["_id"]: r["count"] for r in stats_raw if r["_id"]}

    return APIResponse(data={
        "items": items,
        "total": total,
        "stats": stats,
    })
