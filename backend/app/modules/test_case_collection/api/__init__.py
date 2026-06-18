"""用例集合 API 路由导出。"""
from .routes import router as collection_router

from app.shared.api.router_registry import register_router

register_router(collection_router, prefix="/api/v1", tags=["TestCaseCollection"])

__all__ = ["collection_router"]
