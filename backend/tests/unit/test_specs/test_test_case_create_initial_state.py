from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.service.test_case_service import TestCaseService  # noqa: E402
from app.modules.workflow.repository.models.enums import WorkItemState  # noqa: E402


class _FakeWorkflowGateway:
    def __init__(self) -> None:
        self.last_create_kwargs: dict | None = None

    async def create_work_item(self, **kwargs):
        self.last_create_kwargs = dict(kwargs)
        return {"id": "wi-tc-1", "current_state": kwargs.get("initial_state", "DRAFT")}

    async def get_work_item_by_id(self, item_id: str) -> dict | None:
        return None


class _FakeTestCaseDoc:
    inserted_payloads: list[dict] = []
    case_id = object()

    def __init__(self, **payload):
        self.payload = dict(payload)
        self.id = "doc-tc-1"

    async def insert(self, session=None) -> None:
        self.__class__.inserted_payloads.append(dict(self.payload))

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


async def _async_value(value):
    return value


@pytest.mark.asyncio
async def test_create_test_case_workflow_starts_in_developing(monkeypatch) -> None:
    _FakeTestCaseDoc.inserted_payloads = []
    gateway = _FakeWorkflowGateway()
    service = TestCaseService(workflow_gateway=gateway)

    monkeypatch.setattr(
        "app.modules.test_specs.service.test_case_service.TestCaseDoc",
        _FakeTestCaseDoc,
    )
    monkeypatch.setattr(
        "app.modules.test_specs.service.test_case_service.TestCaseService._ensure_requirement_exists",
        staticmethod(lambda req_id, session=None: _async_value(SimpleNamespace(workflow_item_id="req-wi-1"))),
    )
    monkeypatch.setattr(
        "app.modules.test_specs.service.test_case_service.TestCaseService._validate_and_enrich_attachments",
        lambda self, attachments, session=None: _async_value(attachments),
    )
    monkeypatch.setattr(
        "app.modules.test_specs.service.test_case_service.TestCaseService._enrich_test_case_status",
        lambda self, data: _async_value({**data, "status": WorkItemState.DEVELOPING.value}),
    )
    monkeypatch.setattr(
        "app.modules.test_specs.service.test_case_service.CatalogService.register_path",
        lambda self, lab_id, catalog_path, delta=1: _async_value(None),
    )
    monkeypatch.setattr(
        "app.modules.test_specs.service.test_case_service.CatalogService.prepare_catalog_fields",
        lambda self, lab_id, catalog_path: _async_value(
            {
                "lab_id": lab_id,
                "catalog_path": ["misc"],
                "catalog_path_key": "misc",
            }
        ),
    )

    await service._create_test_case_with_transaction(
        _FakeClient(),
        {
            "case_id": "TC-2026-00099",
            "ref_req_id": "TR-2026-00001",
            "lab_id": "LAB-DEFAULT",
            "catalog_path": ["misc"],
            "title": "new case",
            "owner_id": "admin-1",
            "attachments": [],
        },
    )

    assert gateway.last_create_kwargs is not None
    assert gateway.last_create_kwargs["initial_state"] == WorkItemState.DEVELOPING.value
    assert gateway.last_create_kwargs["creator_id"] == "admin-1"
