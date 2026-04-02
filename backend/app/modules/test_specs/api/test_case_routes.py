"""测试用例 API 路由"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.api.dependencies import (
    TestCaseCommandServiceDep,
    TestCaseQueryServiceDep,
    build_operation_context,
)
from app.modules.test_specs.application import (
    CreateTestCaseCommand,
    DeleteTestCaseCommand,
    LinkAutomationCaseCommand,
    UpdateTestCaseCommand,
)
from app.modules.test_specs.schemas import (
    CreateTestCaseRequest,
    LinkAutomationCaseRequest,
    TestCaseResponse,
    UpdateTestCaseRequest,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/test-cases", tags=["TestCases"])


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
    query_service: TestCaseQueryServiceDep,
):
    try:
        data = await query_service.get_test_case(case_id)
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
    query_service: TestCaseQueryServiceDep,
    ref_req_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    reviewer_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await query_service.list_test_cases(
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
