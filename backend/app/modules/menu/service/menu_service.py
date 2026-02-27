"""菜单管理服务。"""
from typing import Dict, Any, List, Optional, Set

from app.shared.service import BaseService
from app.modules.menu.repository.models import MenuDoc
from app.modules.auth.repository.models import UserDoc, RoleDoc, PermissionDoc


class MenuService(BaseService):
    _UPDATABLE_FIELDS = {
        "name",
        "path",
        "icon",
        "parent_menu_id",
        "order",
        "required_permissions",
        "is_active",
    }

    async def create_menu(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await MenuDoc.find_one(MenuDoc.menu_id == data["menu_id"])
        if existing and not existing.is_deleted:
            raise ValueError("menu_id already exists")
        doc = MenuDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_menu(self, menu_id: str) -> Dict[str, Any]:
        doc = await MenuDoc.find_one(MenuDoc.menu_id == menu_id, MenuDoc.is_deleted == False)
        if not doc:
            raise KeyError("menu not found")
        return self._doc_to_dict(doc)

    async def list_menus(
        self,
        is_active: Optional[bool] = None,
        parent_menu_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = MenuDoc.find(MenuDoc.is_deleted == False)
        if is_active is not None:
            query = query.find(MenuDoc.is_active == is_active)
        if parent_menu_id is not None:
            query = query.find(MenuDoc.parent_menu_id == parent_menu_id)
        docs = await query.sort("order", "name").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_menu(self, menu_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await MenuDoc.find_one(MenuDoc.menu_id == menu_id, MenuDoc.is_deleted == False)
        if not doc:
            raise KeyError("menu not found")
        self._apply_updates(doc, data, self._UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_menu(self, menu_id: str) -> None:
        doc = await MenuDoc.find_one(MenuDoc.menu_id == menu_id, MenuDoc.is_deleted == False)
        if not doc:
            raise KeyError("menu not found")
        doc.is_deleted = True
        await doc.save()

    async def get_user_effective_permissions(self, user_id: str) -> List[str]:
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            return []
        role_ids = user.role_ids or []
        if not role_ids:
            return []

        roles = await RoleDoc.find({"role_id": {"$in": role_ids}}).to_list()
        perm_ids: Set[str] = set()
        for role in roles:
            perm_ids.update(role.permission_ids)
        if not perm_ids:
            return []

        perms = await PermissionDoc.find({"perm_id": {"$in": list(perm_ids)}}).to_list()
        return sorted({p.code for p in perms})

    async def list_visible_menus_for_user(self, user_id: str) -> Dict[str, Any]:
        """根据用户权限返回可见菜单列表。"""
        permissions = await self.get_user_effective_permissions(user_id)
        permission_set = set(permissions)

        docs = await MenuDoc.find(
            MenuDoc.is_deleted == False,
            MenuDoc.is_active == True,
        ).sort("order", "name").to_list()

        visible: List[Dict[str, Any]] = []
        for doc in docs:
            required = doc.required_permissions or []
            if not required or set(required).issubset(permission_set):
                visible.append(self._doc_to_dict(doc))

        return {
            "user_id": user_id,
            "permissions": permissions,
            "menus": visible,
        }
