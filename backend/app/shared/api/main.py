"""
API 路由汇总入口

使用 RouterRegistry 自动收集各模块注册的路由。
"""
from fastapi import APIRouter

from app.shared.api.router_registry import get_registered_routers
from app.shared.enums import router as enums_router

api_router = APIRouter()

# 从注册表加载所有模块注册的路由
for router, prefix, tags in get_registered_routers():
    api_router.include_router(router, prefix=prefix, tags=tags)

# 枚举路由单独注册
api_router.include_router(enums_router, prefix="/api/v1", tags=["Enums"])
