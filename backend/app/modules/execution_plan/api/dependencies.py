from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.execution.application.task_command_service import ExecutionTaskCommandService
from app.modules.execution_plan.service.execution_plan_service import ExecutionPlanService
from app.shared.service import SequenceIdService


def get_execution_plan_service() -> ExecutionPlanService:
    return ExecutionPlanService()


ExecutionPlanServiceDep = Annotated[ExecutionPlanService, Depends(get_execution_plan_service)]


def get_task_command_service() -> ExecutionTaskCommandService:
    return ExecutionTaskCommandService()


ExecutionTaskCommandServiceDep = Annotated[
    ExecutionTaskCommandService,
    Depends(get_task_command_service),
]


def get_sequence_id_service() -> SequenceIdService:
    return SequenceIdService()


SequenceIdServiceDep = Annotated[SequenceIdService, Depends(get_sequence_id_service)]
