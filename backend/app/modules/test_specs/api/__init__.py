"""定义层 API 路由"""
from .automation_test_case_routes import router as automation_test_case_router
from .catalog_routes import router as catalog_router
from .comment_routes import router as comment_router
from .test_required_routes import router as requirement_router
from .test_case_routes import router as test_case_router

from app.shared.api.router_registry import register_router

register_router(requirement_router, prefix="/api/v1", tags=["Requirements"])
register_router(catalog_router, prefix="/api/v1", tags=["Catalog"])
register_router(test_case_router, prefix="/api/v1", tags=["TestCases"])
register_router(comment_router, prefix="/api/v1", tags=["TestCases"])
register_router(automation_test_case_router, prefix="/api/v1", tags=["AutomationTestCases"])

__all__ = [
    "automation_test_case_router",
    "catalog_router",
    "comment_router",
    "requirement_router",
    "test_case_router",
]
