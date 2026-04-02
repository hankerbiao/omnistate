from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.service._service_support import (  # noqa: E402
    apply_workflow_status_projection,
    create_with_workflow_transaction,
    ensure_safe_generic_update,
    load_workflow_states_for_entities,
    workflow_aware_soft_delete,
)


class _FakeDoc:
    inserted_payloads: list[dict] = []
    req_id = object()

    def __init__(self, **payload):
        self.payload = dict(payload)
        self.id = "doc-1"
        self.is_deleted = False
        self.save_calls = 0
        for key, value in payload.items():
            setattr(self, key, value)

    async def insert(self, session=None) -> None:
        self.__class__.inserted_payloads.append(dict(self.payload))

    async def save(self) -> None:
        self.save_calls += 1

    def model_dump(self) -> dict:
        return dict(self.payload)

    @classmethod
    def find_one(cls, *args, **kwargs):
        class _Awaitable:
            def __await__(self_inner):
                async def _coro():
                    return None

                return _coro().__await__()

        return _Awaitable()


class _FakeWorkflowGateway:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create_work_item(self, **kwargs):
        self.calls.append(dict(kwargs))
        return {"id": "wi-1"}


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def start_transaction(self):
        return self


class _FakeClient:
    def start_session(self) -> _FakeSession:
        return _FakeSession()


class _FakeQuery:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self):
        return list(self._docs)


class _FakeDocCollection:
    @staticmethod
    def find(*args, **kwargs):
        return _FakeQuery([_FakeDoc(req_id="REQ-1"), _FakeDoc(req_id="REQ-2")])


def test_apply_workflow_status_projection_adds_status_from_state_map() -> None:
    docs = [_FakeDoc(req_id="REQ-1"), _FakeDoc(req_id="REQ-2")]

    result = asyncio.run(
        apply_workflow_status_projection(
            docs=docs,
            id_getter=lambda doc: doc.payload["req_id"],
            to_dict=lambda doc: {"req_id": doc.payload["req_id"]},
            workflow_states={"REQ-1": "IN_REVIEW"},
        )
    )

    assert result == [
        {"req_id": "REQ-1", "status": "IN_REVIEW"},
        {"req_id": "REQ-2", "status": "未开始"},
    ]


def test_load_workflow_states_for_entities_reads_docs_and_delegates(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.test_specs.service._service_support.get_workflow_states",
        lambda docs, id_field: _async_value({doc.payload[id_field]: "IN_REVIEW" for doc in docs}),
    )

    result = asyncio.run(
        load_workflow_states_for_entities(
            doc_cls=_FakeDocCollection,
            ids=["REQ-1", "REQ-2"],
            id_field="req_id",
        )
    )

    assert result == {"REQ-1": "IN_REVIEW", "REQ-2": "IN_REVIEW"}


def test_ensure_safe_generic_update_rejects_high_risk_fields() -> None:
    with pytest.raises(ValueError, match="Use explicit commands instead"):
        ensure_safe_generic_update(
            data={"owner_id": "u-1"},
            high_risk_fields={"owner_id", "status"},
            allowed_fields={"title"},
        )


def test_workflow_aware_soft_delete_rejects_bound_workflow_and_marks_deleted() -> None:
    bound_doc = _FakeDoc(req_id="REQ-1", workflow_item_id="wi-1")
    with pytest.raises(ValueError, match="workflow-aware"):
        asyncio.run(
            workflow_aware_soft_delete(
                doc=bound_doc,
                workflow_item_id=getattr(bound_doc, "workflow_item_id", None),
                workflow_error_message="delete through workflow-aware path only",
            )
        )

    free_doc = _FakeDoc(req_id="REQ-2")
    asyncio.run(
        workflow_aware_soft_delete(
            doc=free_doc,
            workflow_item_id=getattr(free_doc, "workflow_item_id", None),
            workflow_error_message="delete through workflow-aware path only",
        )
    )
    assert free_doc.is_deleted is True
    assert free_doc.save_calls == 1


def test_create_with_workflow_transaction_inserts_doc_with_workflow_item_id() -> None:
    _FakeDoc.inserted_payloads = []
    workflow_gateway = _FakeWorkflowGateway()

    result = asyncio.run(
        create_with_workflow_transaction(
            client=_FakeClient(),
            payload={"req_id": "REQ-1", "title": "Requirement", "owner_id": "u-1"},
            doc_cls=_FakeDoc,
            unique_lookup=lambda payload: _FakeDoc.req_id == payload["req_id"],
            duplicate_error_message="req_id already exists",
            workflow_gateway=workflow_gateway,
            workflow_item_factory=lambda payload: {
                "type_code": "REQUIREMENT",
                "title": payload["title"],
                "content": payload["title"],
                "creator_id": payload["owner_id"],
                "parent_item_id": None,
            },
            enrich_result=lambda doc: {"id": str(doc.id), **doc.model_dump()},
        )
    )

    assert workflow_gateway.calls[0]["type_code"] == "REQUIREMENT"
    assert _FakeDoc.inserted_payloads[0]["workflow_item_id"] == "wi-1"
    assert result["workflow_item_id"] == "wi-1"


async def _async_value(value):
    return value
