from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.auth.api.dependencies import NavigationAccessServiceDep, require_admin_user
from app.modules.auth.schemas import (
    CreateNavigationPageRequest,
    NavigationPageResponse,
    UpdateNavigationPageRequest,
)
from app.modules.auth.service import NavigationPageNotFoundError
from app.shared.api.schemas.base import APIResponse

router = APIRouter()


@router.get(
    "/admin/navigation/pages",
    response_model=APIResponse[list[NavigationPageResponse]],
    summary="获取系统导航页面定义（管理员）",
)
async def list_navigation_pages(
    service: NavigationAccessServiceDep,
    _=Depends(require_admin_user),
    include_inactive: bool = Query(True, description="是否包含未启用页面"),
):
    data = await service.list_navigation_pages(include_inactive=include_inactive)
    return APIResponse(data=[NavigationPageResponse(**item) for item in data])


@router.get(
    "/admin/navigation/pages/{view}",
    response_model=APIResponse[NavigationPageResponse],
    summary="获取导航页面定义（管理员）",
)
async def get_navigation_page(
    view: str,
    service: NavigationAccessServiceDep,
    _=Depends(require_admin_user),
):
    try:
        data = await service.get_navigation_page(view)
        return APIResponse(data=NavigationPageResponse(**data))
    except NavigationPageNotFoundError:
        raise HTTPException(status_code=404, detail="navigation page not found")


@router.post(
    "/admin/navigation/pages",
    response_model=APIResponse[NavigationPageResponse],
    status_code=201,
    summary="创建导航页面（管理员）",
)
async def create_navigation_page(
    request: CreateNavigationPageRequest,
    service: NavigationAccessServiceDep,
    _=Depends(require_admin_user),
):
    try:
        data = await service.create_navigation_page(request.model_dump())
        return APIResponse(data=NavigationPageResponse(**data))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.put(
    "/admin/navigation/pages/{view}",
    response_model=APIResponse[NavigationPageResponse],
    summary="更新导航页面（管理员）",
)
async def update_navigation_page(
    view: str,
    request: UpdateNavigationPageRequest,
    service: NavigationAccessServiceDep,
    _=Depends(require_admin_user),
):
    payload = request.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="no fields to update")
    try:
        data = await service.update_navigation_page(view, payload)
        return APIResponse(data=NavigationPageResponse(**data))
    except NavigationPageNotFoundError:
        raise HTTPException(status_code=404, detail="navigation page not found")


@router.delete(
    "/admin/navigation/pages/{view}",
    response_model=APIResponse[dict],
    summary="删除导航页面（管理员）",
)
async def delete_navigation_page(
    view: str,
    service: NavigationAccessServiceDep,
    _=Depends(require_admin_user),
):
    try:
        return APIResponse(data=await service.delete_navigation_page(view))
    except NavigationPageNotFoundError:
        raise HTTPException(status_code=404, detail="navigation page not found")
