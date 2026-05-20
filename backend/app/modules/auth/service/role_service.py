"""角色资源服务模块。

提供角色的增删改查以及权限绑定功能。
依赖于 RoleDoc 数据模型和权限验证逻辑。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.modules.auth.repository.models import RoleDoc, UserDoc
from app.modules.auth.service.exceptions import RoleNotFoundError
from app.modules.auth.service.support import AuthServiceSupport


class RoleService(AuthServiceSupport):
    """角色服务类。

    负责角色的创建、查询、更新和权限绑定操作。
    继承自 AuthServiceSupport，获取通用的权限验证和辅助方法。
    """

    # 角色允许更新的字段集合，用于控制哪些字段可通过 update_role 修改
    _ROLE_UPDATABLE_FIELDS = {"name", "description"}

    async def create_role(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新角色。

        Args:
            data: 包含 role_id、name、permission_ids 等字段的角色数据
                  如果 role_id 未提供，将自动从 name 生成

        Returns:
            创建成功后的角色字典

        Raises:
            ValueError: 当 role_id 已存在时抛出
        """
        # 自动生成 role_id（如果未提供）
        if "role_id" not in data or not data["role_id"]:
            data["role_id"] = self._generate_role_id(data["name"])
        existing = await RoleDoc.find_one(RoleDoc.role_id == data["role_id"])
        if existing:
            raise ValueError("role_id already exists")
        # 验证权限 IDs 是否有效
        await self._ensure_permissions_exist(data.get("permission_ids", []))
        doc = RoleDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    @staticmethod
    def _generate_role_id(name: str) -> str:
        """从角色名称生成 role_id。

        Args:
            name: 角色名称

        Returns:
            slugified 的 role_id
        """
        # 转小写，空格和特殊字符替换为下划线
        slug = name.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[_\s]+", "_", slug)
        return slug

    async def get_role(self, role_id: str) -> Dict[str, Any]:
        """根据 role_id 获取单个角色。"""
        doc = await self._find_or_raise(RoleDoc, RoleDoc.role_id == role_id, RoleNotFoundError)
        return self._doc_to_dict(doc)

    async def list_roles(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """分页查询角色列表。

        Args:
            limit: 每页返回的最大数量，默认 50
            offset: 跳过的记录数，用于分页，默认 0

        Returns:
            角色字典列表，按创建时间倒序排列
        """
        docs = await RoleDoc.find().sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_role(self, role_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新角色基本信息。"""
        doc = await self._find_or_raise(RoleDoc, RoleDoc.role_id == role_id, RoleNotFoundError)
        self._apply_updates(doc, data, self._ROLE_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_role_permissions(self, role_id: str, permission_ids: List[str]) -> Dict[str, Any]:
        """更新角色的权限列表（整体替换）。"""
        doc = await self._find_or_raise(RoleDoc, RoleDoc.role_id == role_id, RoleNotFoundError)
        await self._ensure_permissions_exist(permission_ids)
        doc.permission_ids = permission_ids
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_role(self, role_id: str) -> None:
        """删除角色。

        Raises:
            RoleNotFoundError: 当角色不存在时抛出
            ValueError: 当角色是系统角色时抛出，或当有用户绑定此角色时抛出
        """
        doc = await self._find_or_raise(RoleDoc, RoleDoc.role_id == role_id, RoleNotFoundError)
        if doc.is_system:
            raise ValueError("cannot delete system role")
        user_count = await UserDoc.find({"role_ids": role_id}).count()
        if user_count > 0:
            raise ValueError(f"cannot delete role: {user_count} user(s) are assigned to this role")
        await doc.delete()
