"""测试执行 API 路由。"""
from __future__ import annotations

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.modules.execution.schemas import (
    AgentHeartbeatRequest,
    AgentRegisterRequest,
    DispatchTaskRequest,
    DispatchTaskResponse,
    ExecutionAgentResponse,
    ExecutionTaskListItem,
    ScheduledTaskMutationResponse,
    StopTaskRequest,
    StopTaskResponse,
)
from app.modules.execution.application.execution_service import ExecutionService
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.shared.service import SequenceIdService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission
from app.shared.core.logger import log as logger

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
        request_case_payload = [
            {
                "auto_case_id": item.auto_case_id,
                "case_path": item.case_path,
                "case_name": item.case_name,
                "script_entity_id": item.script_entity_id,
                "parameters": dict(item.parameters),
            }
            for item in request.cases
        ]
        logger.info(
            "Dispatch task request received: "
            f"user_id={current_user['user_id']}, framework={request.framework}, "
            f"dispatch_channel={request.dispatch_channel}, agent_id={request.agent_id}, "
            f"schedule_type={request.schedule_type}, planned_at={request.planned_at}, "
            f"cases={request_case_payload}"
        )

        # 生成任务ID
        year = datetime.now().year
        seq = await sequence_service.next(f"execution_task:{year}")
        task_id = f"ET-{year}-{str(seq).zfill(6)}"
        external_task_id = f"EXT-{task_id}"

        # 构建自动化用例ID列表
        auto_case_ids = [item.auto_case_id for item in request.cases]
        case_configs = [dict(item.config) for item in request.cases]
        case_payloads = [
            {
                "case_id": "",
                "case_path": item.case_path,
                "case_name": item.case_name,
                "parameters": dict(item.parameters),
            }
            for item in request.cases
        ]
        case_ids, script_entity_ids = await service.resolve_case_bindings_by_auto_case_ids(auto_case_ids)
        case_payloads = [
            {
                **case_payload,
                "case_id": case_id,
            }
            for case_payload, case_id in zip(case_payloads, case_ids)
        ]
        logger.debug(
            "Dispatch task case bindings resolved: "
            f"task_id={task_id}, auto_case_ids={auto_case_ids}, case_ids={case_ids}, "
            f"script_entity_ids={script_entity_ids}, case_configs={case_configs}, "
            f"case_payloads={case_payloads}"
        )

        # 创建显式命令
        command = DispatchExecutionTaskCommand(
            task_id=task_id,
            external_task_id=external_task_id,
            framework=request.framework,
            dispatch_channel=request.dispatch_channel,
            agent_id=request.agent_id,
            trigger_source=request.trigger_source,
            created_by=current_user["user_id"],
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            script_entity_ids=script_entity_ids,
            case_configs=case_configs,
            case_payloads=case_payloads,
            schedule_type=request.schedule_type,
            planned_at=request.planned_at,
            callback_url=request.callback_url,
            category=request.category,
            project_tag=request.project_tag,
            repo_url=request.repo_url,
            branch=request.branch,
            common_parameters=request.common_parameters,
            pytest_options=request.pytest_options,
            timeout=request.timeout,
            dut=request.dut,
        )

        # 使用执行服务处理任务分发
        data = await service.dispatch_execution_task(command, actor_id=current_user["user_id"])
        logger.info(
            "Dispatch task request handled successfully: "
            f"task_id={task_id}, external_task_id={external_task_id}, "
            f"dispatch_status={data.get('dispatch_status')}, overall_status={data.get('overall_status')}, "
            f"case_count={data.get('case_count')}"
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
        service: ExecutionServiceDep,
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


@router.post(
    "/tasks/{task_id}/stop",
    response_model=APIResponse[StopTaskResponse],
    summary="执行完当前 case 后停止任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def stop_task(
        task_id: str,
        request: StopTaskRequest,
        service: ExecutionServiceDep,
        current_user=Depends(get_current_user),
):
    """请求当前任务在当前 case 完成后停止，不再继续下发下一条。"""
    try:
        data = await service.stop_task_after_current_case(
            task_id=task_id,
            actor_id=current_user["user_id"],
            reason=request.reason,
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
