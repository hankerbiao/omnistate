"""
业务事项路由

提供工作项的 CRUD 和状态流转接口
"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select

from models import BusWorkItem
from services.workflow_service import AsyncWorkflowService
from services.exceptions import (
    WorkItemNotFoundError,
    InvalidTransitionError,
    MissingRequiredFieldError,
)
from api.deps import DatabaseDep
from api.schemas.work_item import (
    CreateWorkItemRequest,
    TransitionRequest,
    TransitionResponse,
    WorkItemResponse,
    TransitionLogResponse,
)
from api.schemas.workflow import (
    WorkTypeResponse,
    WorkflowStateResponse,
    WorkflowConfigResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/work-items", tags=["WorkItems"])


async def get_workflow_service(session: DatabaseDep) -> AsyncWorkflowService:
    """依赖注入：获取 AsyncWorkflowService 实例"""
    return AsyncWorkflowService(session)


WorkflowServiceDep = Annotated[AsyncWorkflowService, Depends(get_workflow_service)]


# ==================== 事项类型和状态管理 ====================

@router.get(
    "/types",
    response_model=List[WorkTypeResponse],
    summary="获取事项类型列表"
)
async def get_work_types(session: DatabaseDep):
    """获取系统中定义的所有业务事项类型"""
    from models import SysWorkType
    stmt = select(SysWorkType)
    result = await session.execute(stmt)
    work_types = result.scalars().all()
    return work_types


@router.get(
    "/states",
    response_model=List[WorkflowStateResponse],
    summary="获取流程状态列表"
)
async def get_workflow_states(session: DatabaseDep):
    """获取系统中定义的所有流程状态"""
    from models import SysWorkflowState
    stmt = select(SysWorkflowState)
    result = await session.execute(stmt)
    states = result.scalars().all()
    return states


@router.get(
    "/configs",
    response_model=List[WorkflowConfigResponse],
    summary="获取指定类型的所有流转配置",
    responses={404: {"model": ErrorResponse, "description": "类型不存在"}}
)
async def get_workflow_configs(
        session: DatabaseDep,
        type_code: str = Query(..., description="事项类型编码"),
):
    """获取指定事项类型的所有流转配置规则"""
    from models import SysWorkflowConfig
    stmt = select(SysWorkflowConfig).where(SysWorkflowConfig.type_code == type_code)
    result = await session.execute(stmt)
    configs = result.scalars().all()
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
        session: DatabaseDep,
        type_code: Optional[str] = Query(None, description="按类型筛选"),
        state: Optional[str] = Query(None, description="按状态筛选"),
        owner_id: Optional[int] = Query(None, description="按当前处理人筛选"),
        limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
        offset: int = Query(0, ge=0, description="分页偏移"),
):
    """查询业务事项列表，支持按类型、状态、处理人筛选"""
    stmt = select(BusWorkItem)

    if type_code:
        stmt = stmt.where(BusWorkItem.type_code == type_code)
    if state:
        stmt = stmt.where(BusWorkItem.current_state == state)
    if owner_id:
        stmt = stmt.where(BusWorkItem.current_owner_id == owner_id)

    stmt = stmt.order_by(desc(BusWorkItem.created_at)).offset(offset).limit(limit)

    result = await session.execute(stmt)
    items = result.scalars().all()
    return items


@router.get(
    "/{item_id}",
    response_model=WorkItemResponse,
    summary="获取事项详情",
    responses={404: {"model": ErrorResponse, "description": "事项不存在"}}
)
async def get_work_item(
        item_id: int,
        session: DatabaseDep
):
    """根据 ID 获取业务事项详情"""
    item = await session.get(BusWorkItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"事项 ID={item_id} 不存在")
    return item


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
        item_id: int,
        request: TransitionRequest,
        service: WorkflowServiceDep,
        session: DatabaseDep
):
    """
    执行状态流转
    """
    try:
        # 1. 先获取旧状态（用于返回响应）
        item_before = await session.get(BusWorkItem, item_id)
        if not item_before:
            raise HTTPException(status_code=404, detail=f"事项 ID={item_id} 不存在")
        old_state = item_before.current_state

        # 2. 调用 Service 执行流转（Service 内部负责事务提交）
        item = await service.handle_transition(
            work_item_id=item_id,
            action=request.action,
            operator_id=request.operator_id,
            form_data=request.form_data
        )

        return TransitionResponse(
            work_item_id=item.id,
            from_state=old_state,
            to_state=item.current_state,
            action=request.action,
            new_owner_id=item.current_owner_id,
            work_item=item
        )
    except WorkItemNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (InvalidTransitionError, MissingRequiredFieldError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{item_id}/logs",
    response_model=List[TransitionLogResponse],
    summary="获取流转历史"
)
async def get_transition_logs(
        item_id: int,
        session: DatabaseDep,
        limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
):
    """获取指定事项的所有流转日志（按时间倒序）"""
    from models import BusFlowLog

    # 检查事项是否存在
    item = await session.get(BusWorkItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"事项 ID={item_id} 不存在")

    stmt = select(BusFlowLog).where(
        BusFlowLog.work_item_id == item_id
    ).order_by(desc(BusFlowLog.created_at)).limit(limit)

    result = await session.execute(stmt)
    logs = result.scalars().all()
    return logs


@router.get(
    "/{item_id}/transitions",
    summary="获取可用的下一步流转"
)
async def get_available_transitions(
        item_id: int,
        session: DatabaseDep,
):
    """获取指定事项在当前状态下可以执行的所有流转动作"""
    from models import SysWorkflowConfig

    item = await session.get(BusWorkItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"事项 ID={item_id} 不存在")

    stmt = select(SysWorkflowConfig).where(
        SysWorkflowConfig.type_code == item.type_code,
        SysWorkflowConfig.from_state == item.current_state
    )
    result = await session.execute(stmt)
    configs = result.scalars().all()

    return {
        "item_id": item_id,
        "current_state": item.current_state,
        "available_transitions": [
            {
                "action": config.action,
                "to_state": config.to_state,
                "target_owner_strategy": config.target_owner_strategy,
                "required_fields": config.required_fields
            }
            for config in configs
        ]
    }
