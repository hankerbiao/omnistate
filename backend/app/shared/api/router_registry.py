"""API 路由自动注册表。

消除 app/shared/api/main.py 的手动路由导入和注册，
改为各模块在 api/__init__.py 中自动注册。
"""

from __future__ import annotations

from typing import List, Tuple

from fastapi import APIRouter


# 全局路由注册表
_api_routers: List[Tuple[APIRouter, str, List[str]]] = []


def register_router(
    router: APIRouter,
    prefix: str = "/api/v1",
    tags: List[str] | None = None,
) -> None:
    """模块调用此函数注册路由，替代手动在 main.py 中 include_router。"""
    _api_routers.append((router, prefix, tags or []))


def get_registered_routers() -> List[Tuple[APIRouter, str, List[str]]]:
    """返回所有已注册的路由列表。"""
    return list(_api_routers)
