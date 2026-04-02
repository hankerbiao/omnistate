"""Role resource service."""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.auth.repository.models import RoleDoc
from app.modules.auth.service.exceptions import RoleNotFoundError
from app.modules.auth.service.support import AuthServiceSupport


class RoleService(AuthServiceSupport):
    """Role CRUD and permission binding."""

    _ROLE_UPDATABLE_FIELDS = {"name"}

    async def create_role(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await RoleDoc.find_one(RoleDoc.role_id == data["role_id"])
        if existing:
            raise ValueError("role_id already exists")
        await self._ensure_permissions_exist(data.get("permission_ids", []))
        doc = RoleDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_role(self, role_id: str) -> Dict[str, Any]:
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise RoleNotFoundError("role not found")
        return self._doc_to_dict(doc)

    async def list_roles(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        docs = await RoleDoc.find().sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_role(self, role_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise RoleNotFoundError("role not found")
        self._apply_updates(doc, data, self._ROLE_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_role_permissions(self, role_id: str, permission_ids: List[str]) -> Dict[str, Any]:
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise RoleNotFoundError("role not found")
        await self._ensure_permissions_exist(permission_ids)
        doc.permission_ids = permission_ids
        await doc.save()
        return self._doc_to_dict(doc)
