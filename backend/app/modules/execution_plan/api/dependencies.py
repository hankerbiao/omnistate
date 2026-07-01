from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.execution_plan.application.plan_command_service import PlanCommandService
from app.modules.execution_plan.application.plan_query_service import PlanQueryService
from app.modules.execution_plan.application.ports import (
    ExecutionDispatchPort,
    PlanNotificationPort,
)
from app.modules.execution_plan.service.execution_plan_service import ExecutionPlanService
from app.shared.service import SequenceIdService


def get_execution_plan_service() -> ExecutionPlanService:
    return ExecutionPlanService()


ExecutionPlanServiceDep = Annotated[ExecutionPlanService, Depends(get_execution_plan_service)]


def get_dispatch_port() -> ExecutionDispatchPort:
    """组合根：由 execution 模块提供端口实现。"""
    from app.modules.execution.application.plan_dispatch_adapter import PlanDispatchAdapter
    return PlanDispatchAdapter()


def get_notification_port() -> PlanNotificationPort:
    """组合根：由 notification 模块提供端口实现。"""
    from app.modules.notification.plan_notification_adapter import PlanNotificationAdapter
    return PlanNotificationAdapter()


def get_plan_command_service(
    dispatch_port: Annotated[ExecutionDispatchPort, Depends(get_dispatch_port)] = None,
    notification_port: Annotated[PlanNotificationPort, Depends(get_notification_port)] = None,
) -> PlanCommandService:
    """组合根：装配 PlanCommandService，注入跨模块端口实现。"""
    return PlanCommandService(
        dispatch_port=dispatch_port,
        notification_port=notification_port,
    )


PlanCommandServiceDep = Annotated[PlanCommandService, Depends(get_plan_command_service)]


def get_plan_query_service() -> PlanQueryService:
    return PlanQueryService()


PlanQueryServiceDep = Annotated[PlanQueryService, Depends(get_plan_query_service)]


def get_sequence_id_service() -> SequenceIdService:
    return SequenceIdService()


SequenceIdServiceDep = Annotated[SequenceIdService, Depends(get_sequence_id_service)]
