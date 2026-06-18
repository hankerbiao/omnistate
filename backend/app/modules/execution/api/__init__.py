"""测试执行 API 路由。"""
from .routes import router as execution_router

from app.shared.api.router_registry import register_router

register_router(execution_router, prefix="/api/v1", tags=["Execution"])

__all__ = ["execution_router"]
