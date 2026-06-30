"""审计日志模块 API 注册。"""
from __future__ import annotations

from app.modules.audit.api.routes import router
from app.shared.api.router_registry import register_router

register_router(router, prefix="/api/v1", tags=["Audit Logs"])
