from copy import deepcopy

from app.modules.test_specs.application._workflow_command_support import (
    delete_entity_or_work_item,
    ensure_authorized_entity,
    ensure_entity,
)
from app.modules.test_specs.application.commands import (
    AssignTestCaseOwnersCommand,
    LinkAutomationCaseCommand,
    MoveTestCaseToRequirementCommand,
    CreateTestCaseCommand,
    UpdateTestCaseCommand,
    DeleteTestCaseCommand,
)
from app.modules.test_specs.domain.exceptions import RequirementNotFoundError, TestCaseNotFoundError
from app.modules.test_specs.domain.policies import can_delete_test_case, can_update_test_case
from app.modules.test_specs.service import TestCaseChangeLogService, TestCaseService, RequirementService
from app.modules.workflow.application import OperationContext, WorkflowCommandService


class TestCaseCommandService:
    """
    测试用例命令服务类，负责处理测试用例的各种命令操作。

    该服务类封装了测试用例的创建、更新、删除以及与自动化测试用例的关联操作，
    并与工作流服务集成，确保操作符合权限策略和业务规则。
    """
    __test__ = False

    def __init__(
        self,
        test_case_service: TestCaseService,
        requirement_service: RequirementService,
        workflow_command_service: WorkflowCommandService,
        change_log_service: TestCaseChangeLogService | None = None,
    ):
        self._test_case_service = test_case_service
        self._requirement_service = requirement_service
        self._workflow_command_service = workflow_command_service
        self._change_log_service = change_log_service or TestCaseChangeLogService()

    async def _record_change(
        self,
        case_id: str,
        context: OperationContext,
        action: str,
        old_snapshot: dict | None,
        new_snapshot: dict,
        remark: str | None = None,
        extra_changes: list[dict] | None = None,
    ) -> None:
        old_for_diff = (
            await self._change_log_service.get_snapshot(old_snapshot)
            if old_snapshot is not None
            else None
        )
        new_for_diff = await self._change_log_service.get_snapshot(new_snapshot)
        await self._change_log_service.append(
            case_id=case_id,
            operator_id=context.actor_id,
            action=action,
            old_snapshot=old_for_diff,
            new_snapshot=new_for_diff,
            remark=remark,
            extra_changes=extra_changes,
        )

    async def create_test_case(
        self,
        context: OperationContext,
        command: CreateTestCaseCommand,
    ) -> dict:
        payload = deepcopy(command.payload)
        owner_id = str(payload.get("owner_id") or "").strip()
        if not owner_id:
            payload["owner_id"] = context.actor_id
        result = await self._test_case_service.create_test_case(payload)
        await self._record_change(
            case_id=result["case_id"],
            context=context,
            action="CREATE",
            old_snapshot=None,
            new_snapshot=await self._test_case_service.get_case_raw_dict(result["case_id"]),
            remark=payload.get("change_log"),
        )
        return result

    async def update_test_case(
        self,
        context: OperationContext,
        command: UpdateTestCaseCommand,
    ) -> dict:
        if not command.payload:
            raise ValueError("no fields to update")

        await ensure_authorized_entity(
            context=context,
            entity_id=command.case_id,
            getter=self._test_case_service.get_test_case,
            error_cls=TestCaseNotFoundError,
            checker=can_update_test_case,
            action="update test case",
            workflow_getter=self._workflow_command_service.get_work_item_by_id,
        )

        old_snapshot = await self._test_case_service.get_case_raw_dict(command.case_id)
        result = await self._test_case_service.update_test_case(command.case_id, command.payload)
        new_snapshot = await self._test_case_service.get_case_raw_dict(command.case_id)
        await self._record_change(
            case_id=command.case_id,
            context=context,
            action="UPDATE",
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            remark=command.payload.get("change_log"),
        )
        return result

    async def delete_test_case(
        self,
        context: OperationContext,
        command: DeleteTestCaseCommand,
    ) -> None:
        old_snapshot = await self._test_case_service.get_case_raw_dict(command.case_id)
        _test_case, workflow_item_id = await ensure_authorized_entity(
            context=context,
            entity_id=command.case_id,
            getter=self._test_case_service.get_test_case,
            error_cls=TestCaseNotFoundError,
            checker=can_delete_test_case,
            action="delete test case",
            workflow_getter=self._workflow_command_service.get_work_item_by_id,
        )

        async def _do_delete() -> None:
            await self._test_case_service.delete_test_case(command.case_id)
            deleted_snapshot = {**old_snapshot, "is_deleted": True}
            await self._record_change(
                case_id=command.case_id,
                context=context,
                action="DELETE",
                old_snapshot=old_snapshot,
                new_snapshot=deleted_snapshot,
            )

        await delete_entity_or_work_item(
            context,
            self._workflow_command_service,
            workflow_item_id,
            _do_delete,
        )

    async def link_automation_case(
        self,
        context: OperationContext,
        command: LinkAutomationCaseCommand,
    ) -> dict:
        await ensure_authorized_entity(
            context=context,
            entity_id=command.case_id,
            getter=self._test_case_service.get_test_case,
            error_cls=TestCaseNotFoundError,
            checker=can_update_test_case,
            action="link automation case",
            workflow_getter=self._workflow_command_service.get_work_item_by_id,
        )

        snapshot = await self._test_case_service.get_case_raw_dict(command.case_id)
        result = await self._test_case_service.link_automation_case(
            case_id=command.case_id,
            auto_case_id=command.auto_case_id,
            version=command.version,
        )
        extra = [{
            "field": "automation_link",
            "old_value": None,
            "new_value": {
                "auto_case_id": command.auto_case_id,
                "version": command.version,
            },
            "change_type": "added",
        }]
        await self._record_change(
            case_id=command.case_id,
            context=context,
            action="LINK_AUTOMATION",
            old_snapshot=snapshot,
            new_snapshot=snapshot,
            extra_changes=extra,
        )
        return result

    async def assign_owners(
        self,
        context: OperationContext,
        command: AssignTestCaseOwnersCommand,
    ) -> dict:
        command.validate()
        await ensure_authorized_entity(
            context=context,
            entity_id=command.case_id,
            getter=self._test_case_service.get_test_case,
            error_cls=TestCaseNotFoundError,
            checker=can_update_test_case,
            action="assign test case owners",
            workflow_getter=self._workflow_command_service.get_work_item_by_id,
        )

        old_snapshot = await self._test_case_service.get_case_raw_dict(command.case_id)
        result = await self._test_case_service.assign_owners(
            case_id=command.case_id,
            owner_id=command.owner_id,
            reviewer_id=command.reviewer_id,
            auto_dev_id=command.auto_dev_id,
        )
        new_snapshot = await self._test_case_service.get_case_raw_dict(command.case_id)
        await self._record_change(
            case_id=command.case_id,
            context=context,
            action="ASSIGN_OWNERS",
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
        )
        return result

    async def move_to_requirement(
        self,
        context: OperationContext,
        command: MoveTestCaseToRequirementCommand,
    ) -> dict:
        test_case, _workflow_item_id = await ensure_authorized_entity(
            context=context,
            entity_id=command.case_id,
            getter=self._test_case_service.get_test_case,
            error_cls=TestCaseNotFoundError,
            checker=can_update_test_case,
            action="move test case to requirement",
            workflow_getter=self._workflow_command_service.get_work_item_by_id,
        )

        if test_case.get("ref_req_id") == command.target_req_id:
            raise ValueError("test case is already linked to the target requirement")

        await ensure_entity(
            command.target_req_id,
            self._requirement_service.get_requirement,
            RequirementNotFoundError,
        )

        command.validate()
        old_snapshot = await self._test_case_service.get_case_raw_dict(command.case_id)
        result = await self._test_case_service.move_to_requirement(
            case_id=command.case_id,
            target_req_id=command.target_req_id,
        )
        new_snapshot = await self._test_case_service.get_case_raw_dict(command.case_id)
        await self._record_change(
            case_id=command.case_id,
            context=context,
            action="MOVE_REQUIREMENT",
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
        )
        return result

    async def list_change_logs(
        self,
        case_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        await self._test_case_service.get_test_case(case_id)
        return await self._change_log_service.list_logs(case_id, limit=limit, offset=offset)
