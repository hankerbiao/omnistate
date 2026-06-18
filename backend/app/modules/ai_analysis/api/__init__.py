from app.modules.ai_analysis.api.routes import router

from app.shared.api.router_registry import register_router

register_router(router, prefix="/api/v1", tags=["AIAnalysis"])
