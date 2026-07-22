"""共享路由"""
from .health import router as health_router
from .metrics import router as metrics_router
from .redis import router as redis_router

__all__ = ["health_router", "metrics_router", "redis_router"]
