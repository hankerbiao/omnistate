"""
API 路由汇总入口

按照功能模块组织路由，便于维护和扩展
"""
from fastapi import APIRouter

from app.modules.workflow.api import router as workflow_router
from app.modules.assets.api import router as assets_router
from app.modules.test_specs.api import requirement_router, test_case_router
from app.modules.auth.api import router as auth_router
from app.shared.api.routes import health_router

api_router = APIRouter()

# 健康检查路由
api_router.include_router(health_router, prefix="/health", tags=["Health"])

# 业务路由
api_router.include_router(workflow_router, prefix="/api/v1", tags=["WorkItems"])
api_router.include_router(assets_router, prefix="/api/v1", tags=["Assets"])
api_router.include_router(requirement_router, prefix="/api/v1", tags=["Requirements"])
api_router.include_router(test_case_router, prefix="/api/v1", tags=["TestCases"])
api_router.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
