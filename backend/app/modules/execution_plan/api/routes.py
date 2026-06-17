"""执行计划 API 路由（My Tasks 所需端点）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.modules.execution_plan.api.dependencies import (
    ExecutionPlanServiceDep,
    SequenceIdServiceDep,
)
from app.modules.execution_plan.api.exception_handler import handle_service_error
from app.modules.execution_plan.schemas.execution_plan import (
    AddPlanItemsRequest,
    BatchDispatchRequest,
    BatchUpdateAssigneeRequest,
    CreatePlanRequest,
    PlanItemDispatchRequest,
    PlanItemRerunRequest,
    ReassignRequest,
    SubmitManualResultRequest,
    UpdatePlanItemRequest,
    UpdatePlanRequest,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter(prefix="/execution-plans", tags=["ExecutionPlan"])


# ═══════════════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════════════

def _get_user_id(current_user: Dict[str, Any]) -> str:
    """从当前用户信息中提取 user_id。"""
    return current_user.get("user_id") or current_user.get("id") or ""


# ═══════════════════════════════════════════════════════════════════════
#  My Tasks — 计划条目查询
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/items/my-items",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="获取当前用户的计划任务列表（My Tasks）",
)
async def list_my_plan_items(
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    assignee_id: Optional[str] = Query(None, description="执行人 user_id，不传则默认当前用户"),
):
    """返回当前用户被指派的计划条目列表，对齐前端 PlanTask 结构。"""
    uid = assignee_id or _get_user_id(current_user)
    items = await service.list_my_items(uid)
    return APIResponse(data=items)


@router.get(
    "/items",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="查询计划条目列表（支持状态/计划筛选，不限执行人）",
)
async def list_plan_items(
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = Query(None, description="按状态筛选: pending|running|done|fail"),
    plan_id: Optional[str] = Query(None, description="按计划ID筛选"),
    limit: int = Query(200, description="返回条目数量上限", ge=1, le=1000),
):
    """查询所有未删除计划的条目列表，支持按状态和计划ID过滤，不限制执行人。"""
    items = await service.list_items(status=status, plan_id=plan_id, limit=limit)
    return APIResponse(data=items)


@router.get(
    "/items/overview",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取所有计划的运行总览",
)
async def get_plan_overview(
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """返回所有执行计划的统计摘要及运行中条目列表。"""
    overview = await service.get_overview()
    return APIResponse(data=overview)


@router.get(
    "/items/{item_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取单条计划条目详情",
)
async def get_plan_item(
    item_id: str,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取计划内单条条目的详细信息（含结果）。"""
    try:
        item = await service.get_item(item_id)
        return APIResponse(data=item)
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  计划条目状态更新
# ═══════════════════════════════════════════════════════════════════════

@router.put(
    "/plans/{plan_id}/items/{item_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="更新计划条目（状态/指派人等）",
)
async def update_plan_item(
    plan_id: str,
    item_id: str,
    data: UpdatePlanItemRequest,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新计划条目的状态、指派人等字段。"""
    try:
        item = await service.update_item(
            plan_id=plan_id,
            item_id=item_id,
            data=data.model_dump(exclude_none=True),
        )
        return APIResponse(data=item)
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  手工结果回填
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/items/{item_id}/result",
    response_model=APIResponse[Dict[str, Any]],
    summary="提交手工测试结果回填",
)
async def submit_manual_result(
    item_id: str,
    request: SubmitManualResultRequest,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """提交手工用例的执行结果回填。"""
    try:
        actor_id = _get_user_id(current_user)
        result = await service.submit_result(
            item_id=item_id,
            request=request,
            actor_id=actor_id,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/items/{item_id}/result",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取已有的手工结果回填",
)
async def get_manual_result(
    item_id: str,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取某个计划条目已有的手工回填结果。"""
    try:
        result = await service.get_result(item_id=item_id)
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/cases/{case_id}/execution-stats",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取测试用例的执行统计",
)
async def get_case_execution_stats(
    case_id: str,
    service: ExecutionPlanServiceDep,
):
    """获取测试用例的历史执行统计（手工+自动化）。"""
    stats = await service.get_case_execution_stats(case_id)
    return APIResponse(data=stats)


# ═══════════════════════════════════════════════════════════════════════
#  自动化下发
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/items/{item_id}/dispatch",
    response_model=APIResponse[Dict[str, Any]],
    summary="单条自动化用例计划内下发",
)
async def dispatch_single_item(
    item_id: str,
    request: PlanItemDispatchRequest,
    service: ExecutionPlanServiceDep,
    sequence_service: SequenceIdServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """将计划内的单条自动化用例下发到执行引擎。"""
    try:
        actor_id = _get_user_id(current_user)
        result = await service.dispatch_item(
            item_id=item_id,
            request=request,
            actor_id=actor_id,
            sequence_service=sequence_service,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/{item_id}/cancel-execution",
    response_model=APIResponse[Dict[str, Any]],
    summary="取消自动化条目的执行",
)
async def cancel_item_execution(
    item_id: str,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """取消计划内自动化条目的执行：删除关联任务，恢复状态为 pending。"""
    try:
        actor_id = _get_user_id(current_user)
        result = await service.cancel_execution(
            item_id=item_id,
            actor_id=actor_id,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/{item_id}/rerun",
    response_model=APIResponse[Dict[str, Any]],
    status_code=201,
    summary="重新执行计划条目",
)
async def rerun_plan_item(
    item_id: str,
    request: PlanItemRerunRequest,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """重新执行计划条目（支持可选执行人变更）。

    对所有条目：仅重置状态为 pending，不自动下发到执行引擎。
    - 自动化条目：同时清空 execution_task_id 关联。
    - 如果提供 assignee_id，会先更新执行人再重置状态。
    - 用户需手动点击"执行"按钮触发实际下发。
    """
    try:
        actor_id = _get_user_id(current_user)
        result = await service.rerun_item(
            item_id=item_id,
            actor_id=actor_id,
            request=request,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/batch-dispatch",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="批量下发自动化用例",
)
async def batch_dispatch_items(
    request: BatchDispatchRequest,
    service: ExecutionPlanServiceDep,
    sequence_service: SequenceIdServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量下发计划内的自动化用例到执行引擎。"""
    try:
        actor_id = _get_user_id(current_user)
        results = await service.batch_dispatch(
            request=request,
            actor_id=actor_id,
            sequence_service=sequence_service,
        )
        return APIResponse(data=results)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/{item_id}/reassign",
    response_model=APIResponse[Dict[str, Any]],
    summary="改派计划条目执行人",
)
async def reassign_plan_item(
    item_id: str,
    request: ReassignRequest,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """改派计划条目到其他执行人，操作会记录审计日志。"""
    try:
        actor_id = _get_user_id(current_user)
        result = await service.reassign_item(
            item_id=item_id,
            assignee_id=request.assignee_id,
            operator_id=actor_id,
            remark=request.remark,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  计划 CRUD
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/plans",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="获取执行计划列表",
)
async def list_plans(
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = Query(None, description="按状态筛选: active|done"),
):
    """返回所有执行计划列表（不含条目详情）。"""
    plans = await service.list_plans(status=status)
    return APIResponse(data=plans)


@router.post(
    "/plans",
    response_model=APIResponse[Dict[str, Any]],
    status_code=201,
    summary="创建执行计划",
)
async def create_plan(
    request: CreatePlanRequest,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建一个新的执行计划（不含条目）。"""
    try:
        actor_id = _get_user_id(current_user)
        plan = await service.create_plan(
            data=request.model_dump(exclude_none=True),
            actor_id=actor_id,
        )
        return APIResponse(data=plan)
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/plans/{plan_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取执行计划详情（含条目列表）",
)
async def get_plan_detail(
    plan_id: str,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取执行计划的详细信息，包含所有计划条目。"""
    try:
        plan = await service.get_plan(plan_id=plan_id)
        return APIResponse(data=plan)
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/plans/{plan_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="更新执行计划",
)
async def update_plan(
    plan_id: str,
    request: UpdatePlanRequest,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新执行计划的基本信息。"""
    try:
        plan = await service.update_plan(
            plan_id=plan_id,
            data=request.model_dump(exclude_none=True),
        )
        return APIResponse(data=plan)
    except Exception as exc:
        handle_service_error(exc)


@router.delete(
    "/plans/{plan_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="删除执行计划（软删除）",
)
async def delete_plan(
    plan_id: str,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """软删除执行计划及其所有条目。"""
    try:
        await service.delete_plan(plan_id=plan_id)
        return APIResponse(data={"plan_id": plan_id, "deleted": True})
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  计划条目管理（仅添加和删除，创建完成后不可编辑）
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/plans/{plan_id}/items",
    status_code=201,
    summary="为计划添加条目",
)
async def add_plan_items(
    plan_id: str,
    request: AddPlanItemsRequest,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """为已有执行计划添加测试用例条目。"""
    try:
        plan = await service.add_items(
            plan_id=plan_id,
            items_data=[item.model_dump() for item in request.items],
        )
        return APIResponse(data=plan)
    except Exception as exc:
        handle_service_error(exc)


@router.delete(
    "/plans/{plan_id}/items/{item_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="从计划中移除条目（软删除）",
)
async def delete_plan_item(
    plan_id: str,
    item_id: str,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """从执行计划中移除单个条目（软删除）。"""
    try:
        await service.delete_item(plan_id=plan_id, item_id=item_id)
        return APIResponse(data={"plan_id": plan_id, "item_id": item_id, "deleted": True})
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/plans/{plan_id}/items/batch-assignee",
    response_model=APIResponse[Dict[str, Any]],
    summary="批量更新计划条目执行人",
)
async def batch_update_assignee(
    plan_id: str,
    request: BatchUpdateAssigneeRequest,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量更新执行计划条目的执行人（指派或取消指派）。"""
    try:
        result = await service.batch_update_assignee(
            plan_id=plan_id,
            item_ids=request.item_ids,
            assignee_id=request.assignee_id,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  收纳箱（Archive Box）
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/items/archived",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="获取已归档的计划任务列表（收纳箱）",
)
async def list_archived_items(
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    assignee_id: Optional[str] = Query(None, description="执行人 user_id，不传则默认当前用户"),
):
    """返回当前用户已归档的计划条目列表。"""
    uid = assignee_id or _get_user_id(current_user)
    items = await service.list_archived_items(uid)
    return APIResponse(data=items)


@router.put(
    "/items/{item_id}/archive",
    response_model=APIResponse[Dict[str, Any]],
    summary="归档计划条目（收纳）",
)
async def archive_item(
    item_id: str,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """将计划条目标记为已归档（放入收纳箱）。"""
    try:
        actor_id = _get_user_id(current_user)
        await service.archive_item(item_id=item_id, actor_id=actor_id)
        return APIResponse(data={"item_id": item_id, "archived": True})
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/items/{item_id}/unarchive",
    response_model=APIResponse[Dict[str, Any]],
    summary="取消归档计划条目",
)
async def unarchive_item(
    item_id: str,
    service: ExecutionPlanServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """将计划条目从收纳箱移回待处理。"""
    try:
        actor_id = _get_user_id(current_user)
        await service.unarchive_item(item_id=item_id, actor_id=actor_id)
        return APIResponse(data={"item_id": item_id, "archived": False})
    except Exception as exc:
        handle_service_error(exc)
