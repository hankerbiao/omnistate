"""
API 路由汇总入口

按照功能模块组织路由，便于维护和扩展
"""
from fastapi import APIRouter

from app.modules.workflow.api import router as workflow_router
from app.modules.test_specs.api import (
    automation_test_case_router,
    catalog_router,
    comment_router,
    requirement_router,
    test_case_router,
)
from app.modules.execution.api import execution_router
from app.modules.auth.api import router as auth_router
from app.modules.attachments.api import router as attachments_router
from app.modules.search.api import search_router
from app.modules.execution_plan.api import router as execution_plan_router
from app.modules.test_case_collection.api import collection_router
from app.modules.system_config.api import router as system_config_router, ai_router as ai_tools_router
from app.modules.ai_analysis.api import router as ai_analysis_router
from app.modules.redis.api import router as redis_router
from app.shared.enums import router as enums_router
api_router = APIRouter()

# 业务路由
api_router.include_router(workflow_router, prefix="/api/v1", tags=["WorkItems"])
api_router.include_router(requirement_router, prefix="/api/v1", tags=["Requirements"])
api_router.include_router(catalog_router, prefix="/api/v1", tags=["Catalog"])
api_router.include_router(test_case_router, prefix="/api/v1", tags=["TestCases"])
api_router.include_router(comment_router, prefix="/api/v1", tags=["TestCases"])
api_router.include_router(automation_test_case_router, prefix="/api/v1", tags=["AutomationTestCases"])
api_router.include_router(execution_router, prefix="/api/v1", tags=["Execution"])
api_router.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
api_router.include_router(attachments_router, prefix="/api/v1", tags=["Attachments"])
api_router.include_router(search_router, prefix="/api/v1", tags=["Search"])
api_router.include_router(execution_plan_router, prefix="/api/v1", tags=["ExecutionPlans"])
api_router.include_router(collection_router, prefix="/api/v1", tags=["TestCaseCollection"])
api_router.include_router(system_config_router, prefix="/api/v1", tags=["SystemConfig"])
api_router.include_router(ai_tools_router, prefix="/api/v1", tags=["AITools"])
api_router.include_router(ai_analysis_router, prefix="/api/v1", tags=["AIAnalysis"])
api_router.include_router(redis_router, prefix="/api/v1", tags=["Redis"])
api_router.include_router(enums_router, prefix="/api/v1", tags=["Enums"])
