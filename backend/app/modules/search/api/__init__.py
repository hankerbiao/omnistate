"""搜索 API 路由导出。"""

from .routes import router as search_router

from app.shared.api.router_registry import register_router

register_router(search_router, prefix="/api/v1", tags=["Search"])

__all__ = ["search_router"]
