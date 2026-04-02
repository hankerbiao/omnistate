"""测试需求 API 路由"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.application import (
    CreateRequirementCommand,
    DeleteRequirementCommand,
    RequirementCommandService,
    TestSpecsWorkflowProjectionHook,
    UpdateRequirementCommand,
)
from app.modules.workflow.application import (
    AsyncWorkflowServiceAdapter,
    OperationContext,
    WorkflowCommandService,
)
from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission
from app.modules.test_specs.service import RequirementService
from app.modules.test_specs.schemas import (
    CreateRequirementRequest,
    UpdateRequirementRequest,
    RequirementResponse,
)

router = APIRouter(prefix="/requirements", tags=["Requirements"])


def get_workflow_service() -> AsyncWorkflowService:
    return AsyncWorkflowService()


WorkflowServiceDep = Annotated[AsyncWorkflowService, Depends(get_workflow_service)]


def get_requirement_service(workflow_service: WorkflowServiceDep) -> RequirementService:
    """FastAPI 依赖：为每次请求提供服务实例。"""
    return RequirementService(workflow_gateway=AsyncWorkflowServiceAdapter(workflow_service))


RequirementServiceDep = Annotated[RequirementService, Depends(get_requirement_service)]


def get_workflow_projection_hook() -> TestSpecsWorkflowProjectionHook:
    return TestSpecsWorkflowProjectionHook()


WorkflowProjectionHookDep = Annotated[TestSpecsWorkflowProjectionHook, Depends(get_workflow_projection_hook)]


def get_workflow_command_service(
    workflow_service: WorkflowServiceDep,
    projection_hook: WorkflowProjectionHookDep,
) -> WorkflowCommandService:
    return WorkflowCommandService(workflow_service, mutation_hooks=[projection_hook])


WorkflowCommandServiceDep = Annotated[WorkflowCommandService, Depends(get_workflow_command_service)]


def get_requirement_command_service(
    requirement_service: RequirementServiceDep,
    workflow_command_service: WorkflowCommandServiceDep,
) -> RequirementCommandService:
    return RequirementCommandService(requirement_service, workflow_command_service)


RequirementCommandServiceDep = Annotated[
    RequirementCommandService, Depends(get_requirement_command_service)
]


def build_operation_context(current_user: dict) -> OperationContext:
    return OperationContext(
        actor_id=str(current_user["user_id"]),
        role_ids=[str(role_id) for role_id in current_user.get("role_ids", [])],
    )


@router.post(
    "",
    response_model=APIResponse[RequirementResponse],
    status_code=201,
    summary="创建测试需求",
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def create_requirement(
    request: CreateRequirementRequest,
    command_service: RequirementCommandServiceDep,
    current_user=Depends(get_current_user),
):
    """创建需求。

    重要说明：
    - 权限由路由依赖 `requirements:write` 统一控制。
    - req_id 字段必须由后端自动生成，前端不应提供此字段。
    - 即使前端传递了 req_id，服务层也会忽略并重新生成。
    - `request.model_dump()` 直接透传到 Service，避免字段重命名转换。
    """
    try:
        data = await command_service.create_requirement(
            build_operation_context(current_user),
            CreateRequirementCommand(payload=request.model_dump()),
        )
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/{req_id}",
    response_model=APIResponse[RequirementResponse],
    summary="获取测试需求详情",
    dependencies=[Depends(require_permission("requirements:read"))],
)
async def get_requirement(
    req_id: str,
    service: RequirementServiceDep,
):
    """按业务主键 req_id 查询单条需求。"""
    try:
        data = await service.get_requirement(req_id)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")


@router.get(
    "",
    response_model=APIResponse[List[RequirementResponse]],
    summary="查询测试需求列表",
    dependencies=[Depends(require_permission("requirements:read"))],
)
async def list_requirements(
    service: RequirementServiceDep,
    status: Optional[str] = Query(None),
    tpm_owner_id: Optional[str] = Query(None),
    manual_dev_id: Optional[str] = Query(None),
    auto_dev_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """分页查询需求，支持按状态/负责人过滤。"""
    data = await service.list_requirements(
        status=status,
        tpm_owner_id=tpm_owner_id,
        manual_dev_id=manual_dev_id,
        auto_dev_id=auto_dev_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.put(
    "/{req_id}",
    response_model=APIResponse[RequirementResponse],
    summary="更新测试需求",
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def update_requirement(
    req_id: str,
    request: UpdateRequirementRequest,
    command_service: RequirementCommandServiceDep,
    current_user=Depends(get_current_user),
):
    """更新需求（仅更新请求中显式提交字段）。"""
    try:
        data = await command_service.update_requirement(
            build_operation_context(current_user),
            UpdateRequirementCommand(
                req_id=req_id,
                payload=request.model_dump(exclude_unset=True),
            ),
        )
        return APIResponse(data=data)
    except ValueError as e:
        if str(e) == "no fields to update":
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")


@router.delete(
    "/{req_id}",
    response_model=APIResponse[dict],
    summary="删除测试需求",
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def delete_requirement(
    req_id: str,
    command_service: RequirementCommandServiceDep,
    current_user=Depends(get_current_user),
):
    """删除需求（服务层执行逻辑删除与关联校验）。"""
    try:
        await command_service.delete_requirement(
            build_operation_context(current_user),
            DeleteRequirementCommand(req_id=req_id),
        )
        return APIResponse(data={"deleted": True})
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")
