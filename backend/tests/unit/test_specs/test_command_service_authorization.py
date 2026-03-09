"""命令服务授权检查测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.test_specs.application import (
    RequirementCommandService,
    UpdateRequirementCommand,
    DeleteRequirementCommand,
)
from app.modules.test_specs.application.commands import UpdateTestCaseCommand, DeleteTestCaseCommand
from app.modules.test_specs.application.test_case_command_service import TestCaseCommandService
from app.modules.workflow.application import OperationContext
from app.modules.workflow.domain.exceptions import PermissionDeniedError
from app.modules.test_specs.domain.exceptions import RequirementNotFoundError, TestCaseNotFoundError


class TestRequirementCommandServiceAuthorization:
    """需求命令服务授权测试"""

    @pytest.mark.asyncio
    async def test_update_requirement_requires_authorization(self):
        """测试更新需求需要授权"""
        requirement_service = AsyncMock()
        workflow_command_service = AsyncMock()

        requirement_service.get_requirement.return_value = {
            "req_id": "req-1",
            "tpm_owner_id": "user-1",
            "workflow_item_id": "wi-1",
        }

        service = RequirementCommandService(requirement_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-2", role_ids=["ROLE_USER"])
        command = UpdateRequirementCommand(req_id="req-1", payload={"title": "New Title"})

        with pytest.raises(PermissionDeniedError):
            await service.update_requirement(actor_context, command)

    @pytest.mark.asyncio
    async def test_update_requirement_allows_owner(self):
        """测试需求拥有者可以更新"""
        requirement_service = AsyncMock()
        workflow_command_service = AsyncMock()

        requirement_service.get_requirement.return_value = {
            "req_id": "req-1",
            "tpm_owner_id": "user-1",
            "workflow_item_id": None,
        }
        requirement_service.update_requirement.return_value = {"req_id": "req-1"}

        service = RequirementCommandService(requirement_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-1", role_ids=["ROLE_USER"])
        command = UpdateRequirementCommand(req_id="req-1", payload={"title": "New Title"})

        result = await service.update_requirement(actor_context, command)
        assert result["req_id"] == "req-1"

    @pytest.mark.asyncio
    async def test_update_requirement_allows_admin(self):
        """测试管理员可以更新任何需求"""
        requirement_service = AsyncMock()
        workflow_command_service = AsyncMock()

        requirement_service.get_requirement.return_value = {
            "req_id": "req-1",
            "tpm_owner_id": "user-1",
            "workflow_item_id": None,
        }
        requirement_service.update_requirement.return_value = {"req_id": "req-1"}

        service = RequirementCommandService(requirement_service, workflow_command_service)

        actor_context = OperationContext(actor_id="admin", role_ids=["ROLE_ADMIN"])
        command = UpdateRequirementCommand(req_id="req-1", payload={"title": "New Title"})

        result = await service.update_requirement(actor_context, command)
        assert result["req_id"] == "req-1"

    @pytest.mark.asyncio
    async def test_update_nonexistent_requirement_raises_error(self):
        """测试更新不存在的需求会引发错误"""
        requirement_service = AsyncMock()
        workflow_command_service = AsyncMock()

        requirement_service.get_requirement.return_value = None

        service = RequirementCommandService(requirement_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-1", role_ids=["ROLE_USER"])
        command = UpdateRequirementCommand(req_id="req-999", payload={"title": "New Title"})

        with pytest.raises(RequirementNotFoundError):
            await service.update_requirement(actor_context, command)

    @pytest.mark.asyncio
    async def test_delete_requirement_requires_authorization(self):
        """测试删除需求需要授权"""
        requirement_service = AsyncMock()
        workflow_command_service = AsyncMock()

        requirement_service.get_requirement.return_value = {
            "req_id": "req-1",
            "tpm_owner_id": "user-1",
            "workflow_item_id": "wi-1",
        }

        service = RequirementCommandService(requirement_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-3", role_ids=["ROLE_USER"])
        command = DeleteRequirementCommand(req_id="req-1")

        with pytest.raises(PermissionDeniedError):
            await service.delete_requirement(actor_context, command)

    @pytest.mark.asyncio
    async def test_delete_requirement_allows_requirement_owner(self):
        """测试需求拥有者可以删除需求（当没有工作项时）"""
        requirement_service = AsyncMock()
        workflow_command_service = AsyncMock()

        requirement = {
            "req_id": "req-1",
            "tpm_owner_id": "user-1",
            "workflow_item_id": None,
        }
        requirement_service.get_requirement.return_value = requirement
        requirement_service.delete_requirement = AsyncMock()

        service = RequirementCommandService(requirement_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-1", role_ids=["ROLE_USER"])
        command = DeleteRequirementCommand(req_id="req-1")

        await service.delete_requirement(actor_context, command)
        requirement_service.delete_requirement.assert_called_once_with("req-1")


class TestTestCaseCommandServiceAuthorization:
    """测试用例命令服务授权测试"""

    @pytest.mark.asyncio
    async def test_update_test_case_requires_authorization(self):
        """测试更新测试用例需要授权"""
        test_case_service = AsyncMock()
        workflow_command_service = AsyncMock()

        test_case_service.get_test_case.return_value = {
            "case_id": "case-1",
            "owner_id": "user-1",
            "workflow_item_id": "wi-1",
        }

        service = TestCaseCommandService(test_case_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-2", role_ids=["ROLE_USER"])
        command = UpdateTestCaseCommand(case_id="case-1", payload={"title": "New Title"})

        with pytest.raises(PermissionDeniedError):
            await service.update_test_case(actor_context, command)

    @pytest.mark.asyncio
    async def test_update_test_case_allows_owner(self):
        """测试测试用例拥有者可以更新"""
        test_case_service = AsyncMock()
        workflow_command_service = AsyncMock()

        test_case_service.get_test_case.return_value = {
            "case_id": "case-1",
            "owner_id": "user-1",
            "workflow_item_id": None,
        }
        test_case_service.update_test_case.return_value = {"case_id": "case-1"}

        service = TestCaseCommandService(test_case_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-1", role_ids=["ROLE_USER"])
        command = UpdateTestCaseCommand(case_id="case-1", payload={"title": "New Title"})

        result = await service.update_test_case(actor_context, command)
        assert result["case_id"] == "case-1"

    @pytest.mark.asyncio
    async def test_delete_test_case_requires_authorization(self):
        """测试删除测试用例需要授权"""
        test_case_service = AsyncMock()
        workflow_command_service = AsyncMock()

        test_case_service.get_test_case.return_value = {
            "case_id": "case-1",
            "owner_id": "user-1",
            "workflow_item_id": "wi-1",
        }

        service = TestCaseCommandService(test_case_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-2", role_ids=["ROLE_USER"])
        command = DeleteTestCaseCommand(case_id="case-1")

        with pytest.raises(PermissionDeniedError):
            await service.delete_test_case(actor_context, command)

    @pytest.mark.asyncio
    async def test_delete_test_case_allows_admin(self):
        """测试管理员可以删除任何测试用例"""
        test_case_service = AsyncMock()
        workflow_command_service = AsyncMock()

        test_case_service.get_test_case.return_value = {
            "case_id": "case-1",
            "owner_id": "user-1",
            "workflow_item_id": "wi-1",
        }

        workflow_command_service.delete_work_item = AsyncMock()

        service = TestCaseCommandService(test_case_service, workflow_command_service)

        actor_context = OperationContext(actor_id="admin", role_ids=["ROLE_ADMIN"])
        command = DeleteTestCaseCommand(case_id="case-1")

        await service.delete_test_case(actor_context, command)
        workflow_command_service.delete_work_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_test_case_raises_error(self):
        """测试更新不存在的测试用例会引发错误"""
        test_case_service = AsyncMock()
        workflow_command_service = AsyncMock()

        test_case_service.get_test_case.return_value = None

        service = TestCaseCommandService(test_case_service, workflow_command_service)

        actor_context = OperationContext(actor_id="user-1", role_ids=["ROLE_USER"])
        command = UpdateTestCaseCommand(case_id="case-999", payload={"title": "New Title"})

        with pytest.raises(TestCaseNotFoundError):
            await service.update_test_case(actor_context, command)