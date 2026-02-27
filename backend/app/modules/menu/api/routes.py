"""菜单管理 API。"""
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission, get_current_user
from app.modules.menu.service import MenuService
from app.modules.menu.schemas import (
    CreateMenuRequest,
    UpdateMenuRequest,
    MenuResponse,
    MyMenusResponse,
)

router = APIRouter(prefix="/menus", tags=["Menus"])


def get_menu_service() -> MenuService:
    return MenuService()


MenuServiceDep = Annotated[MenuService, Depends(get_menu_service)]


@router.post("", response_model=APIResponse[MenuResponse], summary="创建菜单")
async def create_menu(
    request: CreateMenuRequest,
    service: MenuServiceDep,
    _=Depends(require_permission("menu:write")),
):
    try:
        data = await service.create_menu(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=APIResponse[List[MenuResponse]], summary="查询菜单")
async def list_menus(
    service: MenuServiceDep,
    _=Depends(require_permission("menu:read")),
    is_active: Optional[bool] = Query(None),
    parent_menu_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    data = await service.list_menus(is_active, parent_menu_id, limit, offset)
    return APIResponse(data=data)


@router.get("/me", response_model=APIResponse[MyMenusResponse], summary="获取当前用户可见菜单")
async def get_my_menus(
    service: MenuServiceDep,
    current_user=Depends(get_current_user),
):
    data = await service.list_visible_menus_for_user(current_user["user_id"])
    return APIResponse(data=data)


@router.get("/{menu_id}", response_model=APIResponse[MenuResponse], summary="菜单详情")
async def get_menu(
    menu_id: str,
    service: MenuServiceDep,
    _=Depends(require_permission("menu:read")),
):
    try:
        data = await service.get_menu(menu_id)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="menu not found")


@router.put("/{menu_id}", response_model=APIResponse[MenuResponse], summary="更新菜单")
async def update_menu(
    menu_id: str,
    request: UpdateMenuRequest,
    service: MenuServiceDep,
    _=Depends(require_permission("menu:write")),
):
    payload = request.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="no fields to update")
    try:
        data = await service.update_menu(menu_id, payload)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="menu not found")


@router.delete("/{menu_id}", response_model=APIResponse[dict], summary="删除菜单")
async def delete_menu(
    menu_id: str,
    service: MenuServiceDep,
    _=Depends(require_permission("menu:write")),
):
    try:
        await service.delete_menu(menu_id)
        return APIResponse(data={"deleted": True})
    except KeyError:
        raise HTTPException(status_code=404, detail="menu not found")
