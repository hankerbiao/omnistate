from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.modules.auth.api.dependencies import PermissionServiceDep
from app.modules.auth.schemas import PermissionResponse
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter()


@router.get(
    "/permissions",
    response_model=APIResponse[list[PermissionResponse]],
    summary="查询静态权限列表",
)
async def list_permissions(
    service: PermissionServiceDep,
    _=Depends(get_current_user),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return APIResponse(data=await service.list_permissions(limit=limit, offset=offset))
