from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from app.modules.workflow.application.common import docs_to_dicts


class _FakeDoc:
    def __init__(self, *, id: str, type_code: str, req_id: str | None = None) -> None:
        self.id = id
        self.type_code = type_code
        self.req_id = req_id
        self.parent_item_id = None
        self.current_state = "DRAFT"
        self.current_owner_id = "owner-1"
        self.creator_id = "creator-1"

    def model_dump(self) -> dict:
        return {
            "type_code": self.type_code,
            "title": f"title-{self.id}",
            "content": "content",
            "parent_item_id": self.parent_item_id,
            "current_state": self.current_state,
            "current_owner_id": self.current_owner_id,
            "creator_id": self.creator_id,
            "req_id": self.req_id,
            "is_deleted": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }


class _FakeQuery:
    def __init__(self, docs: list[SimpleNamespace]) -> None:
        self._docs = docs

    async def to_list(self) -> list[SimpleNamespace]:
        return self._docs


class _FakeRequirementDoc:
    queries: list[dict] = []

    @classmethod
    def find(cls, query: dict) -> _FakeQuery:
        cls.queries.append(query)
        return _FakeQuery([
            SimpleNamespace(workflow_item_id="req-workflow-1", req_id="TR-001"),
        ])


class _FakeTestCaseDoc:
    queries: list[dict] = []

    @classmethod
    def find(cls, query: dict) -> _FakeQuery:
        cls.queries.append(query)
        return _FakeQuery([
            SimpleNamespace(workflow_item_id="case-workflow-1", case_id="TC-001"),
        ])


def test_docs_to_dicts_loads_business_ids_in_batches(monkeypatch) -> None:
    _FakeRequirementDoc.queries = []
    _FakeTestCaseDoc.queries = []
    docs = [
        _FakeDoc(id="req-workflow-1", type_code="REQUIREMENT"),
        _FakeDoc(id="req-workflow-2", type_code="REQUIREMENT", req_id="TR-002"),
        _FakeDoc(id="case-workflow-1", type_code="TEST_CASE"),
        _FakeDoc(id="case-workflow-2", type_code="TEST_CASE"),
    ]

    monkeypatch.setattr(
        "app.modules.workflow.application.common._get_test_requirement_doc",
        lambda: _FakeRequirementDoc,
    )
    monkeypatch.setattr(
        "app.modules.workflow.application.common._get_test_case_doc",
        lambda: _FakeTestCaseDoc,
    )

    result = asyncio.run(docs_to_dicts(docs))

    assert [item.get("req_id") for item in result[:2]] == ["TR-001", "TR-002"]
    assert [item.get("case_id") for item in result[2:]] == ["TC-001", None]
    assert len(_FakeRequirementDoc.queries) == 1
    assert _FakeRequirementDoc.queries[0]["workflow_item_id"]["$in"] == ["req-workflow-1"]
    assert len(_FakeTestCaseDoc.queries) == 1
    assert _FakeTestCaseDoc.queries[0]["workflow_item_id"]["$in"] == [
        "case-workflow-1",
        "case-workflow-2",
    ]
