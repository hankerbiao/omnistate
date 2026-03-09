import asyncio

import pytest

from app.modules.test_specs.service.requirement_service import RequirementService
from app.modules.test_specs.service.test_case_service import TestCaseService


def test_requirement_delete_requires_workflow_aware_path(monkeypatch):
    service = RequirementService()

    class FakeRequirementDoc:
        workflow_item_id = "507f1f77bcf86cd799439011"

    class FakeRequirementCollection:
        req_id = object()

        @staticmethod
        async def find_one(*args, **kwargs):
            return FakeRequirementDoc()

    monkeypatch.setattr(
        "app.modules.test_specs.service.requirement_service.TestRequirementDoc",
        FakeRequirementCollection,
    )

    with pytest.raises(ValueError, match="workflow-aware path"):
        asyncio.run(service.delete_requirement("REQ-1"))


def test_test_case_delete_requires_workflow_aware_path(monkeypatch):
    service = TestCaseService()

    class FakeTestCaseDoc:
        workflow_item_id = "507f1f77bcf86cd799439011"

    class FakeTestCaseCollection:
        case_id = object()

        @staticmethod
        async def find_one(*args, **kwargs):
            return FakeTestCaseDoc()

    monkeypatch.setattr(
        "app.modules.test_specs.service.test_case_service.TestCaseDoc",
        FakeTestCaseCollection,
    )

    with pytest.raises(ValueError, match="workflow-aware path"):
        asyncio.run(service.delete_test_case("TC-1"))
