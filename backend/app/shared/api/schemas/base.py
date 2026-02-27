"""
通用响应 Envelope

统一 API 响应格式：
{
  "code": 0,
  "message": "ok",
  "data": {}
}
"""
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """标准化 API 响应封装"""
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None
