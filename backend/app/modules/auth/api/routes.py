"""RBAC API 路由

AI 友好注释说明：
- 这里只处理 HTTP 参数解析与错误映射。
- 业务规则放在 Service 层。
- ADMIN 权限控制建议以依赖注入的方式加入（此处先保留接口）。
"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.shared.api.schemas.base import APIResponse
from app.shared.auth import create_access_token, get_current_user
from app.shared.auth import require_permission, require_any_permission
from app.modules.auth.service import (
    RbacService,
    UserNotFoundError,
    RoleNotFoundError,
    PermissionNotFoundError,
)
from app.modules.auth.schemas import (
    CreateUserRequest,
    UpdateUserRequest,
    UpdateUserRolesRequest,
    UpdateUserPasswordRequest,
    ChangePasswordRequest,
    LoginRequest,
    UserResponse,
    LoginResponse,
    MePermissionsResponse,
    NavigationPageResponse,
    UserNavigationResponse,
    UpdateUserNavigationRequest,
    CreateRoleRequest,
    UpdateRoleRequest,
    UpdateRolePermissionsRequest,
    RoleResponse,
    CreatePermissionRequest,
    UpdatePermissionRequest,
    PermissionResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_rbac_service() -> RbacService:
    """FastAPI 依赖：为每个请求创建 Service 实例"""
    return RbacService()


RbacServiceDep = Annotated[RbacService, Depends(get_rbac_service)]


def _is_admin_user(current_user: dict) -> bool:
    role_ids = current_user.get("role_ids", [])
    return any("ADMIN" in str(role_id).upper() for role_id in role_ids)


async def require_admin_user(current_user=Depends(get_current_user)):
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="admin only")
    return current_user


# ===== Users =====

@router.post("/users", response_model=APIResponse[UserResponse], status_code=201, summary="创建用户")
async def create_user(
    request: CreateUserRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("users:write")),
):
    """创建用户（可包含角色绑定）"""
    try:
        data = await service.create_user(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")


@router.post(
    "/login",
    response_model=APIResponse[LoginResponse],
    summary="用户登录",
)
async def login(
    request: LoginRequest,
    service: RbacServiceDep,
):
    """登录并返回 JWT"""
    try:
        user = await service.authenticate_user(request.user_id, request.password)
        token = create_access_token(user["user_id"])
        return APIResponse(data=LoginResponse(access_token=token, user=UserResponse(**user)))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid credentials")


@router.get("/users/{user_id}", response_model=APIResponse[UserResponse], summary="获取用户详情")
async def get_user(
    user_id: str,
    service: RbacServiceDep,
    _=Depends(require_any_permission(["users:read", "work_items:read"])),
):
    """根据 user_id 获取用户详情"""
    try:
        data = await service.get_user(user_id)
        return APIResponse(data=data)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.get("/users", response_model=APIResponse[List[UserResponse]], summary="查询用户列表")
async def list_users(
    service: RbacServiceDep,
    _=Depends(require_any_permission(["users:read", "work_items:read"])),
    status: Optional[str] = Query(None),
    role_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """查询用户列表，支持按状态或角色过滤"""
    data = await service.list_users(status=status, role_id=role_id, limit=limit, offset=offset)
    return APIResponse(data=data)


@router.put("/users/{user_id}", response_model=APIResponse[UserResponse], summary="更新用户信息")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("users:write")),
):
    """更新用户基础信息（不包含角色）"""
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        data = await service.update_user(user_id, payload)
        return APIResponse(data=data)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.patch(
    "/users/{user_id}/roles",
    response_model=APIResponse[UserResponse],
    summary="更新用户角色",
)
async def update_user_roles(
    user_id: str,
    request: UpdateUserRolesRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("users:write")),
):
    """更新用户角色（管理员操作）"""
    try:
        data = await service.update_user_roles(user_id, request.role_ids)
        return APIResponse(data=data)
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.patch(
    "/users/{user_id}/password",
    response_model=APIResponse[UserResponse],
    summary="重置用户密码",
)
async def update_user_password(
    user_id: str,
    request: UpdateUserPasswordRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("users:write")),
):
    """重置用户密码（管理员操作）"""
    try:
        data = await service.update_user_password(user_id, request.new_password)
        return APIResponse(data=data)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.post(
    "/users/me/password",
    response_model=APIResponse[UserResponse],
    summary="用户自助修改密码",
)
async def change_my_password(
    request: ChangePasswordRequest,
    service: RbacServiceDep,
    current_user=Depends(get_current_user),
):
    """用户自助修改密码（需要旧密码）"""
    try:
        data = await service.change_password(
            current_user["user_id"],
            request.old_password,
            request.new_password,
        )
        return APIResponse(data=data)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid credentials")


@router.get(
    "/users/me/permissions",
    response_model=APIResponse[MePermissionsResponse],
    summary="获取当前用户权限",
)
async def get_my_permissions(
    service: RbacServiceDep,
    current_user=Depends(get_current_user),
):
    """返回当前登录用户的角色与有效权限（并集）。"""
    try:
        data = await service.get_effective_permissions(current_user["user_id"])
        return APIResponse(data=MePermissionsResponse(**data))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.get(
    "/users/me/navigation",
    response_model=APIResponse[UserNavigationResponse],
    summary="获取当前用户导航访问权限",
)
async def get_my_navigation(
    service: RbacServiceDep,
    current_user=Depends(get_current_user),
):
    """返回当前登录用户可访问的导航页面。"""
    try:
        data = await service.get_user_navigation(current_user["user_id"])
        return APIResponse(data=UserNavigationResponse(**data))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.get(
    "/admin/navigation/pages",
    response_model=APIResponse[List[NavigationPageResponse]],
    summary="获取系统导航页面定义（管理员）",
)
async def list_navigation_pages(
    service: RbacServiceDep,
    _=Depends(require_admin_user),
):
    data = await service.list_navigation_pages()
    return APIResponse(data=[NavigationPageResponse(**item) for item in data])


@router.get(
    "/admin/users/{user_id}/navigation",
    response_model=APIResponse[UserNavigationResponse],
    summary="获取用户导航访问权限（管理员）",
)
async def get_user_navigation(
    user_id: str,
    service: RbacServiceDep,
    _=Depends(require_admin_user),
):
    try:
        data = await service.get_user_navigation(user_id)
        return APIResponse(data=UserNavigationResponse(**data))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.put(
    "/admin/users/{user_id}/navigation",
    response_model=APIResponse[UserNavigationResponse],
    summary="更新用户导航访问权限（管理员）",
)
async def update_user_navigation(
    user_id: str,
    request: UpdateUserNavigationRequest,
    service: RbacServiceDep,
    _=Depends(require_admin_user),
):
    try:
        data = await service.update_user_navigation(user_id, request.allowed_nav_views)
        return APIResponse(data=UserNavigationResponse(**data))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== Roles =====

@router.post("/roles", response_model=APIResponse[RoleResponse], status_code=201, summary="创建角色")
async def create_role(
    request: CreateRoleRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("roles:write")),
):
    """创建角色并绑定权限"""
    try:
        data = await service.create_role(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionNotFoundError:
        raise HTTPException(status_code=404, detail="permission not found")


@router.get("/roles/{role_id}", response_model=APIResponse[RoleResponse], summary="获取角色详情")
async def get_role(
    role_id: str,
    service: RbacServiceDep,
    _=Depends(require_permission("roles:read")),
):
    """获取角色详情"""
    try:
        data = await service.get_role(role_id)
        return APIResponse(data=data)
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")


@router.get("/roles", response_model=APIResponse[List[RoleResponse]], summary="查询角色列表")
async def list_roles(
    service: RbacServiceDep,
    _=Depends(require_permission("roles:read")),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """查询角色列表"""
    data = await service.list_roles(limit=limit, offset=offset)
    return APIResponse(data=data)


@router.put("/roles/{role_id}", response_model=APIResponse[RoleResponse], summary="更新角色信息")
async def update_role(
    role_id: str,
    request: UpdateRoleRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("roles:write")),
):
    """更新角色信息（不包含权限）"""
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        data = await service.update_role(role_id, payload)
        return APIResponse(data=data)
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")


@router.patch(
    "/roles/{role_id}/permissions",
    response_model=APIResponse[RoleResponse],
    summary="更新角色权限",
)
async def update_role_permissions(
    role_id: str,
    request: UpdateRolePermissionsRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("roles:write")),
):
    """更新角色权限（管理员操作）"""
    try:
        data = await service.update_role_permissions(role_id, request.permission_ids)
        return APIResponse(data=data)
    except PermissionNotFoundError:
        raise HTTPException(status_code=404, detail="permission not found")
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")


# ===== Permissions =====

@router.post(
    "/permissions",
    response_model=APIResponse[PermissionResponse],
    status_code=201,
    summary="创建权限",
)
async def create_permission(
    request: CreatePermissionRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("permissions:write")),
):
    """创建权限"""
    try:
        data = await service.create_permission(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/permissions/{perm_id}",
    response_model=APIResponse[PermissionResponse],
    summary="获取权限详情",
)
async def get_permission(
    perm_id: str,
    service: RbacServiceDep,
    _=Depends(require_permission("permissions:read")),
):
    """获取权限详情"""
    try:
        data = await service.get_permission(perm_id)
        return APIResponse(data=data)
    except PermissionNotFoundError:
        raise HTTPException(status_code=404, detail="permission not found")


@router.get(
    "/permissions",
    response_model=APIResponse[List[PermissionResponse]],
    summary="查询权限列表",
)
async def list_permissions(
    service: RbacServiceDep,
    _=Depends(require_permission("permissions:read")),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """查询权限列表"""
    data = await service.list_permissions(limit=limit, offset=offset)
    return APIResponse(data=data)


@router.put(
    "/permissions/{perm_id}",
    response_model=APIResponse[PermissionResponse],
    summary="更新权限",
)
async def update_permission(
    perm_id: str,
    request: UpdatePermissionRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("permissions:write")),
):
    """更新权限信息"""
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        data = await service.update_permission(perm_id, payload)
        return APIResponse(data=data)
    except PermissionNotFoundError:
        raise HTTPException(status_code=404, detail="permission not found")
