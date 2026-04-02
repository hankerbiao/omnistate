"""Permission resource service."""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.auth.repository.models import PermissionDoc
from app.modules.auth.service.exceptions import PermissionNotFoundError
from app.modules.auth.service.support import AuthServiceSupport


class PermissionService(AuthServiceSupport):
    """Permission CRUD service."""

    _PERMISSION_UPDATABLE_FIELDS = {"code", "name", "description"}

    async def create_permission(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await PermissionDoc.find_one(PermissionDoc.perm_id == data["perm_id"])
        if existing:
            raise ValueError("perm_id already exists")
        doc = PermissionDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_permission(self, perm_id: str) -> Dict[str, Any]:
        doc = await PermissionDoc.find_one(PermissionDoc.perm_id == perm_id)
        if not doc:
            raise PermissionNotFoundError("permission not found")
        return self._doc_to_dict(doc)

    async def list_permissions(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        docs = await PermissionDoc.find().sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_permission(self, perm_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await PermissionDoc.find_one(PermissionDoc.perm_id == perm_id)
        if not doc:
            raise PermissionNotFoundError("permission not found")
        self._apply_updates(doc, data, self._PERMISSION_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)
