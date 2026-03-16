"""测试执行 API 路由。"""
from __future__ import annotations

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.modules.execution.schemas import (
    AgentHeartbeatRequest,
    AgentRegisterRequest,
    ConsumeAckRequest,
    DispatchTaskRequest,
    DispatchTaskResponse,
    ExecutionAgentResponse,
    ExecutionCaseStatusReportRequest,
    ExecutionCaseStatusReportResponse,
    ExecutionEventReportRequest,
    ExecutionEventReportResponse,
    ExecutionTaskCompleteRequest,
    ExecutionTaskCompleteResponse,
    ExecutionTaskListItem,
    ScheduledTaskMutationResponse,
    UpdateScheduledTaskRequest,
)
from app.modules.execution.application.execution_service import ExecutionService
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.shared.service import SequenceIdService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/execution", tags=["Execution"])


def get_execution_service() -> ExecutionService:
    return ExecutionService()


ExecutionServiceDep = Annotated[ExecutionService, Depends(get_execution_service)]


def get_sequence_id_service() -> SequenceIdService:
    """提供可覆盖的序列号服务依赖，便于接口测试。"""
    return SequenceIdService()


SequenceIdServiceDep = Annotated[SequenceIdService, Depends(get_sequence_id_service)]


@router.post(
    "/tasks/dispatch",
    response_model=APIResponse[DispatchTaskResponse],
    status_code=201,
    summary="下发测试任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def dispatch_task(
        request: DispatchTaskRequest,
        service: ExecutionServiceDep,
        sequence_service: SequenceIdServiceDep,
        current_user=Depends(get_current_user),
):
    """分发测试任务。"""
    try:
        # 生成任务ID
        year = datetime.now().year
        seq = await sequence_service.next(f"execution_task:{year}")
        task_id = f"ET-{year}-{str(seq).zfill(6)}"
        external_task_id = f"EXT-{task_id}"

        # 构建用例ID列表
        case_ids = [item.case_id for item in request.cases]

        # 创建显式命令
        command = DispatchExecutionTaskCommand(
            task_id=task_id,
            external_task_id=external_task_id,
            framework=request.framework,
            agent_id=request.agent_id,
            trigger_source=request.trigger_source or "manual",
            created_by=current_user["user_id"],
            case_ids=case_ids,
            schedule_type=request.schedule_type,
            planned_at=request.planned_at,
            callback_url=request.callback_url,
            dut=request.dut,
            runtime_config=request.runtime_config,
        )

        # 使用执行服务处理任务分发
        data = await service.dispatch_execution_task(command, actor_id=current_user["user_id"])

        return APIResponse(data=data)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/tasks/{task_id}/consume-ack",
    response_model=APIResponse[dict],
    summary="确认任务已被消费",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def ack_task_consumed(
        task_id: str,
        request: ConsumeAckRequest,
        service: ExecutionServiceDep,
        current_user=Depends(get_current_user),
):
    """消费者确认已接收到任务。"""
    try:
        data = await service.ack_task_consumed(
            task_id,
            consumer_id=request.consumer_id or current_user["user_id"],
        )
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/tasks/{task_id}/events",
    response_model=APIResponse[ExecutionEventReportResponse],
    summary="接收任务事件上报",
)
async def report_task_event(
        task_id: str,
        request: ExecutionEventReportRequest,
        service: ExecutionServiceDep,
):
    """接收代理端上报的任务事件。"""
    try:
        data = await service.report_task_event(task_id, request.model_dump())
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/tasks/{task_id}/cases/{case_id}/status",
    response_model=APIResponse[ExecutionCaseStatusReportResponse],
    summary="接收用例执行状态上报",
)
async def report_case_status(
        task_id: str,
        case_id: str,
        request: ExecutionCaseStatusReportRequest,
        service: ExecutionServiceDep,
):
    """接收代理端上报的用例状态和进度。"""
    try:
        data = await service.report_case_status(task_id, case_id, request.model_dump())
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/tasks/{task_id}/complete",
    response_model=APIResponse[ExecutionTaskCompleteResponse],
    summary="接收任务完成结果上报",
)
async def complete_task(
        task_id: str,
        request: ExecutionTaskCompleteRequest,
        service: ExecutionServiceDep,
):
    """接收代理端上报的任务最终状态。"""
    try:
        data = await service.complete_task(task_id, request.model_dump())
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=APIResponse[ScheduledTaskMutationResponse],
    summary="取消未触发的定时任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def cancel_scheduled_task(
        task_id: str,
        service: ExecutionServiceDep,
        current_user=Depends(get_current_user),
):
    """取消未触发的定时执行任务。"""
    try:
        data = await service.cancel_scheduled_task(task_id, actor_id=current_user["user_id"])
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put(
    "/tasks/{task_id}/schedule",
    response_model=APIResponse[ScheduledTaskMutationResponse],
    summary="修改未触发的定时任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def update_scheduled_task(
        task_id: str,
        request: UpdateScheduledTaskRequest,
        service: ExecutionServiceDep,
        current_user=Depends(get_current_user),
):
    """修改未触发的定时执行任务。"""
    try:
        data = await service.update_scheduled_task(
            task_id,
            actor_id=current_user["user_id"],
            payload=request.model_dump(exclude_none=True),
        )
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/agents/register",
    response_model=APIResponse[ExecutionAgentResponse],
    status_code=201,
    summary="注册或刷新执行代理",
)
async def register_agent(
        request: AgentRegisterRequest,
        service: ExecutionServiceDep,
):
    """执行代理注册接口。"""
    data = await service.register_agent(request.model_dump())
    return APIResponse(data=data)


@router.post(
    "/agents/{agent_id}/heartbeat",
    response_model=APIResponse[ExecutionAgentResponse],
    summary="上报代理心跳",
)
async def heartbeat_agent(
        agent_id: str,
        request: AgentHeartbeatRequest,
        service: ExecutionServiceDep,
):
    """执行代理心跳接口。"""
    try:
        data = await service.heartbeat_agent(agent_id, request.model_dump())
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/agents",
    response_model=APIResponse[list[ExecutionAgentResponse]],
    summary="查询执行代理列表",
    dependencies=[Depends(require_permission("execution_agents:read"))],
)
async def list_agents(
        service: ExecutionServiceDep,
        region: str | None = None,
        status: str | None = None,
        online_only: bool = False,
        current_user=Depends(get_current_user),
):
    """查询执行代理列表。"""
    data = await service.list_agents(
        region=region,
        status=status,
        online_only=online_only,
    )
    return APIResponse(data=data)


@router.get(
    "/agents/{agent_id}",
    response_model=APIResponse[ExecutionAgentResponse],
    summary="查询执行代理详情",
    dependencies=[Depends(require_permission("execution_agents:read"))],
)
async def get_agent(
        agent_id: str,
        service: ExecutionServiceDep,
        current_user=Depends(get_current_user),
):
    """查询执行代理详情。"""
    try:
        data = await service.get_agent(agent_id)
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/tasks",
    response_model=APIResponse[list[ExecutionTaskListItem]],
    summary="查询执行任务列表",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def list_tasks(
        service: ExecutionServiceDep,
        schedule_type: str | None = None,
        schedule_status: str | None = None,
        dispatch_status: str | None = None,
        consume_status: str | None = None,
        overall_status: str | None = None,
        created_by: str | None = None,
        agent_id: str | None = None,
        framework: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
        current_user=Depends(get_current_user),
):
    """查询执行任务列表。"""
    data = await service.list_tasks(
        schedule_type=schedule_type,
        schedule_status=schedule_status,
        dispatch_status=dispatch_status,
        consume_status=consume_status,
        overall_status=overall_status,
        created_by=created_by,
        agent_id=agent_id,
        framework=framework,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.get(
    "/tasks/{task_id}/status",
    response_model=APIResponse[dict],
    summary="获取任务状态",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def get_task_status(
        task_id: str,
        service: ExecutionServiceDep,
        current_user=Depends(get_current_user),
):
    """获取任务状态"""
    try:
        data = await service.get_task_status(task_id)
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/tasks/{task_id}/retry",
    response_model=APIResponse[dict],
    summary="重试失败的任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def retry_task(
        task_id: str,
        service: ExecutionServiceDep,
        current_user=Depends(get_current_user),
):
    """重试失败的任务"""
    try:
        data = await service.retry_failed_task(task_id, actor_id=current_user["user_id"])
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
