from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.test_specs.service.requirement_service import RequirementService
from app.modules.test_specs.service.test_case_service import TestCaseService as TestCaseAppService


class FakeField:
    def __eq__(self, other):
        return other


class FakeQuery:
    def __init__(self, docs):
        self._docs = docs

    def find(self, *args, **kwargs):
        return self

    def sort(self, *args, **kwargs):
        return self

    def skip(self, offset):
        self._docs = self._docs[offset:]
        return self

    def limit(self, limit):
        self._docs = self._docs[:limit]
        return self

    async def to_list(self):
        return list(self._docs)


@pytest.mark.asyncio
async def test_get_requirement_uses_workflow_status_projection():
    service = RequirementService()
    requirement_doc = SimpleNamespace(
        id="mongo-1",
        req_id="REQ-1",
        workflow_item_id="wf-1",
        status="旧状态",
        model_dump=lambda: {
            "req_id": "REQ-1",
            "workflow_item_id": "wf-1",
            "status": "旧状态",
        },
    )
    work_item = SimpleNamespace(current_state="进行中", is_deleted=False)

    with patch(
        "app.modules.test_specs.service.requirement_service.TestRequirementDoc.find_one",
        new=AsyncMock(return_value=requirement_doc),
    ), patch(
        "app.modules.test_specs.service.requirement_service.TestRequirementDoc.req_id",
        new=FakeField(),
        create=True,
    ), patch(
        "app.modules.test_specs.service.requirement_service.BusWorkItemDoc.get",
        new=AsyncMock(return_value=work_item),
    ):
        result = await service.get_requirement("REQ-1")

    assert result["status"] == "进行中"


@pytest.mark.asyncio
async def test_get_test_case_uses_workflow_status_projection():
    service = TestCaseAppService()
    test_case_doc = SimpleNamespace(
        id="mongo-1",
        case_id="TC-1",
        workflow_item_id="wf-1",
        status="draft",
        model_dump=lambda: {
            "case_id": "TC-1",
            "workflow_item_id": "wf-1",
            "status": "draft",
        },
    )
    work_item = SimpleNamespace(current_state="已评审", is_deleted=False)

    with patch(
        "app.modules.test_specs.service.test_case_service.TestCaseDoc.find_one",
        new=AsyncMock(return_value=test_case_doc),
    ), patch(
        "app.modules.test_specs.service.test_case_service.TestCaseDoc.case_id",
        new=FakeField(),
        create=True,
    ), patch(
        "app.modules.test_specs.service.test_case_service.BusWorkItemDoc.get",
        new=AsyncMock(return_value=work_item),
    ):
        result = await service.get_test_case("TC-1")

    assert result["status"] == "已评审"


@pytest.mark.asyncio
async def test_list_requirements_status_filter_applies_offset_once():
    service = RequirementService()
    docs = [
        SimpleNamespace(id=f"id-{idx}", req_id=f"REQ-{idx}", workflow_item_id=f"wf-{idx}", model_dump=lambda idx=idx: {
            "req_id": f"REQ-{idx}",
            "workflow_item_id": f"wf-{idx}",
            "status": "旧状态",
        })
        for idx in range(4)
    ]

    with patch(
        "app.modules.test_specs.service.requirement_service.TestRequirementDoc.find",
        return_value=FakeQuery(docs),
    ), patch.object(
        service,
        "_get_workflow_states_for_requirements",
        new=AsyncMock(return_value={f"REQ-{idx}": "进行中" for idx in range(4)}),
    ):
        result = await service.list_requirements(status="进行中", limit=1, offset=1)

    assert [item["req_id"] for item in result] == ["REQ-1"]


@pytest.mark.asyncio
async def test_list_test_cases_status_filter_applies_offset_once():
    service = TestCaseAppService()
    docs = [
        SimpleNamespace(id=f"id-{idx}", case_id=f"TC-{idx}", workflow_item_id=f"wf-{idx}", model_dump=lambda idx=idx: {
            "case_id": f"TC-{idx}",
            "workflow_item_id": f"wf-{idx}",
            "status": "draft",
        })
        for idx in range(4)
    ]

    with patch(
        "app.modules.test_specs.service.test_case_service.TestCaseDoc.find",
        return_value=FakeQuery(docs),
    ), patch.object(
        service,
        "_get_workflow_states_for_test_cases",
        new=AsyncMock(return_value={f"TC-{idx}": "进行中" for idx in range(4)}),
    ):
        result = await service.list_test_cases(status="进行中", limit=1, offset=1)

    assert [item["case_id"] for item in result] == ["TC-1"]
