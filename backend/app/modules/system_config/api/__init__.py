from app.modules.system_config.api.routes import router
from app.modules.system_config.api.ai_routes import router as ai_router
from app.shared.ai.embedding_routes import router as embedding_router

from app.shared.api.router_registry import register_router

register_router(router, prefix="/api/v1", tags=["SystemConfig"])
register_router(ai_router, prefix="/api/v1", tags=["AITools"])
register_router(embedding_router, prefix="/api/v1", tags=["AITools"])

__all__ = ["router", "ai_router", "embedding_router"]
