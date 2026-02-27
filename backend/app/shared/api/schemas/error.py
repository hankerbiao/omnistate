"""通用错误响应模型"""
from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
