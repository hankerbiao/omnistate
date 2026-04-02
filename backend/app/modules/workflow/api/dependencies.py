from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.workflow.application import OperationContext, WorkflowCommandService, WorkflowQueryService
from app.modules.workflow.service.workflow_service import AsyncWorkflowService


def get_workflow_service() -> AsyncWorkflowService:
    return AsyncWorkflowService()


WorkflowServiceDep = Annotated[AsyncWorkflowService, Depends(get_workflow_service)]


def get_workflow_query_service(service: WorkflowServiceDep) -> WorkflowQueryService:
    return service._query_service


WorkflowQueryServiceDep = Annotated[WorkflowQueryService, Depends(get_workflow_query_service)]


def get_workflow_command_service(service: WorkflowServiceDep) -> WorkflowCommandService:
    return WorkflowCommandService(service)


WorkflowCommandServiceDep = Annotated[WorkflowCommandService, Depends(get_workflow_command_service)]


def build_operation_context(current_user: dict[str, object]) -> OperationContext:
    return OperationContext(
        actor_id=str(current_user["user_id"]),
        role_ids=[str(role_id) for role_id in current_user.get("role_ids", [])],
    )
