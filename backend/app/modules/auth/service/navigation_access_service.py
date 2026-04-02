"""Navigation page and access service."""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.auth.repository.models import UserDoc
from app.modules.auth.service.exceptions import UserNotFoundError
from app.modules.auth.service.navigation_page_service import NavigationPageService
from app.modules.auth.service.support import AuthServiceSupport
from app.shared.auth.jwt_auth import get_permissions_by_role_ids, is_admin_role


class NavigationAccessService(AuthServiceSupport):
    """Navigation definition CRUD and user-level access derivation."""

    def __init__(self, navigation_page_service: NavigationPageService | None = None) -> None:
        self._navigation_service = navigation_page_service or NavigationPageService()

    async def list_navigation_pages(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        return await self._navigation_service.list_pages(include_inactive=include_inactive)

    async def get_navigation_page(self, view: str) -> Dict[str, Any]:
        return await self._navigation_service.get_page(view)

    async def create_navigation_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._navigation_service.create_page(data)

    async def update_navigation_page(self, view: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._navigation_service.update_page(view, data)

    async def delete_navigation_page(self, view: str) -> Dict[str, Any]:
        await self._navigation_service.delete_page(view)
        return {"deleted": True, "view": view}

    async def get_user_navigation(self, user_id: str) -> Dict[str, Any]:
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise UserNotFoundError("user not found")

        role_ids = user.role_ids or []
        permissions = await get_permissions_by_role_ids(role_ids) if role_ids else []
        nav_pages = await self._navigation_service.list_active_pages()
        all_nav_views = self._nav_views_in_order(nav_pages)

        if is_admin_role(role_ids):
            allowed_nav_views = list(all_nav_views)
            if "all" not in permissions:
                permissions = ["all", *permissions]
        else:
            user_override = self._sanitize_nav_views(user.allowed_nav_views or [], all_nav_views)
            if user_override:
                allowed_nav_views = user_override
            else:
                allowed_nav_views = self._derive_nav_views_from_permissions(permissions, nav_pages, all_nav_views)
                if not allowed_nav_views:
                    allowed_nav_views = self._sanitize_nav_views(self._DEFAULT_NAV_VIEWS, all_nav_views)

        allowed_nav_views = self._ensure_mandatory_nav_views(allowed_nav_views, all_nav_views)
        return {
            "user_id": user_id,
            "role_ids": role_ids,
            "permissions": permissions,
            "allowed_nav_views": allowed_nav_views,
        }

    async def update_user_navigation(self, user_id: str, allowed_nav_views: List[str]) -> Dict[str, Any]:
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise UserNotFoundError("user not found")

        nav_pages = await self._navigation_service.list_active_pages()
        all_nav_views = self._nav_views_in_order(nav_pages)
        normalized_views = self._sanitize_nav_views(allowed_nav_views, all_nav_views)
        if is_admin_role(user.role_ids or []):
            normalized_views = list(all_nav_views)
        elif not normalized_views:
            raise ValueError("allowed_nav_views must contain at least one valid view")
        normalized_views = self._ensure_mandatory_nav_views(normalized_views, all_nav_views)

        user.allowed_nav_views = normalized_views
        await user.save()
        return await self.get_user_navigation(user_id)
