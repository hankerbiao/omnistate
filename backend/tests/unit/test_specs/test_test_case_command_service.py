import asyncio

import pytest

from app.modules.test_specs.application import (
    AssignTestCaseOwnersCommand,
    CreateTestCaseCommand,
    DeleteTestCaseCommand,
    LinkAutomationCaseCommand,
    MoveTestCaseToRequirementCommand,
    TestCaseCommandService,
    UpdateTestCaseCommand,
)
from app.modules.workflow.domain.exceptions import PermissionDeniedError
from app.modules.workflow.application import OperationContext


def test_create_test_case_command_service_defaults_owner_to_actor():
    captured = {}

    class FakeTestCaseService:
        async def create_test_case(self, payload):
            captured["payload"] = payload
            return payload

    class FakeRequirementService:
        pass

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            raise AssertionError("delete path should not be used")

    service = TestCaseCommandService(FakeTestCaseService(), FakeRequirementService(), FakeWorkflowCommandService())

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

    class FakeRequirementService:
        pass

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            raise AssertionError("delete path should not be used")

    service = TestCaseCommandService(FakeTestCaseService(), FakeRequirementService(), FakeWorkflowCommandService())

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

    class FakeRequirementService:
        pass

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            captured["actor_id"] = context.actor_id
            captured["work_item_id"] = command.work_item_id
            return True

    service = TestCaseCommandService(FakeTestCaseService(), FakeRequirementService(), FakeWorkflowCommandService())

    asyncio.run(
        service.delete_test_case(
            OperationContext(actor_id="admin", role_ids=["ROLE_ADMIN"]),
            DeleteTestCaseCommand(case_id="TC-1"),
        )
    )

    assert captured["case_id"] == "TC-1"
    assert captured["actor_id"] == "admin"
    assert captured["work_item_id"] == "workflow-1"


def test_assign_test_case_owners_command_service_validates_command():
    class FakeTestCaseService:
        async def get_test_case(self, case_id):
            raise AssertionError("service should not be called when command is invalid")

    class FakeRequirementService:
        pass

    class FakeWorkflowCommandService:
        pass

    service = TestCaseCommandService(FakeTestCaseService(), FakeRequirementService(), FakeWorkflowCommandService())

    with pytest.raises(ValueError, match="at least one owner must be specified"):
        asyncio.run(
            service.assign_owners(
                OperationContext(actor_id="user-1"),
                AssignTestCaseOwnersCommand(case_id="TC-1"),
            )
        )


def test_move_test_case_command_service_rejects_same_requirement():
    class FakeTestCaseService:
        async def get_test_case(self, case_id):
            return {"case_id": case_id, "ref_req_id": "REQ-1", "owner_id": "user-1", "workflow_item_id": None}

        async def move_to_requirement(self, case_id, target_req_id):
            raise AssertionError("move should not run when target requirement is unchanged")

    class FakeRequirementService:
        async def get_requirement(self, req_id):
            return {"req_id": req_id}

    class FakeWorkflowCommandService:
        pass

    service = TestCaseCommandService(FakeTestCaseService(), FakeRequirementService(), FakeWorkflowCommandService())

    with pytest.raises(ValueError, match="already linked to the target requirement"):
        asyncio.run(
            service.move_to_requirement(
                OperationContext(actor_id="user-1"),
                MoveTestCaseToRequirementCommand(case_id="TC-1", target_req_id="REQ-1"),
            )
        )


def test_link_automation_case_requires_object_permission():
    class FakeTestCaseService:
        async def get_test_case(self, case_id):
            return {"case_id": case_id, "owner_id": "owner-1", "workflow_item_id": None}

        async def link_automation_case(self, case_id, auto_case_id, version=None):
            raise AssertionError("link should not run without permission")

    class FakeRequirementService:
        pass

    class FakeWorkflowCommandService:
        pass

    service = TestCaseCommandService(FakeTestCaseService(), FakeRequirementService(), FakeWorkflowCommandService())

    with pytest.raises(PermissionDeniedError):
        asyncio.run(
            service.link_automation_case(
                OperationContext(actor_id="user-2", role_ids=["ROLE_USER"]),
                LinkAutomationCaseCommand(case_id="TC-1", auto_case_id="AUTO-1"),
            )
        )
