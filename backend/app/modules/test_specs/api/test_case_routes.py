"""测试用例 API 路由"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.application import (
    CreateTestCaseCommand,
    DeleteTestCaseCommand,
    LinkAutomationCaseCommand,
    TestCaseCommandService,
    UpdateTestCaseCommand,
)
from app.modules.workflow.application import OperationContext, WorkflowCommandService
from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission
from app.modules.test_specs.service import RequirementService, TestCaseService
from app.modules.test_specs.schemas import (
    CreateTestCaseRequest,
    UpdateTestCaseRequest,
    TestCaseResponse,
    LinkAutomationCaseRequest,
)

router = APIRouter(prefix="/test-cases", tags=["TestCases"])


def get_test_case_service() -> TestCaseService:
    """FastAPI 依赖：为每次请求提供服务实例。"""
    return TestCaseService()


TestCaseServiceDep = Annotated[TestCaseService, Depends(get_test_case_service)]


def get_requirement_service() -> RequirementService:
    """FastAPI 依赖：为命令服务提供需求服务实例。"""
    return RequirementService()


RequirementServiceDep = Annotated[RequirementService, Depends(get_requirement_service)]


def get_workflow_command_service() -> WorkflowCommandService:
    return WorkflowCommandService(AsyncWorkflowService())


WorkflowCommandServiceDep = Annotated[WorkflowCommandService, Depends(get_workflow_command_service)]


def get_test_case_command_service(
    test_case_service: TestCaseServiceDep,
    requirement_service: RequirementServiceDep,
    workflow_command_service: WorkflowCommandServiceDep,
) -> TestCaseCommandService:
    return TestCaseCommandService(test_case_service, requirement_service, workflow_command_service)


TestCaseCommandServiceDep = Annotated[TestCaseCommandService, Depends(get_test_case_command_service)]


def build_operation_context(current_user: dict) -> OperationContext:
    return OperationContext(
        actor_id=str(current_user["user_id"]),
        role_ids=[str(role_id) for role_id in current_user.get("role_ids", [])],
    )


@router.post(
    "",
    response_model=APIResponse[TestCaseResponse],
    status_code=201,
    summary="创建测试用例",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def create_test_case(
    request: CreateTestCaseRequest,
    command_service: TestCaseCommandServiceDep,
    current_user=Depends(get_current_user),
):
    """创建测试用例。

    说明：
    - 权限由路由依赖 `test_cases:write` 统一控制。
    - 请求字段直接透传到 Service，不做字段名转换。
    """
    try:
        data = await command_service.create_test_case(
            build_operation_context(current_user),
            CreateTestCaseCommand(payload=request.model_dump()),
        )
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")


@router.get(
    "/{case_id}",
    response_model=APIResponse[TestCaseResponse],
    summary="获取测试用例详情",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def get_test_case(
    case_id: str,
    service: TestCaseServiceDep,
):
    """按业务主键 case_id 查询单条用例。"""
    try:
        data = await service.get_test_case(case_id)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="test case not found")


@router.get(
    "",
    response_model=APIResponse[List[TestCaseResponse]],
    summary="查询测试用例列表",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def list_test_cases(
    service: TestCaseServiceDep,
    ref_req_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    reviewer_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """分页查询用例，支持按需求/状态/责任人等过滤。"""
    data = await service.list_test_cases(
        ref_req_id=ref_req_id,
        status=status,
        owner_id=owner_id,
        reviewer_id=reviewer_id,
        priority=priority,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.put(
    "/{case_id}",
    response_model=APIResponse[TestCaseResponse],
    summary="更新测试用例",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def update_test_case(
    case_id: str,
    request: UpdateTestCaseRequest,
    command_service: TestCaseCommandServiceDep,
    current_user=Depends(get_current_user),
):
    """更新测试用例（仅更新请求中显式提交字段）。"""
    try:
        data = await command_service.update_test_case(
            build_operation_context(current_user),
            UpdateTestCaseCommand(
                case_id=case_id,
                payload=request.model_dump(exclude_unset=True),
            ),
        )
        return APIResponse(data=data)
    except ValueError as e:
        if str(e) == "no fields to update":
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError as e:
        # 服务层会复用 KeyError 抛出「需求不存在」与「用例不存在」，这里做 HTTP 映射。
        if str(e) == "'requirement not found'":
            raise HTTPException(status_code=404, detail="requirement not found")
        raise HTTPException(status_code=404, detail="test case not found")


@router.delete(
    "/{case_id}",
    response_model=APIResponse[dict],
    summary="删除测试用例",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def delete_test_case(
    case_id: str,
    command_service: TestCaseCommandServiceDep,
    current_user=Depends(get_current_user),
):
    """删除用例（服务层执行逻辑删除）。"""
    try:
        await command_service.delete_test_case(
            build_operation_context(current_user),
            DeleteTestCaseCommand(case_id=case_id),
        )
        return APIResponse(data={"deleted": True})
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="test case not found")


@router.post(
    "/{case_id}/automation-link",
    response_model=APIResponse[TestCaseResponse],
    summary="关联自动化测试用例",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def link_automation_case(
    case_id: str,
    request: LinkAutomationCaseRequest,
    command_service: TestCaseCommandServiceDep,
    current_user=Depends(get_current_user),
):
    try:
        data = await command_service.link_automation_case(
            build_operation_context(current_user),
            LinkAutomationCaseCommand(
                case_id=case_id,
                auto_case_id=request.auto_case_id,
                version=request.version,
            ),
        )
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError as e:
        if str(e) == "'automation test case not found'":
            raise HTTPException(status_code=404, detail="automation test case not found")
        raise HTTPException(status_code=404, detail="test case not found")
