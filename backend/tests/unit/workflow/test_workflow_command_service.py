import asyncio

from app.modules.workflow.application import (
    CreateWorkItemCommand,
    DeleteWorkItemCommand,
    OperationContext,
    ReassignWorkItemCommand,
    TransitionWorkItemCommand,
    WorkflowCommandService,
)


def test_workflow_command_service_uses_operation_context():
    captured = {}

    class FakeWorkflowService:
        async def create_item(self, **kwargs):
            captured["create"] = kwargs
            return {"item_id": "w1"}

        async def handle_transition(self, **kwargs):
            captured["transition"] = kwargs
            return {"work_item_id": "w1"}

        async def reassign_item(self, **kwargs):
            captured["reassign"] = kwargs
            return {"item_id": "w1"}

        async def delete_item(self, **kwargs):
            captured["delete"] = kwargs
            return True

    context = OperationContext(actor_id="user-1", role_ids=["ROLE_ADMIN"])
    service = WorkflowCommandService(FakeWorkflowService())

    asyncio.run(
        service.create_work_item(
            context,
            CreateWorkItemCommand(
                type_code="REQ",
                title="Title",
                content="Content",
                parent_item_id="parent-1",
            ),
        )
    )
    asyncio.run(
        service.transition_work_item(
            context,
            TransitionWorkItemCommand(
                work_item_id="w1",
                action="SUBMIT",
                form_data={"comment": "ok"},
            ),
        )
    )
    asyncio.run(
        service.reassign_work_item(
            context,
            ReassignWorkItemCommand(
                work_item_id="w1",
                target_owner_id="owner-2",
                remark="handoff",
            ),
        )
    )
    asyncio.run(service.delete_work_item(context, DeleteWorkItemCommand(work_item_id="w1")))

    assert captured["create"]["creator_id"] == "user-1"
    assert captured["transition"]["operator_id"] == "user-1"
    assert captured["transition"]["actor_role_ids"] == ["ROLE_ADMIN"]
    assert captured["reassign"]["operator_id"] == "user-1"
    assert captured["delete"]["operator_id"] == "user-1"
