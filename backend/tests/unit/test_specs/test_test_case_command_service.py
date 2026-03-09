import asyncio

import pytest

from app.modules.test_specs.application import (
    CreateTestCaseCommand,
    DeleteTestCaseCommand,
    TestCaseCommandService,
    UpdateTestCaseCommand,
)
from app.modules.workflow.application import OperationContext


def test_create_test_case_command_service_defaults_owner_to_actor():
    captured = {}

    class FakeTestCaseService:
        async def create_test_case(self, payload):
            captured["payload"] = payload
            return payload

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            raise AssertionError("delete path should not be used")

    service = TestCaseCommandService(FakeTestCaseService(), FakeWorkflowCommandService())

    result = asyncio.run(
        service.create_test_case(
            OperationContext(actor_id="user-1"),
            CreateTestCaseCommand(payload={"title": "Case A", "ref_req_id": "REQ-1"}),
        )
    )

    assert captured["payload"]["owner_id"] == "user-1"
    assert result["owner_id"] == "user-1"


def test_update_test_case_command_service_rejects_empty_payload():
    class FakeTestCaseService:
        async def update_test_case(self, case_id, payload):
            raise AssertionError("update should not run")

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            raise AssertionError("delete path should not be used")

    service = TestCaseCommandService(FakeTestCaseService(), FakeWorkflowCommandService())

    with pytest.raises(ValueError, match="no fields to update"):
        asyncio.run(
            service.update_test_case(
                OperationContext(actor_id="user-1"),
                UpdateTestCaseCommand(case_id="TC-1", payload={}),
            )
        )


def test_delete_test_case_command_service_routes_linked_delete_to_workflow():
    captured = {}

    class FakeTestCaseService:
        async def get_test_case(self, case_id):
            captured["case_id"] = case_id
            return {"case_id": case_id, "workflow_item_id": "workflow-1"}

        async def delete_test_case(self, case_id):
            raise AssertionError("direct delete should not be used for linked records")

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            captured["actor_id"] = context.actor_id
            captured["work_item_id"] = command.work_item_id
            return True

    service = TestCaseCommandService(FakeTestCaseService(), FakeWorkflowCommandService())

    asyncio.run(
        service.delete_test_case(
            OperationContext(actor_id="user-1"),
            DeleteTestCaseCommand(case_id="TC-1"),
        )
    )

    assert captured["case_id"] == "TC-1"
    assert captured["actor_id"] == "user-1"
    assert captured["work_item_id"] == "workflow-1"
