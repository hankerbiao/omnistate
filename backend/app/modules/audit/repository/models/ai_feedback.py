"""AI 输出反馈文档模型。

记录用户对 AI 生成/评审/分析结果的反馈：
- accepted: 直接采纳
- rejected: 拒绝
- edited: 编辑后采纳

用于持续改进 AI 提示词质量和评估 AI 效果。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class AiFeedbackDoc(Document):
    """AI 输出反馈记录。"""

    # ── AI 调用标识 ──
    ai_endpoint: str = Field(..., description="AI 端点路径")
    request_id: str = Field(default="-", description="关联的请求 ID")
    actor_id: str = Field(default="-", description="操作者 ID")

    # ── 输入输出 ──
    input_summary: str = Field(default="", description="输入摘要")
    output_summary: str = Field(default="", description="输出摘要")

    # ── 用户反馈 ──
    feedback: str = Field(..., description="accepted / rejected / edited")
    edited_content: Optional[str] = Field(default=None, description="用户编辑后的内容（edited 时有值）")
    comment: str = Field(default="", description="用户评论/补充说明")

    # ── 评分 ──
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="用户评分 1-5")
    score: Optional[int] = Field(default=None, description="AI 原始评分（如果端点返回了评分）")

    # ── 元信息 ──
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "ai_feedback"
        indexes = [
            IndexModel("ai_endpoint"),
            IndexModel("feedback"),
            IndexModel([("ai_endpoint", 1), ("created_at", -1)]),
            IndexModel([("feedback", 1), ("created_at", -1)]),
        ]
