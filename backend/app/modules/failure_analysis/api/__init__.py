from .routes import router as failure_analysis_router

from app.shared.api.router_registry import register_router

register_router(failure_analysis_router, prefix="/api/v1", tags=["FailureAnalysis"])

__all__ = ["failure_analysis_router"]
