"""Compatibility RBAC facade."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.modules.auth.service.navigation_access_service import NavigationAccessService
from app.modules.auth.service.permission_service import PermissionService
from app.modules.auth.service.role_service import RoleService
from app.modules.auth.service.user_service import UserService


class RbacService:
    """Deprecated compatibility facade delegating to resource services."""

    def __init__(
        self,
        user_service: UserService | None = None,
        role_service: RoleService | None = None,
        permission_service: PermissionService | None = None,
        navigation_access_service: NavigationAccessService | None = None,
    ) -> None:
        self._user_service = user_service or UserService()
        self._role_service = role_service or RoleService()
        self._permission_service = permission_service or PermissionService()
        self._navigation_access_service = navigation_access_service or NavigationAccessService()

    async def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._user_service.create_user(data)

    async def authenticate_user(self, user_id: str, password: str) -> Dict[str, Any]:
        return await self._user_service.authenticate_user(user_id, password)

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        return await self._user_service.get_user(user_id)

    async def list_users(
        self,
        status: Optional[str] = None,
        role_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return await self._user_service.list_users(status=status, role_id=role_id, limit=limit, offset=offset)

    async def update_user(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._user_service.update_user(user_id, data)

    async def update_user_roles(self, user_id: str, role_ids: List[str]) -> Dict[str, Any]:
        return await self._user_service.update_user_roles(user_id, role_ids)

    async def update_user_password(self, user_id: str, new_password: str) -> Dict[str, Any]:
        return await self._user_service.update_user_password(user_id, new_password)

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        return await self._user_service.change_password(user_id, old_password, new_password)

    async def get_effective_permissions(self, user_id: str) -> Dict[str, Any]:
        return await self._user_service.get_effective_permissions(user_id)

    async def create_role(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._role_service.create_role(data)

    async def get_role(self, role_id: str) -> Dict[str, Any]:
        return await self._role_service.get_role(role_id)

    async def list_roles(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        return await self._role_service.list_roles(limit=limit, offset=offset)

    async def update_role(self, role_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._role_service.update_role(role_id, data)

    async def update_role_permissions(self, role_id: str, permission_ids: List[str]) -> Dict[str, Any]:
        return await self._role_service.update_role_permissions(role_id, permission_ids)

    async def create_permission(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._permission_service.create_permission(data)

    async def get_permission(self, perm_id: str) -> Dict[str, Any]:
        return await self._permission_service.get_permission(perm_id)

    async def list_permissions(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return await self._permission_service.list_permissions(limit=limit, offset=offset)

    async def update_permission(self, perm_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._permission_service.update_permission(perm_id, data)

    async def list_navigation_pages(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        return await self._navigation_access_service.list_navigation_pages(include_inactive=include_inactive)

    async def get_navigation_page(self, view: str) -> Dict[str, Any]:
        return await self._navigation_access_service.get_navigation_page(view)

    async def create_navigation_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._navigation_access_service.create_navigation_page(data)

    async def update_navigation_page(self, view: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._navigation_access_service.update_navigation_page(view, data)

    async def delete_navigation_page(self, view: str) -> Dict[str, Any]:
        return await self._navigation_access_service.delete_navigation_page(view)

    async def get_user_navigation(self, user_id: str) -> Dict[str, Any]:
        return await self._navigation_access_service.get_user_navigation(user_id)

    async def update_user_navigation(self, user_id: str, allowed_nav_views: List[str]) -> Dict[str, Any]:
        return await self._navigation_access_service.update_user_navigation(user_id, allowed_nav_views)
