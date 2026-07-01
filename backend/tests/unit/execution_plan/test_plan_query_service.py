"""PlanQueryService 单元测试。

测试策略：使用 AsyncMock 模拟 ExecutionPlanService，
验证 PlanQueryService 正确委托底层服务、不引入写操作。
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.execution_plan.application.plan_query_service import (  # noqa: E402
    PlanQueryService,
)


# ═══════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
def query_service(mock_service):
    return PlanQueryService(plan_service=mock_service)


# ═══════════════════════════════════════════════════════════════════════
#  Construction
# ═══════════════════════════════════════════════════════════════════════

def test_uses_provided_plan_service(query_service, mock_service):
    assert query_service._plan_service is mock_service


def test_default_construction_lazy_loads_service(monkeypatch):
    """无参构造时，底层服务延迟到方法调用时才创建。"""
    # Patch ExecutionPlanService in the module to verify lazy import
    svc = PlanQueryService.__new__(PlanQueryService)
    svc._plan_service = None
    assert svc._plan_service is None


# ═══════════════════════════════════════════════════════════════════════
#  list_plans
# ═══════════════════════════════════════════════════════════════════════

async def test_list_plans_delegates_to_plan_service(query_service, mock_service):
    mock_service.list_plans.return_value = [{"plan_id": "EP-1"}, {"plan_id": "EP-2"}]

    result = await query_service.list_plans(status="active")

    # list_plans 透传默认分页参数 page=1, page_size=20
    mock_service.list_plans.assert_awaited_once_with(status="active", page=1, page_size=20)
    assert result == [{"plan_id": "EP-1"}, {"plan_id": "EP-2"}]


async def test_list_plans_without_status(query_service, mock_service):
    mock_service.list_plans.return_value = []

    result = await query_service.list_plans()

    mock_service.list_plans.assert_awaited_once_with(status=None, page=1, page_size=20)
    assert result == []


# ═══════════════════════════════════════════════════════════════════════
#  get_plan
# ═══════════════════════════════════════════════════════════════════════

async def test_get_plan_returns_plan_dict(query_service, mock_service):
    mock_service.get_plan.return_value = {"plan_id": "EP-1", "title": "Sprint 1"}

    result = await query_service.get_plan("EP-1")

    mock_service.get_plan.assert_awaited_once_with("EP-1")
    assert result["plan_id"] == "EP-1"
    assert result["title"] == "Sprint 1"


# ═══════════════════════════════════════════════════════════════════════
#  get_item
# ═══════════════════════════════════════════════════════════════════════

async def test_get_item_returns_item_dict(query_service, mock_service):
    mock_service.get_item.return_value = {"item_id": "EPI-1", "status": "pending"}

    result = await query_service.get_item("EPI-1")

    mock_service.get_item.assert_awaited_once_with("EPI-1")
    assert result["item_id"] == "EPI-1"


# ═══════════════════════════════════════════════════════════════════════
#  list_my_items
# ═══════════════════════════════════════════════════════════════════════

async def test_list_my_items_for_assignee(query_service, mock_service):
    mock_service.list_my_items.return_value = [
        {"item_id": "EPI-1", "assignee_id": "user-1"},
    ]

    result = await query_service.list_my_items("user-1")

    # list_my_items 透传默认 limit=200
    mock_service.list_my_items.assert_awaited_once_with("user-1", limit=200)
    assert len(result) == 1
    assert result[0]["assignee_id"] == "user-1"


# ═══════════════════════════════════════════════════════════════════════
#  list_items
# ═══════════════════════════════════════════════════════════════════════

async def test_list_items_with_all_filters(query_service, mock_service):
    mock_service.list_items.return_value = [{"item_id": "EPI-1"}]

    result = await query_service.list_items(status="pending", plan_id="EP-1", limit=50)

    mock_service.list_items.assert_awaited_once_with(
        status="pending", plan_id="EP-1", limit=50,
    )
    assert len(result) == 1


async def test_list_items_default_limit(query_service, mock_service):
    mock_service.list_items.return_value = []

    await query_service.list_items()

    # 默认 limit=200
    _, kwargs = mock_service.list_items.call_args
    assert kwargs.get("limit") == 200


# ═══════════════════════════════════════════════════════════════════════
#  get_overview
# ═══════════════════════════════════════════════════════════════════════

async def test_get_overview_returns_summary(query_service, mock_service):
    mock_service.get_overview.return_value = {
        "total_plans": 10, "active_plans": 5, "completed_plans": 3,
    }

    result = await query_service.get_overview()

    mock_service.get_overview.assert_awaited_once()
    assert result["total_plans"] == 10
    assert result["active_plans"] == 5


# ═══════════════════════════════════════════════════════════════════════
#  list_archived_items
# ═══════════════════════════════════════════════════════════════════════

async def test_list_archived_items_for_assignee(query_service, mock_service):
    mock_service.list_archived_items.return_value = [
        {"item_id": "EPI-A1", "archived_at": "2026-01-01"},
    ]

    result = await query_service.list_archived_items("user-1")

    # list_archived_items 透传默认 limit=200
    mock_service.list_archived_items.assert_awaited_once_with("user-1", limit=200)
    assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════
#  get_result
# ═══════════════════════════════════════════════════════════════════════

async def test_get_result_returns_manual_result(query_service, mock_service):
    mock_service.get_result.return_value = {
        "result_id": "MER-1", "passed": True, "notes": "All pass",
    }

    result = await query_service.get_result("EPI-1")

    mock_service.get_result.assert_awaited_once_with("EPI-1")
    assert result["passed"] is True


# ═══════════════════════════════════════════════════════════════════════
#  get_case_execution_stats
# ═══════════════════════════════════════════════════════════════════════

async def test_get_case_execution_stats(query_service, mock_service):
    mock_service.get_case_execution_stats.return_value = {
        "case_id": "TC-1", "execution_count": 5, "pass_rate": 0.8,
    }

    result = await query_service.get_case_execution_stats("TC-1")

    mock_service.get_case_execution_stats.assert_awaited_once_with("TC-1")
    assert result["pass_rate"] == 0.8


# ═══════════════════════════════════════════════════════════════════════
#  Read-only invariant
# ═══════════════════════════════════════════════════════════════════════

def test_query_service_has_no_write_methods():
    """PlanQueryService 应当不暴露任何写操作方法。"""
    write_methods = {
        "create_plan", "update_plan", "delete_plan",
        "add_items", "delete_item", "update_item",
        "reassign_item", "batch_update_assignee",
        "submit_result", "dispatch_item", "cancel_execution",
        "rerun_item", "batch_dispatch",
        "archive_item", "unarchive_item",
    }
    query_methods = {m for m in dir(PlanQueryService) if not m.startswith("_")}
    leaked = write_methods & query_methods
    assert not leaked, f"QueryService 暴露了写方法: {leaked}"


def test_query_service_does_not_have_dispatch_port():
    """QueryService 不应持有 dispatch port（写操作专用）。"""
    svc = PlanQueryService.__new__(PlanQueryService)
    svc._plan_service = None
    assert not hasattr(svc, "_dispatch_port")
    assert not hasattr(svc, "_notification_port")
