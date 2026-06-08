"""测试用例评论 Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateCommentRequest(BaseModel):
    """创建评论请求"""
    content: str = Field(..., min_length=1, max_length=2000, description="评论内容")


class UpdateCommentRequest(BaseModel):
    """更新评论请求"""
    content: str = Field(..., min_length=1, max_length=2000, description="评论内容")


class CommentResponse(BaseModel):
    """评论响应"""
    comment_id: str = Field(..., alias="_id")
    case_id: str
    content: str
    author_id: str
    author_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class CommentListResponse(BaseModel):
    """评论列表响应"""
    items: list[CommentResponse]
    total: int
