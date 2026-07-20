"""计划项自动化结果应用测试。"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.execution_plan.application.plan_command_service import PlanCommandService
from app.modules.execution_plan.domain.constants import PlanItemStatus, ResultSource


class _FakeField:
    def __init__(self, name: str) -> None:
        self._name = name

    def __eq__(self, other):
        return _FakeExpr(self._name, other)

    def __bool__(self) -> bool:
        return False


class _FakeExpr:
    def __init__(self, field: str, value) -> None:
        self._field = field
        self._value = value


class _Awaitable:
    def __init__(self, value) -> None:
        self._value = value

    def __await__(self):
        return self._await_impl().__await__()

    async def _await_impl(self):
        return self._value


class _FakeItemDoc:
    store: dict[str, "_FakeItemDoc"] = {}
    execution_task_id = _FakeField("execution_task_id")
    is_deleted = _FakeField("is_deleted")

    def __init__(self, **payload) -> None:
        for key, value in payload.items():
            setattr(self, key, value)
        self.store[self.item_id] = self

    def save(self):
        self.store[self.item_id] = self
        return _Awaitable(self)

    @classmethod
    def reset(cls) -> None:
        cls.store = {}

    @classmethod
    def find_one(cls, *args, **kwargs):
        async def _coro():
            docs = [doc for doc in cls.store.values() if not getattr(doc, "is_deleted", False)]
            for expr in args:
                if hasattr(expr, "_field"):
                    docs = [doc for doc in docs if getattr(doc, expr._field, None) == expr._value]
            return docs[0] if docs else None

        return _coro()


@pytest.fixture(autouse=True)
def reset_items():
    _FakeItemDoc.reset()
    yield
    _FakeItemDoc.reset()


@pytest.fixture
def command_service():
    plan_service = AsyncMock()

    async def _item_to_response(item):
        return {"item_id": item.item_id, "status": item.status}

    plan_service.item_to_response.side_effect = _item_to_response
    plan_service.refresh_plan_status = AsyncMock()
    return PlanCommandService(
        plan_service=plan_service,
        dispatch_port=AsyncMock(),
        notification_port=AsyncMock(),
    )


def _auto_item(status: str, task_id: str = "task-1") -> _FakeItemDoc:
    return _FakeItemDoc(
        item_id="EPI-1",
        plan_id="EP-1",
        ref_type="auto",
        status=status,
        execution_task_id=task_id,
        is_deleted=False,
    )


async def test_apply_passed_result_marks_auto_item_done(command_service) -> None:
    item = _auto_item(PlanItemStatus.RUNNING.value, "task-pass")

    with patch("app.modules.execution_plan.application.plan_command_service.ExecutionPlanItemDoc", _FakeItemDoc):
        result = await command_service.apply_execution_result("task-pass", "PASSED")

    assert result == {"item_id": item.item_id, "status": PlanItemStatus.DONE.value}
    assert item.status == PlanItemStatus.DONE.value
    assert item.result_source == ResultSource.AUTO.value
    command_service._plan_service.refresh_plan_status.assert_awaited_once_with("EP-1")


async def test_apply_failed_result_marks_auto_item_failed(command_service) -> None:
    item = _auto_item(PlanItemStatus.RUNNING.value, "task-fail")

    with patch("app.modules.execution_plan.application.plan_command_service.ExecutionPlanItemDoc", _FakeItemDoc):
        result = await command_service.apply_execution_result("task-fail", "FAILED")

    assert result == {"item_id": item.item_id, "status": PlanItemStatus.FAIL.value}
    assert item.status == PlanItemStatus.FAIL.value
    assert item.result_source == ResultSource.AUTO.value


async def test_apply_same_final_status_is_idempotent(command_service) -> None:
    _auto_item(PlanItemStatus.DONE.value, "task-done")

    with patch("app.modules.execution_plan.application.plan_command_service.ExecutionPlanItemDoc", _FakeItemDoc):
        result = await command_service.apply_execution_result("task-done", "PASSED")

    assert result == {"item_id": "EPI-1", "status": PlanItemStatus.DONE.value}
    command_service._plan_service.refresh_plan_status.assert_not_called()


async def test_apply_conflicting_final_status_does_not_override(command_service) -> None:
    item = _auto_item(PlanItemStatus.DONE.value, "task-conflict")

    with patch("app.modules.execution_plan.application.plan_command_service.ExecutionPlanItemDoc", _FakeItemDoc):
        result = await command_service.apply_execution_result("task-conflict", "FAILED")

    assert result == {"item_id": item.item_id, "status": PlanItemStatus.DONE.value}
    assert item.status == PlanItemStatus.DONE.value


async def test_apply_non_final_status_keeps_running(command_service) -> None:
    item = _auto_item(PlanItemStatus.RUNNING.value, "task-running")

    with patch("app.modules.execution_plan.application.plan_command_service.ExecutionPlanItemDoc", _FakeItemDoc):
        result = await command_service.apply_execution_result("task-running", "RUNNING")

    assert result == {"item_id": item.item_id, "status": PlanItemStatus.RUNNING.value}
    assert item.status == PlanItemStatus.RUNNING.value


async def test_apply_missing_bound_item_returns_none(command_service) -> None:
    with patch("app.modules.execution_plan.application.plan_command_service.ExecutionPlanItemDoc", _FakeItemDoc):
        result = await command_service.apply_execution_result("missing-task", "PASSED")

    assert result is None
