"""
业务事项路由（MongoDB 版本）

提供工作项的 CRUD 和状态流转接口
"""
from typing import Dict, List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.exceptions import (
    WorkItemNotFoundError,
    InvalidTransitionError,
    MissingRequiredFieldError,
)
from app.api.schemas.work_item import (
    CreateWorkItemRequest,
    TransitionRequest,
    TransitionResponse,
    WorkItemResponse,
    TransitionLogResponse,
)
from app.api.schemas.workflow import (
    WorkTypeResponse,
    WorkflowStateResponse,
    WorkflowConfigResponse,
    ErrorResponse,
)
from app.services.workflow_service import AsyncWorkflowService

router = APIRouter(prefix="/work-items", tags=["WorkItems"])


def get_workflow_service() -> AsyncWorkflowService:
    return AsyncWorkflowService()


WorkflowServiceDep = Annotated[AsyncWorkflowService, Depends(get_workflow_service)]


# ==================== 事项类型和状态管理 ====================

@router.get(
    "/types",
    response_model=List[WorkTypeResponse],
    summary="获取事项类型列表"
)
async def get_work_types(service: WorkflowServiceDep):
    """获取系统中定义的所有业务事项类型"""
    return await service.get_work_types()


@router.get(
    "/states",
    response_model=List[WorkflowStateResponse],
    summary="获取流程状态列表"
)
async def get_workflow_states(service: WorkflowServiceDep):
    """获取系统中定义的所有流程状态"""
    return await service.get_workflow_states()


@router.get(
    "/configs",
    response_model=List[WorkflowConfigResponse],
    summary="获取指定类型的所有流转配置",
    responses={404: {"model": ErrorResponse, "description": "类型不存在"}}
)
async def get_workflow_configs(
    service: WorkflowServiceDep,
    type_code: str = Query(..., description="事项类型编码"),
):
    """获取指定事项类型的所有流转配置规则"""
    configs = await service.get_workflow_configs(type_code)
    if not configs:
        raise HTTPException(status_code=404, detail=f"类型 '{type_code}' 的流转配置不存在")
    return configs


# ==================== 事项 CRUD 操作 ====================

@router.post(
    "",
    response_model=WorkItemResponse,
    status_code=201,
    summary="创建业务事项"
)
async def create_work_item(
    request: CreateWorkItemRequest,
    service: WorkflowServiceDep,
):
    """创建一个新的业务事项，初始状态为 DRAFT"""
    try:
        item = await service.create_item(
            type_code=request.type_code,
            title=request.title,
            content=request.content,
            creator_id=request.creator_id
        )
        return item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=List[WorkItemResponse],
    summary="获取事项列表"
)
async def list_work_items(
    service: WorkflowServiceDep,
    type_code: Optional[str] = Query(None, description="按类型筛选"),
    state: Optional[str] = Query(None, description="按状态筛选"),
    owner_id: Optional[int] = Query(None, description="按当前处理人筛选"),
    creator_id: Optional[int] = Query(None, description="按创建人筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
):
    """
    查询业务事项列表，支持按类型、状态、处理人、创建人筛选

    说明：
    - 如果同时传入了 owner_id 和 creator_id，使用 OR 逻辑
    - 即：当前处理人是 owner_id OR 创建人是 creator_id
    - 这样创建者可以始终看到自己创建的任务，无论任务被指派给谁
    """
    return await service.list_items(
        type_code=type_code,
        state=state,
        owner_id=owner_id,
        creator_id=creator_id,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{item_id}",
    response_model=WorkItemResponse,
    summary="获取事项详情",
    responses={404: {"model": ErrorResponse, "description": "事项不存在"}}
)
async def get_work_item(
    item_id: str,
    service: WorkflowServiceDep
):
    """根据 ID 获取业务事项详情"""
    try:
        item = await service.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"事项 ID={item_id} 不存在")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{item_id}",
    summary="删除事项",
    responses={
        404: {"model": ErrorResponse, "description": "事项不存在"},
        400: {"model": ErrorResponse, "description": "删除失败"}
    }
)
async def delete_work_item(
    item_id: str,
    service: WorkflowServiceDep,
):
    """
    删除业务事项（及其所有流转日志）

    注意：实际项目中建议使用软删除（is_deleted 标志位）替代硬删除
    """
    try:
        await service.delete_item(item_id)
        return {"message": f"事项 ID={item_id} 已删除", "item_id": item_id}
    except WorkItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除失败: {str(e)}")


# ==================== 状态流转操作 ====================

@router.post(
    "/{item_id}/transition",
    response_model=TransitionResponse,
    summary="执行状态流转",
    responses={
        404: {"model": ErrorResponse, "description": "事项不存在"},
        400: {"model": ErrorResponse, "description": "流转失败"}
    }
)
async def transition_work_item(
    item_id: str,
    request: TransitionRequest,
    service: WorkflowServiceDep,
):
    """
    执行状态流转
    """
    try:
        # 调用 Service 执行流转（Service 内部负责事务提交）
        result = await service.handle_transition(
            work_item_id=item_id,
            action=request.action,
            operator_id=request.operator_id,
            form_data=request.form_data
        )

        return result
    except WorkItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (InvalidTransitionError, MissingRequiredFieldError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{item_id}/reassign",
    response_model=WorkItemResponse,
    summary="改派任务",
    responses={
        404: {"model": ErrorResponse, "description": "事项不存在"},
        400: {"model": ErrorResponse, "description": "改派失败"}
    }
)
async def reassign_work_item(
    item_id: str,
    service: WorkflowServiceDep,
    operator_id: int = Query(..., description="操作人ID"),
    target_owner_id: int = Query(..., description="目标处理人ID"),
):
    """
    改派任务给其他处理人（不改变状态）

    - 无需经过工作流配置，通用改派逻辑
    - 更新当前处理人并记录操作日志
    """
    try:
        return await service.reassign_item(item_id, operator_id, target_owner_id)
    except WorkItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"改派失败: {str(e)}")


@router.get(
    "/{item_id}/logs",
    response_model=List[TransitionLogResponse],
    summary="获取流转历史"
)
async def get_transition_logs(
    item_id: str,
    service: WorkflowServiceDep,
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
):
    """获取指定事项的所有流转日志（按时间倒序）"""
    try:
        return await service.get_logs(item_id, limit)
    except WorkItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/logs/batch",
    response_model=Dict[str, List[TransitionLogResponse]],
    summary="批量获取事项流转日志"
)
async def batch_get_transition_logs(
    service: WorkflowServiceDep,
    item_ids: str = Query(..., description="事项ID列表，逗号分隔，如: id1,id2,id3"),
    limit: int = Query(20, ge=1, le=100, description="每个事项最多返回的日志数量"),
):
    """
    批量获取多个事项的流转日志

    返回格式: { item_id: [日志列表] }

    用途：在看板列表中展示任务的状态流转时间线
    """
    # 解析 item_ids（MongoDB ObjectId 是字符串）
    ids = [x.strip() for x in item_ids.split(",") if x.strip()]

    if not ids:
        return {}

    return await service.batch_get_logs(ids, limit)


@router.get(
    "/{item_id}/transitions",
    summary="获取可用的下一步流转"
)
async def get_available_transitions(
    item_id: str,
    service: WorkflowServiceDep,
):
    """获取指定事项在当前状态下可以执行的所有流转动作"""
    try:
        result = await service.get_item_with_transitions(item_id)
        item = result["item"]
        return {
            "item_id": item_id,
            "current_state": item["current_state"],
            "available_transitions": result["available_transitions"]
        }
    except WorkItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
