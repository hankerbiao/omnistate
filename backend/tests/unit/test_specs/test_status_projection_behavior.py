from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.application.workflow_projection_hook import (  # noqa: E402
    TestSpecsWorkflowProjectionHook,
)
from app.modules.test_specs.service.requirement_service import RequirementService as _RequirementService  # noqa: E402
from app.modules.test_specs.service.test_case_service import TestCaseService as _TestCaseService  # noqa: E402


class _FakeWorkflowGateway:
    async def create_work_item(
        self,
        type_code: str,
        title: str,
        content: str,
        creator_id: str,
        parent_item_id: str | None = None,
        session=None,
    ) -> dict[str, str]:
        return {
            "id": f"{type_code.lower()}-wi-1",
            "current_state": "IN_REVIEW",
        }

    async def get_work_item_by_id(self, item_id: str) -> dict[str, str] | None:
        return {"id": item_id, "current_state": "IN_REVIEW"}


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


class _FakeRequirementDoc:
    inserted_payloads: list[dict] = []
    req_id = object()

    def __init__(self, **payload):
        self.payload = dict(payload)
        self.id = "req-doc-1"

    async def insert(self, session=None) -> None:
        self.__class__.inserted_payloads.append(dict(self.payload))

    def model_dump(self) -> dict:
        return dict(self.payload)

    @classmethod
    def find_one(cls, *args, **kwargs):
        class _Query:
            def __await__(self_inner):
                async def _coro():
                    return None

                return _coro().__await__()

        return _Query()


class _FakeTestCaseDoc:
    inserted_payloads: list[dict] = []
    case_id = object()

    def __init__(self, **payload):
        self.payload = dict(payload)
        self.id = "case-doc-1"

    async def insert(self, session=None) -> None:
        self.__class__.inserted_payloads.append(dict(self.payload))

    def model_dump(self) -> dict:
        return dict(self.payload)

    @classmethod
    def find_one(cls, *args, **kwargs):
        class _Query:
            def __await__(self_inner):
                async def _coro():
                    return None

                return _coro().__await__()

        return _Query()


class _FakeProjectionDoc:
    def __init__(self) -> None:
        self.is_deleted = False
        self.save_calls = 0

    async def save(self) -> None:
        self.save_calls += 1


def test_create_requirement_does_not_persist_status_but_returns_workflow_status(monkeypatch) -> None:
    _FakeRequirementDoc.inserted_payloads = []
    service = _RequirementService(workflow_gateway=_FakeWorkflowGateway())

    monkeypatch.setattr(
        "app.modules.test_specs.service.requirement_service.TestRequirementDoc",
        _FakeRequirementDoc,
    )
    monkeypatch.setattr(
        "app.modules.test_specs.service.requirement_service.RequirementService._generate_req_id",
        lambda self: _async_value("TR-2026-00001"),
    )
    monkeypatch.setattr(
        "app.modules.test_specs.service.requirement_service.RequirementService._enrich_requirement_status",
        lambda self, data: _async_value({**data, "status": "IN_REVIEW"}),
    )

    result = asyncio.run(
        service._create_requirement_with_transaction(
            _FakeClient(),
            {
                "req_id": "TR-2026-00001",
                "title": "req",
                "description": "desc",
                "tpm_owner_id": "u-1",
            },
        )
    )

    assert "status" not in _FakeRequirementDoc.inserted_payloads[0]
    assert result["status"] == "IN_REVIEW"


def test_create_test_case_does_not_persist_status_but_returns_workflow_status(monkeypatch) -> None:
    _FakeTestCaseDoc.inserted_payloads = []
    service = _TestCaseService(workflow_gateway=_FakeWorkflowGateway())

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
        lambda self, data: _async_value({**data, "status": "IN_REVIEW"}),
    )

    result = asyncio.run(
        service._create_test_case_with_transaction(
            _FakeClient(),
            {
                "case_id": "TC-2026-00001",
                "ref_req_id": "TR-2026-00001",
                "title": "case",
                "owner_id": "u-2",
                "attachments": [],
            },
        )
    )

    assert "status" not in _FakeTestCaseDoc.inserted_payloads[0]
    assert result["status"] == "IN_REVIEW"


def test_projection_hook_no_longer_exposes_transition_side_effect_hook() -> None:
    hook = TestSpecsWorkflowProjectionHook()

    assert not hasattr(hook, "after_transition")


async def _async_value(value):
    return value
