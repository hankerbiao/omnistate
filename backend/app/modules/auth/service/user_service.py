"""User resource service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.modules.auth.repository.models import UserDoc
from app.modules.auth.service.exceptions import UserNotFoundError
from app.modules.auth.service.support import AuthServiceSupport
from app.shared.auth import hash_password, verify_password
from app.shared.auth.jwt_auth import get_permissions_by_ids, get_permissions_by_role_ids, is_admin_role


class UserService(AuthServiceSupport):
    """User CRUD, authentication, and permission aggregation."""

    _USER_UPDATABLE_FIELDS = {"username", "email", "status", "itcode"}

    async def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await UserDoc.find_one(UserDoc.user_id == data["user_id"])
        if existing:
            raise ValueError("user_id already exists")
        await self._ensure_roles_exist(data.get("role_ids", []))
        await self._ensure_permissions_exist(data.get("extra_permission_ids", []))
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
        doc = await self._find_or_raise(UserDoc, UserDoc.user_id == user_id, UserNotFoundError)
        return self._doc_to_dict(doc)

    async def list_users(
        self,
        status: Optional[str] = None,
        role_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = UserDoc.find()
        if status:
            query = query.find(UserDoc.status == status)
        if role_id:
            query = query.find({"role_ids": role_id})
        if search:
            # 支持搜索用户名或用户ID
            query = query.find(
                {"$or": [
                    {"username": {"$regex": search, "$options": "i"}},
                    {"user_id": {"$regex": search, "$options": "i"}},
                ]}
            )
        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_user(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await self._find_or_raise(UserDoc, UserDoc.user_id == user_id, UserNotFoundError)
        self._apply_updates(doc, data, self._USER_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_user_roles(self, user_id: str, role_ids: List[str]) -> Dict[str, Any]:
        doc = await self._find_or_raise(UserDoc, UserDoc.user_id == user_id, UserNotFoundError)
        await self._ensure_roles_exist(role_ids)
        doc.role_ids = role_ids
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_user_extra_permissions(self, user_id: str, extra_permission_ids: List[str]) -> Dict[str, Any]:
        """更新用户的独立额外权限列表。"""
        doc = await self._find_or_raise(UserDoc, UserDoc.user_id == user_id, UserNotFoundError)
        await self._ensure_permissions_exist(extra_permission_ids)
        doc.extra_permission_ids = extra_permission_ids
        await doc.save()
        return self._doc_to_dict(doc)

    async def _set_password(self, doc, new_password: str) -> None:
        salt, pwd_hash = hash_password(new_password)
        doc.password_salt = salt
        doc.password_hash = pwd_hash

    async def update_user_password(self, user_id: str, new_password: str) -> Dict[str, Any]:
        doc = await self._find_or_raise(UserDoc, UserDoc.user_id == user_id, UserNotFoundError)
        await self._set_password(doc, new_password)
        await doc.save()
        return self._doc_to_dict(doc)

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        doc = await self._find_or_raise(UserDoc, UserDoc.user_id == user_id, UserNotFoundError)
        if not verify_password(old_password, doc.password_salt, doc.password_hash):
            raise ValueError("invalid credentials")
        await self._set_password(doc, new_password)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_user(self, user_id: str, current_user_id: str) -> None:
        """删除用户（软删除，设置 status 为 DISABLED）。"""
        doc = await self._find_or_raise(UserDoc, UserDoc.user_id == user_id, UserNotFoundError)
        # 禁止删除自己
        if user_id == current_user_id:
            raise ValueError("cannot delete yourself")
        # 检查是否是最后一个 ADMIN
        admin_users = await UserDoc.find({"role_ids": {"$regex": "ADMIN", "$options": "i"}}).count()
        if admin_users <= 1 and is_admin_role(doc.role_ids or []):
            # 检查当前用户是否是 ADMIN，如果不是，禁止删除最后一个 ADMIN
            current_user = await UserDoc.find_one(UserDoc.user_id == current_user_id)
            if current_user and not is_admin_role(current_user.role_ids or []):
                raise ValueError("cannot delete the last admin user")
        # 软删除：设置状态为 DISABLED
        doc.status = "DISABLED"
        await doc.save()

    async def get_effective_permissions(self, user_id: str) -> Dict[str, Any]:
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise UserNotFoundError("user not found")
        role_ids = user.role_ids or []
        extra_ids = user.extra_permission_ids or []

        role_codes = await get_permissions_by_role_ids(role_ids)
        extra_codes = await get_permissions_by_ids(extra_ids)

        all_codes = sorted(set(role_codes) | set(extra_codes))
        return {
            "user_id": user_id,
            "role_ids": role_ids,
            "extra_permission_ids": extra_ids,
            "role_permissions": role_codes,
            "extra_permissions": extra_codes,
            "permissions": all_codes,
        }
