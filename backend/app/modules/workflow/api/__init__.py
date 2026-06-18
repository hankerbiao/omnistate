"""工作流模块路由入口"""
from .routes import router

from app.shared.api.router_registry import register_router

register_router(router, prefix="/api/v1", tags=["WorkItems"])

__all__ = ["router"]
