from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.execution_plan.application.plan_command_service import PlanCommandService
from app.modules.execution_plan.application.plan_query_service import PlanQueryService
from app.modules.execution_plan.service.execution_plan_service import ExecutionPlanService
from app.shared.service import SequenceIdService


def get_execution_plan_service() -> ExecutionPlanService:
    return ExecutionPlanService()


ExecutionPlanServiceDep = Annotated[ExecutionPlanService, Depends(get_execution_plan_service)]


def get_plan_command_service() -> PlanCommandService:
    return PlanCommandService()


PlanCommandServiceDep = Annotated[PlanCommandService, Depends(get_plan_command_service)]


def get_plan_query_service() -> PlanQueryService:
    return PlanQueryService()


PlanQueryServiceDep = Annotated[PlanQueryService, Depends(get_plan_query_service)]


def get_sequence_id_service() -> SequenceIdService:
    return SequenceIdService()


SequenceIdServiceDep = Annotated[SequenceIdService, Depends(get_sequence_id_service)]
