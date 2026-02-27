"""RBAC 服务

AI 友好注释说明：
- Service 层负责业务规则与数据库交互。
- 本文件不实现鉴权，仅提供用户/角色/权限的 CRUD 与关联校验。
- ADMIN 权限控制建议在 API 层依赖或中间件中实现。
"""
from typing import Dict, Any, Optional, List
from app.shared.service import BaseService
from app.shared.auth import hash_password, verify_password
from app.modules.auth.repository.models import UserDoc, RoleDoc, PermissionDoc


class RbacService(BaseService):
    """用户/角色/权限管理服务（异步）"""

    # 允许更新的字段白名单，避免主键/非法字段被写入
    _USER_UPDATABLE_FIELDS = {"username", "email", "status"}
    _ROLE_UPDATABLE_FIELDS = {"name"}
    _PERMISSION_UPDATABLE_FIELDS = {"code", "name", "description"}

    # ===== Users =====

    async def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户并校验角色存在"""
        existing = await UserDoc.find_one(UserDoc.user_id == data["user_id"])
        if existing:
            raise ValueError("user_id already exists")
        await self._ensure_roles_exist(data.get("role_ids", []))

        # 密码加密存储
        salt, pwd_hash = hash_password(data["password"])
        data["password_salt"] = salt
        data["password_hash"] = pwd_hash
        data.pop("password", None)

        doc = UserDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def authenticate_user(self, user_id: str, password: str) -> Dict[str, Any]:
        """校验用户密码，返回用户信息"""
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user or user.status != "ACTIVE":
            raise KeyError("user not found")
        if not verify_password(password, user.password_salt, user.password_hash):
            raise ValueError("invalid credentials")
        return self._doc_to_dict(user)

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """根据 user_id 获取用户"""
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise KeyError("user not found")
        return self._doc_to_dict(doc)

    async def list_users(
        self,
        status: Optional[str] = None,
        role_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """查询用户列表，支持按状态与角色过滤"""
        query = UserDoc.find()
        if status:
            query = query.find(UserDoc.status == status)
        if role_id:
            # role_ids 为数组字段，使用包含查询
            query = query.find({"role_ids": role_id})
        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_user(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户信息（白名单字段）"""
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise KeyError("user not found")
        self._apply_updates(doc, data, self._USER_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_user_roles(self, user_id: str, role_ids: List[str]) -> Dict[str, Any]:
        """更新用户角色列表（管理员操作）"""
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise KeyError("user not found")
        await self._ensure_roles_exist(role_ids)
        doc.role_ids = role_ids
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_user_password(self, user_id: str, new_password: str) -> Dict[str, Any]:
        """更新用户密码（管理员或本人）"""
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise KeyError("user not found")
        salt, pwd_hash = hash_password(new_password)
        doc.password_salt = salt
        doc.password_hash = pwd_hash
        await doc.save()
        return self._doc_to_dict(doc)

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """用户自助修改密码（需要旧密码）"""
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise KeyError("user not found")
        if not verify_password(old_password, doc.password_salt, doc.password_hash):
            raise ValueError("invalid credentials")
        salt, pwd_hash = hash_password(new_password)
        doc.password_salt = salt
        doc.password_hash = pwd_hash
        await doc.save()
        return self._doc_to_dict(doc)

    async def get_effective_permissions(self, user_id: str) -> Dict[str, Any]:
        """获取用户有效权限（多角色并集）"""
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise KeyError("user not found")

        if not user.role_ids:
            return {"user_id": user_id, "role_ids": [], "permissions": []}

        roles = await RoleDoc.find({"role_id": {"$in": user.role_ids}}).to_list()
        perm_ids: List[str] = []
        for role in roles:
            perm_ids.extend(role.permission_ids)

        if not perm_ids:
            return {"user_id": user_id, "role_ids": user.role_ids, "permissions": []}

        perms = await PermissionDoc.find({"perm_id": {"$in": list(set(perm_ids))}}).to_list()
        codes = sorted({perm.code for perm in perms})
        return {"user_id": user_id, "role_ids": user.role_ids, "permissions": codes}

    # ===== Roles =====

    async def create_role(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建角色并校验权限存在"""
        existing = await RoleDoc.find_one(RoleDoc.role_id == data["role_id"])
        if existing:
            raise ValueError("role_id already exists")
        await self._ensure_permissions_exist(data.get("permission_ids", []))
        doc = RoleDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_role(self, role_id: str) -> Dict[str, Any]:
        """获取角色详情"""
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise KeyError("role not found")
        return self._doc_to_dict(doc)

    async def list_roles(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """查询角色列表"""
        docs = await RoleDoc.find().sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_role(self, role_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新角色信息（仅允许更新名称）"""
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise KeyError("role not found")
        self._apply_updates(doc, data, self._ROLE_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_role_permissions(self, role_id: str, permission_ids: List[str]) -> Dict[str, Any]:
        """更新角色权限列表（管理员操作）"""
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise KeyError("role not found")
        await self._ensure_permissions_exist(permission_ids)
        doc.permission_ids = permission_ids
        await doc.save()
        return self._doc_to_dict(doc)

    # ===== Permissions =====

    async def create_permission(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建权限"""
        existing = await PermissionDoc.find_one(PermissionDoc.perm_id == data["perm_id"])
        if existing:
            raise ValueError("perm_id already exists")
        doc = PermissionDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_permission(self, perm_id: str) -> Dict[str, Any]:
        """获取权限详情"""
        doc = await PermissionDoc.find_one(PermissionDoc.perm_id == perm_id)
        if not doc:
            raise KeyError("permission not found")
        return self._doc_to_dict(doc)

    async def list_permissions(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """查询权限列表"""
        docs = await PermissionDoc.find().sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_permission(self, perm_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新权限信息"""
        doc = await PermissionDoc.find_one(PermissionDoc.perm_id == perm_id)
        if not doc:
            raise KeyError("permission not found")
        self._apply_updates(doc, data, self._PERMISSION_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    # ===== Helpers =====

    async def _ensure_roles_exist(self, role_ids: List[str]) -> None:
        """校验角色是否都存在，避免绑定到无效角色"""
        if not role_ids:
            return
        count = await RoleDoc.find({"role_id": {"$in": role_ids}}).count()
        if count != len(set(role_ids)):
            raise KeyError("role not found")

    async def _ensure_permissions_exist(self, permission_ids: List[str]) -> None:
        """校验权限是否都存在，避免角色绑定到无效权限"""
        if not permission_ids:
            return
        count = await PermissionDoc.find({"perm_id": {"$in": permission_ids}}).count()
        if count != len(set(permission_ids)):
            raise KeyError("permission not found")
