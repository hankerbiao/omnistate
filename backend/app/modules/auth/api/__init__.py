"""RBAC API 路由

AI 友好注释说明：
- 这里导出 router，供 app/shared/api/main.py 挂载。
- 不包含业务逻辑，仅作模块入口。
"""
from .routes import router

from app.shared.api.router_registry import register_router

register_router(router, prefix="/api/v1", tags=["Auth"])

__all__ = ["router"]
