"""Shared auth service helpers."""

from __future__ import annotations

from typing import Type

from app.modules.auth.permissions import permission_exists
from app.modules.auth.repository.models import RoleDoc
from app.modules.auth.service.exceptions import PermissionNotFoundError, RoleNotFoundError
from app.shared.service import BaseService


class AuthServiceSupport(BaseService):
    """Shared lookup and validation helpers for auth services."""

    @staticmethod
    async def _find_or_raise(model_cls: Type, condition, error_cls: Type[Exception], error_msg: str = "not found"):
        doc = await model_cls.find_one(condition)
        if not doc:
            raise error_cls(error_msg)
        return doc

    async def _ensure_roles_exist(self, role_ids: list[str]) -> None:
        if not role_ids:
            return
        count = await RoleDoc.find({"role_id": {"$in": role_ids}}).count()
        if count != len(set(role_ids)):
            raise RoleNotFoundError("role not found")

    async def _ensure_permissions_exist(self, permission_ids: list[str]) -> None:
        missing = [pid for pid in set(permission_ids) if not permission_exists(pid)]
        if missing:
            raise PermissionNotFoundError("permission not found")
