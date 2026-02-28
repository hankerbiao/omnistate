"""测试用例 API 路由"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission
from app.modules.test_specs.service import TestCaseService
from app.modules.test_specs.schemas import (
    CreateTestCaseRequest,
    UpdateTestCaseRequest,
    TestCaseResponse,
)

router = APIRouter(prefix="/test-cases", tags=["TestCases"])


def get_test_case_service() -> TestCaseService:
    return TestCaseService()


TestCaseServiceDep = Annotated[TestCaseService, Depends(get_test_case_service)]


@router.post(
    "",
    response_model=APIResponse[TestCaseResponse],
    status_code=201,
    summary="创建测试用例",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def create_test_case(
    request: CreateTestCaseRequest,
    service: TestCaseServiceDep,
):
    try:
        data = await service.create_test_case(request.model_dump())
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
    service: TestCaseServiceDep,
):
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        data = await service.update_test_case(case_id, payload)
        return APIResponse(data=data)
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
    service: TestCaseServiceDep,
):
    try:
        await service.delete_test_case(case_id)
        return APIResponse(data={"deleted": True})
    except KeyError:
        raise HTTPException(status_code=404, detail="test case not found")
