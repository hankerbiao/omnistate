"""API 路由自动注册表。

消除 app/shared/api/main.py 的手动路由导入和注册，
改为各模块在 api/__init__.py 中自动注册。
"""

from __future__ import annotations

import importlib
from typing import List, Tuple

from fastapi import APIRouter


# 全局路由注册表
_api_routers: List[Tuple[APIRouter, str, List[str]]] = []

# 所有需要注册 API 路由的模块路径
_API_MODULE_PATHS = [
    "app.modules.workflow.api",
    "app.modules.test_specs.api",
    "app.modules.execution.api",
    "app.modules.auth.api",
    "app.modules.attachments.api",
    "app.modules.search.api",
    "app.modules.execution_plan.api",
    "app.modules.test_case_collection.api",
    "app.modules.system_config.api",
    "app.modules.ai_analysis.api",
    "app.shared.redis.api",
    "app.modules.failure_analysis.api",
    "app.modules.project.api",
]


def _ensure_all_modules_imported() -> None:
    """确保所有模块的 api/__init__.py 被导入，触发 register_router()。"""
    for module_path in _API_MODULE_PATHS:
        try:
            importlib.import_module(module_path)
        except ImportError as e:
            import logging
            logging.warning(f"Failed to import {module_path}: {e}")


def register_router(
    router: APIRouter,
    prefix: str = "/api/v1",
    tags: List[str] | None = None,
) -> None:
    """模块调用此函数注册路由，替代手动在 main.py 中 include_router。"""
    _api_routers.append((router, prefix, tags or []))


def get_registered_routers() -> List[Tuple[APIRouter, str, List[str]]]:
    """返回所有已注册的路由列表。"""
    _ensure_all_modules_imported()
    return list(_api_routers)
