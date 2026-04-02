from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.workflow.application import (
    OperationContext,
    WorkflowCommandService,
    WorkflowMutationService,
    WorkflowQueryService,
)


def get_workflow_query_service() -> WorkflowQueryService:
    return WorkflowQueryService()


WorkflowQueryServiceDep = Annotated[WorkflowQueryService, Depends(get_workflow_query_service)]


def get_workflow_mutation_service() -> WorkflowMutationService:
    return WorkflowMutationService()


WorkflowMutationServiceDep = Annotated[WorkflowMutationService, Depends(get_workflow_mutation_service)]


def get_workflow_command_service(
    query_service: WorkflowQueryServiceDep,
    mutation_service: WorkflowMutationServiceDep,
) -> WorkflowCommandService:
    return WorkflowCommandService(mutation_service, query_service=query_service)


WorkflowCommandServiceDep = Annotated[WorkflowCommandService, Depends(get_workflow_command_service)]


def build_operation_context(current_user: dict[str, object]) -> OperationContext:
    return OperationContext(
        actor_id=str(current_user["user_id"]),
        role_ids=[str(role_id) for role_id in current_user.get("role_ids", [])],
    )
