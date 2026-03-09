"""测试执行 API 路由 - Phase 5

使用发件箱模式的执行任务分发API。
通过显式命令服务确保可靠的外部事件发布。
"""
from __future__ import annotations

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.modules.execution.schemas import (
    DispatchTaskRequest,
    DispatchTaskResponse,
)
from app.modules.execution.application.execution_command_service import ExecutionCommandService
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.shared.service import SequenceIdService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/execution", tags=["Execution"])


def get_execution_command_service() -> ExecutionCommandService:
    return ExecutionCommandService()


ExecutionCommandServiceDep = Annotated[ExecutionCommandService, Depends(get_execution_command_service)]


@router.post(
    "/tasks/dispatch",
    response_model=APIResponse[DispatchTaskResponse],
    status_code=201,
    summary="下发测试任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def dispatch_task(
        request: DispatchTaskRequest,
        service: ExecutionCommandServiceDep,
        current_user=Depends(get_current_user),
):
    """分发测试任务 - 使用发件箱模式

    该端点使用显式命令模式和发件箱机制，确保：
    - 本地数据库事务与Kafka发布解耦
    - 任务创建不依赖外部Kafka的可用性
    - 支持可靠的重试机制
    """
    try:
        # 生成任务ID
        year = datetime.now().year
        seq = await SequenceIdService().next(f"execution_task:{year}")
        task_id = f"ET-{year}-{str(seq).zfill(6)}"
        external_task_id = f"EXT-{task_id}"

        # 构建用例ID列表
        case_ids = [item.case_id for item in request.cases]

        # 创建显式命令
        command = DispatchExecutionTaskCommand(
            task_id=task_id,
            external_task_id=external_task_id,
            framework=request.framework,
            trigger_source=request.trigger_source or "manual",
            created_by=current_user["user_id"],
            case_ids=case_ids,
            callback_url=request.callback_url,
            dut=request.dut,
            runtime_config=request.runtime_config,
        )

        # 使用命令服务处理任务分发
        data = await service.dispatch_execution_task(command, actor_id=current_user["user_id"])

        return APIResponse(data=data)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/tasks/{task_id}/status",
    response_model=APIResponse[dict],
    summary="获取任务状态",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def get_task_status(
        task_id: str,
        service: ExecutionCommandServiceDep,
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
        service: ExecutionCommandServiceDep,
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
