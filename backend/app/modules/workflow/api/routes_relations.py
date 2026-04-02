from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.modules.workflow.api.dependencies import WorkflowQueryServiceDep
from app.modules.workflow.domain.exceptions import WorkItemNotFoundError
from app.modules.workflow.schemas.work_item import WorkItemResponse
from app.shared.api.schemas.base import APIResponse
from app.shared.api.schemas.error import ErrorResponse
from app.shared.auth import require_permission

router = APIRouter()


@router.get(
    "/{item_id}/test-cases",
    response_model=APIResponse[list[WorkItemResponse]],
    summary="获取某个需求下的测试用例列表",
    dependencies=[Depends(require_permission("work_items:read"))],
    responses={404: {"model": APIResponse[ErrorResponse], "description": "需求不存在"}},
)
async def list_test_cases_for_requirement(item_id: str, service: WorkflowQueryServiceDep):
    try:
        return APIResponse(data=await service.list_test_cases_for_requirement(item_id))
    except WorkItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/{item_id}/requirement",
    response_model=APIResponse[Optional[WorkItemResponse]],
    summary="获取测试用例所属的需求（如果存在）",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def get_requirement_for_test_case(item_id: str, service: WorkflowQueryServiceDep):
    try:
        return APIResponse(data=await service.get_requirement_for_test_case(item_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
