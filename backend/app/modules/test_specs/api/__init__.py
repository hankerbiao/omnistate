"""定义层 API 路由"""
from .automation_test_case_routes import router as automation_test_case_router
from .test_required_routes import router as requirement_router
from .test_case_routes import router as test_case_router

__all__ = ["automation_test_case_router", "requirement_router", "test_case_router"]
