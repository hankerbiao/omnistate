"""测试执行 API 路由。"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.modules.execution.application.agent_service import ExecutionAgentService
from app.modules.execution.application.task_command_service import ExecutionTaskCommandService
from app.modules.execution.application.task_query_service import ExecutionTaskQueryService
from app.modules.execution.schemas import (
    AgentHeartbeatRequest,
    AgentRegisterRequest,
    DispatchTaskRequest,
    DispatchTaskResponse,
    ExecutionAgentResponse,
    ExecutionTaskListItem,
    RerunTaskRequest,
)
from app.shared.service import SequenceIdService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission
from app.shared.core.logger import log as logger

router = APIRouter(prefix="/execution", tags=["Execution"])


def get_task_command_service() -> ExecutionTaskCommandService:
    return ExecutionTaskCommandService()


ExecutionTaskCommandServiceDep = Annotated[
    ExecutionTaskCommandService,
    Depends(get_task_command_service),
]


def get_task_query_service() -> ExecutionTaskQueryService:
    return ExecutionTaskQueryService()


ExecutionTaskQueryServiceDep = Annotated[
    ExecutionTaskQueryService,
    Depends(get_task_query_service),
]


def get_agent_service() -> ExecutionAgentService:
    return ExecutionAgentService()


ExecutionAgentServiceDep = Annotated[ExecutionAgentService, Depends(get_agent_service)]


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
        service: ExecutionTaskCommandServiceDep,
        sequence_service: SequenceIdServiceDep,
        current_user=Depends(get_current_user),
):
    """分发测试任务。"""
    try:
        data = await service.create_and_dispatch_task(
            request=request,
            actor_id=current_user["user_id"],
            sequence_service=sequence_service,
        )
        return APIResponse(data=data)

    except ValueError as exc:
        logger.warning(
            "Dispatch task request rejected with validation error: "
            f"user_id={current_user['user_id']}, framework={request.framework}, "
            f"dispatch_channel={request.dispatch_channel}, detail={exc}"
        )
        raise HTTPException(status_code=400, detail=str(exc))
    except KeyError as exc:
        logger.warning(
            "Dispatch task request rejected with missing dependency: "
            f"user_id={current_user['user_id']}, framework={request.framework}, "
            f"dispatch_channel={request.dispatch_channel}, "
            f"auto_case_ids={[item.auto_case_id for item in request.cases]}, detail={exc}"
        )
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception(
            "Dispatch task request failed unexpectedly: "
            f"user_id={current_user['user_id']}, framework={request.framework}, "
            f"dispatch_channel={request.dispatch_channel}"
        )
        raise


@router.delete(
    "/tasks/{task_id}",
    response_model=APIResponse[dict],
    summary="删除执行任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def delete_task(
        task_id: str,
        service: ExecutionTaskCommandServiceDep,
        current_user=Depends(get_current_user),
):
    """删除执行任务（逻辑删除）。"""
    try:
        data = await service.delete_task(task_id, actor_id=current_user["user_id"])
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/tasks/{task_id}/rerun",
    response_model=APIResponse[DispatchTaskResponse],
    status_code=201,
    summary="重新运行测试任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def rerun_task(
        task_id: str,
        request: RerunTaskRequest,
        service: ExecutionTaskCommandServiceDep,
        sequence_service: SequenceIdServiceDep,
        current_user=Depends(get_current_user),
):
    """基于已有任务快照创建一个新的执行任务。"""
    try:
        year = datetime.now().year
        seq = await sequence_service.next(f"execution_task:{year}")
        new_task_id = f"ET-{year}-{str(seq).zfill(6)}"
        data = await service.rerun_task(
            source_task_id=task_id,
            new_task_id=new_task_id,
            actor_id=current_user["user_id"],
            request=request,
        )
        return APIResponse(data=data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/agents/register",
    response_model=APIResponse[ExecutionAgentResponse],
    status_code=201,
    summary="注册或刷新执行代理",
)
async def register_agent(
        request: AgentRegisterRequest,
        service: ExecutionAgentServiceDep,
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
        service: ExecutionAgentServiceDep,
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
        service: ExecutionAgentServiceDep,
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
        service: ExecutionAgentServiceDep,
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
        service: ExecutionTaskQueryServiceDep,
        current_user=Depends(get_current_user),
):
    """查询执行任务列表。"""
    data = await service.list_tasks()
    return APIResponse(data=data)


@router.get(
    "/tasks/{task_id}/status",
    response_model=APIResponse[dict],
    summary="获取任务状态",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def get_task_status(
        task_id: str,
        service: ExecutionTaskQueryServiceDep,
        current_user=Depends(get_current_user),
):
    """获取任务状态"""
    try:
        data = await service.get_task_status(task_id)
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
