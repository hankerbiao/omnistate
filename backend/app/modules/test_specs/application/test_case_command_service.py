from copy import deepcopy

from app.modules.test_specs.application.commands import (
    CreateTestCaseCommand,
    DeleteTestCaseCommand,
    LinkAutomationCaseCommand,
    UnlinkAutomationCaseCommand,
    UpdateTestCaseCommand,
)
from app.modules.test_specs.domain.policies import can_delete_test_case, can_update_test_case
from app.modules.test_specs.service import TestCaseService
from app.modules.workflow.application import DeleteWorkItemCommand, OperationContext, WorkflowCommandService
from app.modules.workflow.domain.exceptions import PermissionDeniedError


class TestCaseCommandService:
    __test__ = False

    def __init__(
        self,
        test_case_service: TestCaseService,
        workflow_command_service: WorkflowCommandService,
    ):
        self._test_case_service = test_case_service
        self._workflow_command_service = workflow_command_service

    async def create_test_case(
        self,
        context: OperationContext,
        command: CreateTestCaseCommand,
    ) -> dict:
        payload = deepcopy(command.payload)
        owner_id = str(payload.get("owner_id") or "").strip()
        if not owner_id:
            payload["owner_id"] = context.actor_id
        return await self._test_case_service.create_test_case(payload)

    async def update_test_case(
        self,
        context: OperationContext,
        command: UpdateTestCaseCommand,
    ) -> dict:
        if not command.payload:
            raise ValueError("no fields to update")

        test_case = await self._test_case_service.get_test_case(command.case_id)
        if not test_case:
            from app.modules.test_specs.domain.exceptions import TestCaseNotFoundError
            raise TestCaseNotFoundError(command.case_id)

        workflow_item_id = str(test_case.get("workflow_item_id") or "").strip()
        work_item = None
        if workflow_item_id:
            from app.modules.workflow.service.workflow_service import AsyncWorkflowService
            workflow_service = AsyncWorkflowService()
            work_item = await workflow_service.get_item(workflow_item_id)

        actor = {"actor_id": context.actor_id, "role_ids": context.role_ids}
        if not can_update_test_case(actor, test_case, work_item):
            raise PermissionDeniedError(context.actor_id, "update test case")

        return await self._test_case_service.update_test_case(command.case_id, command.payload)

    async def delete_test_case(
        self,
        context: OperationContext,
        command: DeleteTestCaseCommand,
    ) -> None:
        test_case = await self._test_case_service.get_test_case(command.case_id)
        if not test_case:
            from app.modules.test_specs.domain.exceptions import TestCaseNotFoundError
            raise TestCaseNotFoundError(command.case_id)

        workflow_item_id = str(test_case.get("workflow_item_id") or "").strip()
        work_item = None
        if workflow_item_id:
            from app.modules.workflow.service.workflow_service import AsyncWorkflowService
            workflow_service = AsyncWorkflowService()
            work_item = await workflow_service.get_item(workflow_item_id)

        actor = {"actor_id": context.actor_id, "role_ids": context.role_ids}
        if not can_delete_test_case(actor, test_case, work_item):
            raise PermissionDeniedError(context.actor_id, "delete test case")

        if workflow_item_id:
            await self._workflow_command_service.delete_work_item(
                context,
                DeleteWorkItemCommand(work_item_id=workflow_item_id),
            )
            return
        await self._test_case_service.delete_test_case(command.case_id)

    async def link_automation_case(
        self,
        context: OperationContext,
        command: LinkAutomationCaseCommand,
    ) -> dict:
        del context
        return await self._test_case_service.link_automation_case(
            case_id=command.case_id,
            auto_case_id=command.auto_case_id,
            version=command.version,
        )

    async def unlink_automation_case(
        self,
        context: OperationContext,
        command: UnlinkAutomationCaseCommand,
    ) -> dict:
        del context
        return await self._test_case_service.unlink_automation_case(case_id=command.case_id)
