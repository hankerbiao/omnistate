"""自动化测试用例 API 路由"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission
from app.modules.test_specs.service import AutomationTestCaseService
from app.modules.test_specs.schemas import (
    CreateAutomationTestCaseRequest,
    UpdateAutomationTestCaseRequest,
    AutomationTestCaseResponse,
)

router = APIRouter(prefix="/automation-test-cases", tags=["AutomationTestCases"])


def get_automation_test_case_service() -> AutomationTestCaseService:
    return AutomationTestCaseService()


AutomationTestCaseServiceDep = Annotated[AutomationTestCaseService, Depends(get_automation_test_case_service)]


@router.post(
    "",
    response_model=APIResponse[AutomationTestCaseResponse],
    status_code=201,
    summary="创建自动化测试用例",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def create_automation_test_case(
    request: CreateAutomationTestCaseRequest,
    service: AutomationTestCaseServiceDep,
):
    try:
        data = await service.create_automation_test_case(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/{auto_case_id}",
    response_model=APIResponse[AutomationTestCaseResponse],
    summary="获取自动化测试用例详情",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def get_automation_test_case(
    auto_case_id: str,
    service: AutomationTestCaseServiceDep,
    version: Optional[str] = Query(None, description="自动化用例版本，为空时返回最新版本"),
):
    try:
        data = await service.get_automation_test_case(auto_case_id=auto_case_id, version=version)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="automation test case not found")


@router.get(
    "",
    response_model=APIResponse[List[AutomationTestCaseResponse]],
    summary="查询自动化测试用例列表",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def list_automation_test_cases(
    service: AutomationTestCaseServiceDep,
    framework: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    maintainer_id: Optional[str] = Query(None),
    script_entity_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await service.list_automation_test_cases(
        framework=framework,
        status=status,
        tag=tag,
        maintainer_id=maintainer_id,
        script_entity_id=script_entity_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.put(
    "/{auto_case_id}",
    response_model=APIResponse[AutomationTestCaseResponse],
    summary="更新自动化测试用例",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def update_automation_test_case(
    auto_case_id: str,
    request: UpdateAutomationTestCaseRequest,
    service: AutomationTestCaseServiceDep,
    version: Optional[str] = Query(None, description="自动化用例版本，为空时更新最新版本"),
):
    payload = request.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="no fields to update")
    try:
        data = await service.update_automation_test_case(
            auto_case_id=auto_case_id,
            version=version,
            data=payload,
        )
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="automation test case not found")


@router.delete(
    "/{auto_case_id}",
    response_model=APIResponse[dict],
    summary="删除自动化测试用例",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def delete_automation_test_case(
    auto_case_id: str,
    service: AutomationTestCaseServiceDep,
    version: Optional[str] = Query(None, description="自动化用例版本，为空时删除最新版本"),
):
    try:
        await service.delete_automation_test_case(auto_case_id=auto_case_id, version=version)
        return APIResponse(data={"deleted": True})
    except KeyError:
        raise HTTPException(status_code=404, detail="automation test case not found")
