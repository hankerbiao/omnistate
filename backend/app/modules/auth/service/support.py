"""Auth service shared support helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.auth.repository.models import PermissionDoc, RoleDoc
from app.modules.auth.service.exceptions import PermissionNotFoundError, RoleNotFoundError
from app.shared.service import BaseService


class AuthServiceSupport(BaseService):
    """Shared persistence and navigation helpers for auth services."""

    _DEFAULT_NAV_VIEWS = ["req_list", "case_list", "my_tasks"]

    async def _ensure_roles_exist(self, role_ids: List[str]) -> None:
        if not role_ids:
            return
        count = await RoleDoc.find({"role_id": {"$in": role_ids}}).count()
        if count != len(set(role_ids)):
            raise RoleNotFoundError("role not found")

    async def _ensure_permissions_exist(self, permission_ids: List[str]) -> None:
        if not permission_ids:
            return
        count = await PermissionDoc.find({"perm_id": {"$in": permission_ids}}).count()
        if count != len(set(permission_ids)):
            raise PermissionNotFoundError("permission not found")

    @staticmethod
    def _nav_views_in_order(nav_pages: List[Dict[str, Any]]) -> List[str]:
        views = [str(item.get("view", "")).strip() for item in nav_pages]
        return [view for view in views if view]

    @staticmethod
    def _sanitize_nav_views(views: List[str], all_nav_views: List[str]) -> List[str]:
        valid_views = set(all_nav_views)
        seen = set()
        ordered: List[str] = []
        for view in views:
            if view in valid_views and view not in seen:
                seen.add(view)
                ordered.append(view)
        ordered_set = set(ordered)
        return [view for view in all_nav_views if view in ordered_set]

    @classmethod
    def _derive_nav_views_from_permissions(
        cls,
        permissions: List[str],
        nav_pages: List[Dict[str, Any]],
        all_nav_views: List[str],
    ) -> List[str]:
        permission_set = set(permissions)
        derived = []
        for item in nav_pages:
            view = item.get("view")
            permission = item.get("permission")
            if not view:
                continue
            if permission == "nav:public" or permission is None:
                derived.append(view)
            elif permission in permission_set:
                derived.append(view)
        return cls._sanitize_nav_views(derived, all_nav_views)

    @classmethod
    def _ensure_mandatory_nav_views(cls, views: List[str], all_nav_views: List[str]) -> List[str]:
        return cls._sanitize_nav_views(views, all_nav_views)
