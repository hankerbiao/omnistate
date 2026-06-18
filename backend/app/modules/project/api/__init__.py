from app.modules.project.api.routes import router

from app.shared.api.router_registry import register_router

register_router(router, prefix="/api/v1", tags=["Projects"])

__all__ = ["router"]
