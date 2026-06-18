"""Redis 模块 API 路由。"""
from .routes import router

from app.shared.api.router_registry import register_router

register_router(router, prefix="/api/v1", tags=["Redis"])

__all__ = ["router"]
