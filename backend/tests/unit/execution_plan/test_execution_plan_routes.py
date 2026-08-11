"""execution_plan API 路由辅助逻辑单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.execution_plan.api.routes import _resolve_assignee_id  # noqa: E402


def test_resolve_assignee_defaults_to_current_user() -> None:
    current_user = {"user_id": "user-1", "role_ids": []}

    assert _resolve_assignee_id(current_user, None) == "user-1"


def test_resolve_assignee_allows_current_user() -> None:
    current_user = {"user_id": "user-1", "role_ids": []}

    assert _resolve_assignee_id(current_user, "user-1") == "user-1"


def test_resolve_assignee_rejects_other_user_for_non_admin() -> None:
    current_user = {"user_id": "user-1", "role_ids": []}

    with pytest.raises(HTTPException) as exc_info:
        _resolve_assignee_id(current_user, "user-2")

    assert exc_info.value.status_code == 403


def test_resolve_assignee_allows_admin_to_query_other_user() -> None:
    current_user = {"user_id": "admin", "role_ids": ["ADMIN"]}

    assert _resolve_assignee_id(current_user, "user-2") == "user-2"


def test_execution_plan_route_surface_is_preserved() -> None:
    from app.modules.execution_plan.api.routes import router

    app = FastAPI()
    app.include_router(router)
    schema = app.openapi()
    operations = {
        (method.upper(), path)
        for path, path_item in schema["paths"].items()
        for method in path_item
    }

    assert operations == {
        ("GET", "/execution-plans/items/archived"),
        ("PUT", "/execution-plans/items/{item_id}/archive"),
        ("PUT", "/execution-plans/items/{item_id}/unarchive"),
        ("POST", "/execution-plans/items/{item_id}/dispatch"),
        ("POST", "/execution-plans/items/{item_id}/cancel-execution"),
        ("POST", "/execution-plans/items/{item_id}/rerun"),
        ("POST", "/execution-plans/items/batch-dispatch"),
        ("POST", "/execution-plans/items/{item_id}/result"),
        ("GET", "/execution-plans/items/{item_id}/result"),
        ("GET", "/execution-plans/cases/{case_id}/execution-stats"),
        ("GET", "/execution-plans/plans"),
        ("POST", "/execution-plans/plans"),
        ("GET", "/execution-plans/plans/{plan_id}"),
        ("PUT", "/execution-plans/plans/{plan_id}"),
        ("DELETE", "/execution-plans/plans/{plan_id}"),
        ("GET", "/execution-plans/items/my-items"),
        ("GET", "/execution-plans/items"),
        ("GET", "/execution-plans/items/overview"),
        ("GET", "/execution-plans/items/{item_id}"),
        ("PUT", "/execution-plans/plans/{plan_id}/items/{item_id}"),
        ("POST", "/execution-plans/items/{item_id}/reassign"),
        ("POST", "/execution-plans/plans/{plan_id}/items"),
        ("DELETE", "/execution-plans/plans/{plan_id}/items/{item_id}"),
        ("PUT", "/execution-plans/plans/{plan_id}/items/batch-assignee"),
    }


def test_static_archive_route_precedes_dynamic_item_route() -> None:
    from app.modules.execution_plan.api.routes import router

    app = FastAPI()
    app.include_router(router)
    paths = list(app.openapi()["paths"])

    assert paths.index("/execution-plans/items/archived") < paths.index(
        "/execution-plans/items/{item_id}"
    )
