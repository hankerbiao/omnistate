"""RBAC 服务

AI 友好注释说明：
- Service 层负责业务规则与数据库交互。
- 本文件不实现鉴权，仅提供用户/角色/权限的 CRUD 与关联校验。
- ADMIN 权限控制建议在 API 层依赖或中间件中实现。
"""
from typing import Dict, Any, Optional, List
from app.shared.service import BaseService
from app.shared.auth import hash_password, verify_password
from app.shared.auth.jwt_auth import get_permissions_by_role_ids, is_admin_role
from app.modules.auth.repository.models import UserDoc, RoleDoc, PermissionDoc
from app.modules.auth.service.navigation_page_service import NavigationPageService
from app.modules.auth.service.exceptions import (
    UserNotFoundError,
    RoleNotFoundError,
    PermissionNotFoundError,
)


class RbacService(BaseService):
    """用户/角色/权限管理服务（异步）"""

    # 允许更新的字段白名单，避免主键/非法字段被写入
    _USER_UPDATABLE_FIELDS = {"username", "email", "status"}
    _ROLE_UPDATABLE_FIELDS = {"name"}
    _PERMISSION_UPDATABLE_FIELDS = {"code", "name", "description"}
    _DEFAULT_NAV_VIEWS = ["req_list", "case_list", "my_tasks"]

    def __init__(self):
        self._navigation_service = NavigationPageService()

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
            raise UserNotFoundError("user not found")
        if not verify_password(password, user.password_salt, user.password_hash):
            raise ValueError("invalid credentials")
        return self._doc_to_dict(user)

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """根据 user_id 获取用户"""
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
            raise UserNotFoundError("user not found")
        self._apply_updates(doc, data, self._USER_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_user_roles(self, user_id: str, role_ids: List[str]) -> Dict[str, Any]:
        """更新用户角色列表（管理员操作）"""
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise UserNotFoundError("user not found")
        await self._ensure_roles_exist(role_ids)
        doc.role_ids = role_ids
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_user_password(self, user_id: str, new_password: str) -> Dict[str, Any]:
        """更新用户密码（管理员或本人）"""
        doc = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not doc:
            raise UserNotFoundError("user not found")
        salt, pwd_hash = hash_password(new_password)
        doc.password_salt = salt
        doc.password_hash = pwd_hash
        await doc.save()
        return self._doc_to_dict(doc)

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """用户自助修改密码（需要旧密码）"""
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
        """获取用户有效权限（多角色并集）"""
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise UserNotFoundError("user not found")

        role_ids = user.role_ids or []
        if not role_ids:
            return {"user_id": user_id, "role_ids": [], "permissions": []}

        codes = await get_permissions_by_role_ids(role_ids)
        return {"user_id": user_id, "role_ids": role_ids, "permissions": codes}

    async def list_navigation_pages(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        """返回导航页面定义。"""
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
        """返回用户可见导航页面（用户级覆盖 > 权限推导；管理员固定全量）。"""
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise UserNotFoundError("user not found")

        effective = await self.get_effective_permissions(user_id)
        permissions = effective.get("permissions", [])
        role_ids = user.role_ids or []
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
        """更新用户导航可见页面（管理员用户固定全量，不允许锁死）。"""
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
            raise RoleNotFoundError("role not found")
        return self._doc_to_dict(doc)

    async def list_roles(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """查询角色列表"""
        docs = await RoleDoc.find().sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_role(self, role_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新角色信息（仅允许更新名称）"""
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise RoleNotFoundError("role not found")
        self._apply_updates(doc, data, self._ROLE_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_role_permissions(self, role_id: str, permission_ids: List[str]) -> Dict[str, Any]:
        """更新角色权限列表（管理员操作）"""
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise RoleNotFoundError("role not found")
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
            raise PermissionNotFoundError("permission not found")
        return self._doc_to_dict(doc)

    async def list_permissions(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """查询权限列表"""
        docs = await PermissionDoc.find().sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_permission(self, perm_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新权限信息"""
        doc = await PermissionDoc.find_one(PermissionDoc.perm_id == perm_id)
        if not doc:
            raise PermissionNotFoundError("permission not found")
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
            raise RoleNotFoundError("role not found")

    async def _ensure_permissions_exist(self, permission_ids: List[str]) -> None:
        """校验权限是否都存在，避免角色绑定到无效权限"""
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
        """根据用户权限和导航页面配置推导可访问的导航视图。

        权限匹配逻辑：
        1. nav:public: 所有登录用户默认可访问
        2. nav:xxx:view: 需要用户具有对应权限码
        3. None: 兼容旧数据，转换为公共权限处理

        Args:
            permissions: 用户拥有的权限码列表
            nav_pages: 所有导航页面配置列表
            all_nav_views: 所有导航页面视图标识列表

        Returns:
            用户可访问的导航视图列表
        """
        permission_set = set(permissions)

        derived = []
        for item in nav_pages:
            view = item.get("view")
            permission = item.get("permission")

            if not view:
                continue

            # 权限匹配逻辑
            if permission == "nav:public":
                # 公共页面，所有登录用户可见
                derived.append(view)
            elif permission and permission in permission_set:
                # 用户拥有对应权限
                derived.append(view)
            elif permission is None:
                # 兼容旧数据：None 权限也作为公共页面处理
                derived.append(view)

        return cls._sanitize_nav_views(derived, all_nav_views)

    @classmethod
    def _ensure_mandatory_nav_views(cls, views: List[str], all_nav_views: List[str]) -> List[str]:
        """确保全员默认可访问导航始终可见。

        注意：该方法现在已经不太需要，因为公共页面权限（nav:public）
        已经通过 _derive_nav_views_from_permissions 方法统一处理。
        保留此方法以兼容现有调用。
        """
        # 由于现在使用 nav:public 权限统一处理公共页面，
        # 这个方法主要是向后兼容，实际上可以简化
        return cls._sanitize_nav_views(views, all_nav_views)
