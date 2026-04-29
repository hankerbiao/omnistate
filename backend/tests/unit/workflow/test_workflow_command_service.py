from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.workflow.application import (  # noqa: E402
    DeleteWorkItemCommand,
    OperationContext,
    TransitionWorkItemCommand,
    WorkflowCommandService,
)


class _FakeMutationService:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.transition_calls: list[tuple[str, str, str, dict, list[str]]] = []

    async def handle_transition(
        self,
        work_item_id: str,
        action: str,
        operator_id: str,
        form_data: dict,
        actor_role_ids: list[str],
    ) -> dict:
        self.transition_calls.append((work_item_id, action, operator_id, form_data, actor_role_ids))
        return {
            "work_item_id": work_item_id,
            "to_state": "DONE",
            "work_item": {
                "id": work_item_id,
                "type_code": "TEST_CASE",
                "current_state": "DONE",
            },
        }

    async def delete_item(
        self,
        item_id: str,
        operator_id: str,
        actor_role_ids: list[str],
    ) -> bool:
        self.deleted.append(item_id)
        return True


class _FakeQueryService:
    async def get_item_by_id(self, item_id: str) -> dict:
        return {
            "id": item_id,
            "type_code": "REQUIREMENT",
            "current_state": "DRAFT",
        }


class _FakeHook:
    def __init__(self) -> None:
        self.transition_results: list[dict] = []
        self.before_delete_items: list[dict] = []
        self.after_delete_items: list[dict] = []

    async def after_transition(self, result: dict) -> None:
        self.transition_results.append(result)

    async def before_delete(self, work_item: dict) -> None:
        self.before_delete_items.append(work_item)

    async def after_delete(self, work_item: dict) -> None:
        self.after_delete_items.append(work_item)


def test_transition_work_item_runs_post_transition_hooks() -> None:
    mutation_service = _FakeMutationService()
    hook = _FakeHook()
    command_service = WorkflowCommandService(
        mutation_service=mutation_service,
        query_service=_FakeQueryService(),
        mutation_hooks=[hook],
    )
    context = OperationContext(actor_id="u-1", role_ids=["ROLE_QA"])

    result = asyncio.run(
        command_service.transition_work_item(
            context,
            TransitionWorkItemCommand(
                work_item_id="wi-1",
                action="submit",
                form_data={"title": "demo"},
            ),
        )
    )

    assert result["to_state"] == "DONE"
    assert hook.transition_results == [result]


def test_delete_work_item_runs_delete_hooks_around_workflow_delete() -> None:
    mutation_service = _FakeMutationService()
    hook = _FakeHook()
    command_service = WorkflowCommandService(
        mutation_service=mutation_service,
        query_service=_FakeQueryService(),
        mutation_hooks=[hook],
    )
    context = OperationContext(actor_id="u-1", role_ids=["ROLE_QA"])

    deleted = asyncio.run(
        command_service.delete_work_item(
            context,
            DeleteWorkItemCommand(work_item_id="wi-2"),
        )
    )

    assert deleted is True
    assert mutation_service.deleted == ["wi-2"]
    assert hook.before_delete_items == [
        {"id": "wi-2", "type_code": "REQUIREMENT", "current_state": "DRAFT"}
    ]
    assert hook.after_delete_items == [
        {"id": "wi-2", "type_code": "REQUIREMENT", "current_state": "DRAFT"}
    ]
