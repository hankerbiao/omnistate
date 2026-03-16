"""自动化测试用例 API 路由。"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.schemas import (
    AutomationTestCaseResponse,
    CreateAutomationTestCaseRequest,
)
from app.modules.test_specs.service import AutomationTestCaseService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission

router = APIRouter(prefix="/automation-test-cases", tags=["AutomationTestCases"])


def get_automation_test_case_service() -> AutomationTestCaseService:
    return AutomationTestCaseService()


AutomationTestCaseServiceDep = Annotated[
    AutomationTestCaseService,
    Depends(get_automation_test_case_service),
]


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
    """创建自动化测试用例库记录。"""
    try:
        data = await service.create_automation_test_case(request.model_dump())
        return APIResponse(data=data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get(
    "",
    response_model=APIResponse[List[AutomationTestCaseResponse]],
    summary="查询自动化测试用例列表",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def list_automation_test_cases(
    service: AutomationTestCaseServiceDep,
    framework: Optional[str] = Query(None),
    automation_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    maintainer_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """分页查询自动化测试用例列表。"""
    data = await service.list_automation_test_cases(
        framework=framework,
        automation_type=automation_type,
        status=status,
        maintainer_id=maintainer_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.get(
    "/{auto_case_id}",
    response_model=APIResponse[AutomationTestCaseResponse],
    summary="获取自动化测试用例详情",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def get_automation_test_case(
    auto_case_id: str,
    service: AutomationTestCaseServiceDep,
):
    """按业务编号获取自动化测试用例最新版本。"""
    try:
        data = await service.get_automation_test_case(auto_case_id)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="automation test case not found")
