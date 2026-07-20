"""execution_plan API 路由辅助逻辑单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

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
