"""
API 路由汇总入口

按照功能模块组织路由，便于维护和扩展
"""
from fastapi import APIRouter

from app.api.routes.work_items import router as work_items_router
from app.api.routes.health import router as health_router

api_router = APIRouter()

# 健康检查路由
api_router.include_router(health_router, prefix="/health", tags=["Health"])

# 业务路由
api_router.include_router(work_items_router, prefix="/api/v1", tags=["WorkItems"])

