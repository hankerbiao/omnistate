"""角色资源服务模块。

提供角色的增删改查以及权限绑定功能。
依赖于 RoleDoc 数据模型和权限验证逻辑。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.auth.repository.models import RoleDoc
from app.modules.auth.service.exceptions import RoleNotFoundError
from app.modules.auth.service.support import AuthServiceSupport


class RoleService(AuthServiceSupport):
    """角色服务类。

    负责角色的创建、查询、更新和权限绑定操作。
    继承自 AuthServiceSupport，获取通用的权限验证和辅助方法。
    """

    # 角色允许更新的字段集合，用于控制哪些字段可通过 update_role 修改
    _ROLE_UPDATABLE_FIELDS = {"name"}

    async def create_role(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新角色。

        Args:
            data: 包含 role_id、name、permission_ids 等字段的角色数据

        Returns:
            创建成功后的角色字典

        Raises:
            ValueError: 当 role_id 已存在时抛出
        """
        existing = await RoleDoc.find_one(RoleDoc.role_id == data["role_id"])
        if existing:
            raise ValueError("role_id already exists")
        # 验证权限 IDs 是否有效
        await self._ensure_permissions_exist(data.get("permission_ids", []))
        doc = RoleDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_role(self, role_id: str) -> Dict[str, Any]:
        """根据 role_id 获取单个角色。

        Args:
            role_id: 角色的唯一标识符

        Returns:
            角色信息字典

        Raises:
            RoleNotFoundError: 当角色不存在时抛出
        """
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise RoleNotFoundError("role not found")
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
        """更新角色基本信息。

        Args:
            role_id: 要更新的角色唯一标识符
            data: 包含更新字段的字典，仅允许更新 _ROLE_UPDATABLE_FIELDS 中的字段

        Returns:
            更新后的角色字典

        Raises:
            RoleNotFoundError: 当角色不存在时抛出
        """
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise RoleNotFoundError("role not found")
        # 仅应用允许更新的字段（当前仅 name）
        self._apply_updates(doc, data, self._ROLE_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def update_role_permissions(self, role_id: str, permission_ids: List[str]) -> Dict[str, Any]:
        """更新角色的权限列表。

        将角色的所有权限替换为新的权限列表（整体替换而非增量）。

        Args:
            role_id: 要更新的角色唯一标识符
            permission_ids: 新的权限 ID 列表，会完全替换原有权限

        Returns:
            更新后的角色字典

        Raises:
            RoleNotFoundError: 当角色不存在时抛出
        """
        doc = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if not doc:
            raise RoleNotFoundError("role not found")
        # 确保所有权限 ID 都是有效的
        await self._ensure_permissions_exist(permission_ids)
        doc.permission_ids = permission_ids
        await doc.save()
        return self._doc_to_dict(doc)
