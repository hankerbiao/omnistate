from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.test_specs.application import (
    RequirementCommandService,
    RequirementQueryService,
    TestCaseCommandService,
    TestCaseQueryService,
    TestSpecsWorkflowProjectionHook,
    WorkflowServicesAdapter,
)
from app.modules.test_specs.service import CatalogService, LabService, RequirementService, TestCaseService
from app.modules.workflow.application import (
    OperationContext,
    WorkflowCommandService,
    WorkflowQueryService,
)
from app.modules.workflow.application.mutation_service import WorkflowMutationService
from app.modules.workflow.application.notification_hook import WorkflowNotificationHook


def get_workflow_query_service() -> WorkflowQueryService:
    return WorkflowQueryService()


WorkflowQueryServiceDep = Annotated[WorkflowQueryService, Depends(get_workflow_query_service)]


def get_workflow_mutation_service() -> WorkflowMutationService:
    return WorkflowMutationService()


WorkflowMutationServiceDep = Annotated[WorkflowMutationService, Depends(get_workflow_mutation_service)]


def get_requirement_service(
    workflow_mutation_service: WorkflowMutationServiceDep,
    workflow_query_service: WorkflowQueryServiceDep,
) -> RequirementService:
    return RequirementService(
        workflow_gateway=WorkflowServicesAdapter(
            mutation_service=workflow_mutation_service,
            query_service=workflow_query_service,
        )
    )


RequirementServiceDep = Annotated[RequirementService, Depends(get_requirement_service)]


def get_test_case_service(
    workflow_mutation_service: WorkflowMutationServiceDep,
    workflow_query_service: WorkflowQueryServiceDep,
) -> TestCaseService:
    return TestCaseService(
        workflow_gateway=WorkflowServicesAdapter(
            mutation_service=workflow_mutation_service,
            query_service=workflow_query_service,
        )
    )


TestCaseServiceDep = Annotated[TestCaseService, Depends(get_test_case_service)]


def get_lab_service() -> LabService:
    return LabService()


LabServiceDep = Annotated[LabService, Depends(get_lab_service)]


def get_catalog_service() -> CatalogService:
    return CatalogService()


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


def get_requirement_query_service(requirement_service: RequirementServiceDep) -> RequirementQueryService:
    return RequirementQueryService(requirement_service)


RequirementQueryServiceDep = Annotated[RequirementQueryService, Depends(get_requirement_query_service)]


def get_test_case_query_service(test_case_service: TestCaseServiceDep) -> TestCaseQueryService:
    return TestCaseQueryService(test_case_service)


TestCaseQueryServiceDep = Annotated[TestCaseQueryService, Depends(get_test_case_query_service)]


def get_workflow_projection_hook() -> TestSpecsWorkflowProjectionHook:
    return TestSpecsWorkflowProjectionHook()


WorkflowProjectionHookDep = Annotated[TestSpecsWorkflowProjectionHook, Depends(get_workflow_projection_hook)]


def get_workflow_command_service(
    workflow_query_service: WorkflowQueryServiceDep,
    workflow_mutation_service: WorkflowMutationServiceDep,
    projection_hook: WorkflowProjectionHookDep,
) -> WorkflowCommandService:
    return WorkflowCommandService(
        mutation_service=workflow_mutation_service,
        query_service=workflow_query_service,
        mutation_hooks=[projection_hook, WorkflowNotificationHook()],
    )


WorkflowCommandServiceDep = Annotated[WorkflowCommandService, Depends(get_workflow_command_service)]


def get_requirement_command_service(
    requirement_service: RequirementServiceDep,
    workflow_command_service: WorkflowCommandServiceDep,
) -> RequirementCommandService:
    return RequirementCommandService(requirement_service, workflow_command_service)


RequirementCommandServiceDep = Annotated[
    RequirementCommandService,
    Depends(get_requirement_command_service),
]


def get_test_case_command_service(
    test_case_service: TestCaseServiceDep,
    requirement_service: RequirementServiceDep,
    workflow_command_service: WorkflowCommandServiceDep,
) -> TestCaseCommandService:
    return TestCaseCommandService(test_case_service, requirement_service, workflow_command_service)


TestCaseCommandServiceDep = Annotated[TestCaseCommandService, Depends(get_test_case_command_service)]


def build_operation_context(current_user: dict) -> OperationContext:
    return OperationContext(
        actor_id=str(current_user["user_id"]),
        role_ids=[str(role_id) for role_id in current_user.get("role_ids", [])],
    )
