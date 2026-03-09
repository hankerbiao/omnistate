import asyncio

import pytest

from app.modules.test_specs.application import (
    CreateRequirementCommand,
    DeleteRequirementCommand,
    RequirementCommandService,
    UpdateRequirementCommand,
)
from app.modules.workflow.application import OperationContext


def test_create_requirement_command_service_defaults_owner_to_actor():
    captured = {}

    class FakeRequirementService:
        async def create_requirement(self, payload):
            captured["payload"] = payload
            return payload

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            raise AssertionError("delete path should not be used")

    service = RequirementCommandService(FakeRequirementService(), FakeWorkflowCommandService())

    result = asyncio.run(
        service.create_requirement(
            OperationContext(actor_id="user-1"),
            CreateRequirementCommand(payload={"title": "Requirement A"}),
        )
    )

    assert captured["payload"]["tpm_owner_id"] == "user-1"
    assert result["tpm_owner_id"] == "user-1"


def test_update_requirement_command_service_rejects_empty_payload():
    class FakeRequirementService:
        async def update_requirement(self, req_id, payload):
            raise AssertionError("update should not run")

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            raise AssertionError("delete path should not be used")

    service = RequirementCommandService(FakeRequirementService(), FakeWorkflowCommandService())

    with pytest.raises(ValueError, match="no fields to update"):
        asyncio.run(
            service.update_requirement(
                OperationContext(actor_id="user-1"),
                UpdateRequirementCommand(req_id="REQ-1", payload={}),
            )
        )


def test_delete_requirement_command_service_routes_linked_delete_to_workflow():
    captured = {}

    class FakeRequirementService:
        async def get_requirement(self, req_id):
            captured["req_id"] = req_id
            return {"req_id": req_id, "workflow_item_id": "workflow-1"}

        async def delete_requirement(self, req_id):
            raise AssertionError("direct delete should not be used for linked records")

    class FakeWorkflowCommandService:
        async def delete_work_item(self, context, command):
            captured["actor_id"] = context.actor_id
            captured["work_item_id"] = command.work_item_id
            return True

    service = RequirementCommandService(FakeRequirementService(), FakeWorkflowCommandService())

    asyncio.run(
        service.delete_requirement(
            OperationContext(actor_id="admin", role_ids=["ROLE_ADMIN"]),
            DeleteRequirementCommand(req_id="REQ-1"),
        )
    )

    assert captured["req_id"] == "REQ-1"
    assert captured["actor_id"] == "admin"
    assert captured["work_item_id"] == "workflow-1"
