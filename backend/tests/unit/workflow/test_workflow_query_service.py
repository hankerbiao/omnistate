from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.workflow.application.query_service import WorkflowQueryService  # noqa: E402


class _FakeConfigQuery:
    def __init__(self, configs: list[SimpleNamespace]) -> None:
        self._configs = configs

    async def to_list(self) -> list[SimpleNamespace]:
        return self._configs


class _FakeWorkflowConfigDoc:
    type_code = object()
    from_state = object()

    configs: list[SimpleNamespace] = []

    @classmethod
    def find(cls, *args) -> _FakeConfigQuery:
        return _FakeConfigQuery(cls.configs)


def test_get_item_with_transitions_filters_by_actor_role(monkeypatch) -> None:
    service = WorkflowQueryService()

    async def fake_get_item_by_id(item_id: str) -> dict:
        return {
            "id": item_id,
            "type_code": "REQUIREMENT",
            "current_state": "DRAFT",
            "creator_id": "creator-1",
            "current_owner_id": "owner-1",
        }

    configs = [
        SimpleNamespace(
            action="SUBMIT",
            to_state="PENDING_REVIEW",
            target_owner_strategy="TO_SPECIFIC_USER",
            required_fields=["target_owner_id", "priority"],
            properties={"allowed_role_ids": ["TPM"]},
        ),
        SimpleNamespace(
            action="QA_ONLY",
            to_state="PENDING_TEST",
            target_owner_strategy="KEEP",
            required_fields=[],
            properties={"allowed_role_ids": ["QA"]},
        ),
    ]

    monkeypatch.setattr(service, "get_item_by_id", fake_get_item_by_id)
    _FakeWorkflowConfigDoc.configs = configs
    monkeypatch.setattr(
        "app.modules.workflow.application.query_service.SysWorkflowConfigDoc",
        _FakeWorkflowConfigDoc,
    )

    result = asyncio.run(
        service.get_item_with_transitions(
            "wi-1",
            actor={"actor_id": "tpm-1", "role_ids": ["ROLE_TPM"]},
        )
    )

    assert [transition["action"] for transition in result["available_transitions"]] == ["SUBMIT"]
