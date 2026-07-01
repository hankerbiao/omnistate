"""执行计划 API 路由。

读写分离：
- PlanQueryServiceDep：纯读操作（列表、详情、统计）
- PlanCommandServiceDep：写操作（CRUD、派发、改派、结果回填）

权限策略：
- 读操作：execution_tasks:read
- 写操作：execution_tasks:write
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.modules.execution_plan.api.dependencies import (
    PlanCommandServiceDep,
    PlanQueryServiceDep,
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
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/execution-plans", tags=["ExecutionPlan"])

READ_DEP = [Depends(require_permission("execution_tasks:read"))]
WRITE_DEP = [Depends(require_permission("execution_tasks:write"))]


# ═══════════════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════════════

def _get_user_id(current_user: Dict[str, Any]) -> str:
    """从当前用户信息中提取 user_id。"""
    return current_user.get("user_id") or current_user.get("id") or ""


# ═══════════════════════════════════════════════════════════════════════
#  My Tasks — 计划条目查询（PlanQueryService）
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/items/my-items",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="获取当前用户的计划任务列表（My Tasks）",
    dependencies=READ_DEP,
)
async def list_my_plan_items(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    assignee_id: Optional[str] = Query(None, description="执行人 user_id，不传则默认当前用户"),
    limit: int = Query(200, ge=1, le=1000, description="返回条目数量上限"),
):
    """返回当前用户被指派的计划条目列表，对齐前端 PlanTask 结构。"""
    uid = assignee_id or _get_user_id(current_user)
    items = await query_service.list_my_items(uid, limit=limit)
    return APIResponse(data=items)


@router.get(
    "/items",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="查询计划条目列表（支持状态/计划筛选，不限执行人）",
    dependencies=READ_DEP,
)
async def list_plan_items(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = Query(None, description="按状态筛选: pending|running|done|fail"),
    plan_id: Optional[str] = Query(None, description="按计划ID筛选"),
    limit: int = Query(200, description="返回条目数量上限", ge=1, le=1000),
):
    """查询所有未删除计划的条目列表，支持按状态和计划ID过滤，不限制执行人。"""
    items = await query_service.list_items(status=status, plan_id=plan_id, limit=limit)
    return APIResponse(data=items)


@router.get(
    "/items/overview",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取所有计划的运行总览",
    dependencies=READ_DEP,
)
async def get_plan_overview(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """返回所有执行计划的统计摘要及运行中条目列表。"""
    overview = await query_service.get_overview()
    return APIResponse(data=overview)


@router.get(
    "/items/{item_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取单条计划条目详情",
    dependencies=READ_DEP,
)
async def get_plan_item(
    item_id: str,
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取计划内单条条目的详细信息（含结果）。"""
    try:
        item = await query_service.get_item(item_id)
        return APIResponse(data=item)
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  计划条目状态更新（PlanCommandService）
# ═══════════════════════════════════════════════════════════════════════

@router.put(
    "/plans/{plan_id}/items/{item_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="更新计划条目（状态/指派人等）",
    dependencies=WRITE_DEP,
)
async def update_plan_item(
    plan_id: str,
    item_id: str,
    data: UpdatePlanItemRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新计划条目的状态、指派人等字段。"""
    try:
        item = await command_service.update_item(
            plan_id=plan_id,
            item_id=item_id,
            data=data.model_dump(exclude_none=True),
        )
        return APIResponse(data=item)
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  手工结果回填（PlanCommandService / PlanQueryService）
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/items/{item_id}/result",
    response_model=APIResponse[Dict[str, Any]],
    summary="提交手工测试结果回填",
    dependencies=WRITE_DEP,
)
async def submit_manual_result(
    item_id: str,
    request: SubmitManualResultRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """提交手工用例的执行结果回填。"""
    try:
        actor_id = _get_user_id(current_user)
        result = await command_service.submit_result(
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
    dependencies=READ_DEP,
)
async def get_manual_result(
    item_id: str,
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取某个计划条目已有的手工回填结果。"""
    try:
        result = await query_service.get_result(item_id=item_id)
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/cases/{case_id}/execution-stats",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取测试用例的执行统计",
    dependencies=READ_DEP,
)
async def get_case_execution_stats(
    case_id: str,
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取测试用例的历史执行统计（手工+自动化）。"""
    stats = await query_service.get_case_execution_stats(case_id)
    return APIResponse(data=stats)


# ═══════════════════════════════════════════════════════════════════════
#  自动化下发（PlanCommandService）
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/items/{item_id}/dispatch",
    response_model=APIResponse[Dict[str, Any]],
    summary="单条自动化用例计划内下发",
    dependencies=WRITE_DEP,
)
async def dispatch_single_item(
    item_id: str,
    request: PlanItemDispatchRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """将计划内的单条自动化用例下发到执行引擎。"""
    try:
        actor_id = _get_user_id(current_user)
        result = await command_service.dispatch_item(
            item_id=item_id,
            request=request,
            actor_id=actor_id,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/{item_id}/cancel-execution",
    response_model=APIResponse[Dict[str, Any]],
    summary="取消自动化条目的执行",
    dependencies=WRITE_DEP,
)
async def cancel_item_execution(
    item_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """取消计划内自动化条目的执行：删除关联任务，恢复状态为 pending。"""
    try:
        actor_id = _get_user_id(current_user)
        result = await command_service.cancel_execution(
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
    dependencies=WRITE_DEP,
)
async def rerun_plan_item(
    item_id: str,
    request: PlanItemRerunRequest,
    command_service: PlanCommandServiceDep,
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
        result = await command_service.rerun_item(
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
    dependencies=WRITE_DEP,
)
async def batch_dispatch_items(
    request: BatchDispatchRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量下发计划内的自动化用例到执行引擎。"""
    try:
        actor_id = _get_user_id(current_user)
        results = await command_service.batch_dispatch(
            request=request,
            actor_id=actor_id,
        )
        return APIResponse(data=results)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/{item_id}/reassign",
    response_model=APIResponse[Dict[str, Any]],
    summary="改派计划条目执行人",
    dependencies=WRITE_DEP,
)
async def reassign_plan_item(
    item_id: str,
    request: ReassignRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """改派计划条目到其他执行人，操作会记录审计日志。"""
    try:
        actor_id = _get_user_id(current_user)
        result = await command_service.reassign_item(
            item_id=item_id,
            assignee_id=request.assignee_id,
            operator_id=actor_id,
            remark=request.remark,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  计划 CRUD（PlanCommandService 写 / PlanQueryService 读）
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/plans",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取执行计划列表（分页）",
    dependencies=READ_DEP,
)
async def list_plans(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = Query(None, description="按状态筛选: active|done"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """分页返回执行计划列表（不含条目详情）。"""
    plans = await query_service.list_plans(status=status, page=page, page_size=page_size)
    return APIResponse(data=plans)


@router.post(
    "/plans",
    response_model=APIResponse[Dict[str, Any]],
    status_code=201,
    summary="创建执行计划",
    dependencies=WRITE_DEP,
)
async def create_plan(
    request: CreatePlanRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建一个新的执行计划（不含条目）。"""
    try:
        actor_id = _get_user_id(current_user)
        plan = await command_service.create_plan(
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
    dependencies=READ_DEP,
)
async def get_plan_detail(
    plan_id: str,
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取执行计划的详细信息，包含所有计划条目。"""
    try:
        plan = await query_service.get_plan(plan_id=plan_id)
        return APIResponse(data=plan)
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/plans/{plan_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="更新执行计划",
    dependencies=WRITE_DEP,
)
async def update_plan(
    plan_id: str,
    request: UpdatePlanRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新执行计划的基本信息。"""
    try:
        plan = await command_service.update_plan(
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
    dependencies=WRITE_DEP,
)
async def delete_plan(
    plan_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """软删除执行计划及其所有条目。"""
    try:
        await command_service.delete_plan(plan_id=plan_id)
        return APIResponse(data={"plan_id": plan_id, "deleted": True})
    except Exception as exc:
        handle_service_error(exc)


# ═══════════════════════════════════════════════════════════════════════
#  计划条目管理（PlanCommandService）
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/plans/{plan_id}/items",
    status_code=201,
    summary="为计划添加条目",
    dependencies=WRITE_DEP,
)
async def add_plan_items(
    plan_id: str,
    request: AddPlanItemsRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """为已有执行计划添加测试用例条目。"""
    try:
        plan = await command_service.add_items(
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
    dependencies=WRITE_DEP,
)
async def delete_plan_item(
    plan_id: str,
    item_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """从执行计划中移除单个条目（软删除）。"""
    try:
        await command_service.delete_item(plan_id=plan_id, item_id=item_id)
        return APIResponse(data={"plan_id": plan_id, "item_id": item_id, "deleted": True})
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/plans/{plan_id}/items/batch-assignee",
    response_model=APIResponse[Dict[str, Any]],
    summary="批量更新计划条目执行人",
    dependencies=WRITE_DEP,
)
async def batch_update_assignee(
    plan_id: str,
    request: BatchUpdateAssigneeRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量更新执行计划条目的执行人（指派或取消指派）。"""
    try:
        result = await command_service.batch_update_assignee(
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
    dependencies=READ_DEP,
)
async def list_archived_items(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    assignee_id: Optional[str] = Query(None, description="执行人 user_id，不传则默认当前用户"),
    limit: int = Query(200, ge=1, le=1000, description="返回条目数量上限"),
):
    """返回当前用户已归档的计划条目列表。"""
    uid = assignee_id or _get_user_id(current_user)
    items = await query_service.list_archived_items(uid, limit=limit)
    return APIResponse(data=items)


@router.put(
    "/items/{item_id}/archive",
    response_model=APIResponse[Dict[str, Any]],
    summary="归档计划条目（收纳）",
    dependencies=WRITE_DEP,
)
async def archive_item(
    item_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """将计划条目标记为已归档（放入收纳箱）。"""
    try:
        actor_id = _get_user_id(current_user)
        await command_service.archive_item(item_id=item_id, actor_id=actor_id)
        return APIResponse(data={"item_id": item_id, "archived": True})
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/items/{item_id}/unarchive",
    response_model=APIResponse[Dict[str, Any]],
    summary="取消归档计划条目",
    dependencies=WRITE_DEP,
)
async def unarchive_item(
    item_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """将计划条目从收纳箱移回待处理。"""
    try:
        actor_id = _get_user_id(current_user)
        await command_service.unarchive_item(item_id=item_id, actor_id=actor_id)
        return APIResponse(data={"item_id": item_id, "archived": False})
    except Exception as exc:
        handle_service_error(exc)
