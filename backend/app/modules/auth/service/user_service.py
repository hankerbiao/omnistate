"""User resource service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.modules.auth.repository.models import UserDoc
from app.modules.auth.service.exceptions import UserNotFoundError
from app.modules.auth.service.support import AuthServiceSupport
from app.shared.auth import hash_password, verify_password
from app.shared.auth.jwt_auth import get_permissions_by_role_ids


class UserService(AuthServiceSupport):
    """User CRUD, authentication, and permission aggregation."""

    _USER_UPDATABLE_FIELDS = {"username", "email", "status"}

    async def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await UserDoc.find_one(UserDoc.user_id == data["user_id"])
        if existing:
            raise ValueError("user_id already exists")
        await self._ensure_roles_exist(data.get("role_ids", []))
        salt, pwd_hash = hash_password(data["password"])
        payload = dict(data)
        payload["password_salt"] = salt
        payload["password_hash"] = pwd_hash
        payload.pop("password", None)
        doc = UserDoc(**payload)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def authenticate_user(self, user_id: str, password: str) -> Dict[str, Any]:
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user or user.status != "ACTIVE":
            raise UserNotFoundError("user not found")
        if not verify_password(password, user.password_salt, user.password_hash):
            raise ValueError("invalid credentials")
        return self._doc_to_dict(user)

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise UserNotFoundError("user not found")
        return self._doc_to_dict(doc)

    async def list_users(
        self,
        status: Optional[str] = None,
        role_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = UserDoc.find()
        if status:
            query = query.find(UserDoc.status == status)
        if role_id:
            query = query.find({"role_ids": role_id})
        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_user(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise UserNotFoundError("user not found")
        self._apply_updates(doc, data, self._USER_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_user_roles(self, user_id: str, role_ids: List[str]) -> Dict[str, Any]:
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise UserNotFoundError("user not found")
        await self._ensure_roles_exist(role_ids)
        doc.role_ids = role_ids
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_user_password(self, user_id: str, new_password: str) -> Dict[str, Any]:
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise UserNotFoundError("user not found")
        salt, pwd_hash = hash_password(new_password)
        doc.password_salt = salt
        doc.password_hash = pwd_hash
        await doc.save()
        return self._doc_to_dict(doc)

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise UserNotFoundError("user not found")
        if not verify_password(old_password, doc.password_salt, doc.password_hash):
            raise ValueError("invalid credentials")
        salt, pwd_hash = hash_password(new_password)
        doc.password_salt = salt
        doc.password_hash = pwd_hash
        await doc.save()
        return self._doc_to_dict(doc)

    async def get_effective_permissions(self, user_id: str) -> Dict[str, Any]:
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise UserNotFoundError("user not found")
        role_ids = user.role_ids or []
        if not role_ids:
            return {"user_id": user_id, "role_ids": [], "permissions": []}
        codes = await get_permissions_by_role_ids(role_ids)
        return {"user_id": user_id, "role_ids": role_ids, "permissions": codes}
