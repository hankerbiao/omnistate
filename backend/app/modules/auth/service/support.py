"""认证服务共享辅助工具模块。

提供角色/权限存在性验证、导航视图处理等通用功能。
被 UserService、RoleService 等认证模块服务类继承使用。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.auth.repository.models import PermissionDoc, RoleDoc
from app.modules.auth.service.exceptions import PermissionNotFoundError, RoleNotFoundError
from app.shared.service import BaseService


class AuthServiceSupport(BaseService):
    """认证服务共享工具基类。

    提供数据存在性验证和导航视图处理等通用方法。
    所有认证模块的服务类应继承此类以复用通用逻辑。
    """

    # 默认导航视图列表，用户登录后默认可见的页面
    _DEFAULT_NAV_VIEWS = ["req_list", "case_list", "my_tasks"]

    async def _ensure_roles_exist(self, role_ids: List[str]) -> None:
        """验证角色 IDs 是否全部存在。

        Args:
            role_ids: 待验证的角色 ID 列表

        Raises:
            RoleNotFoundError: 当任意角色 ID 不存在时抛出
        """
        if not role_ids:
            return
        count = await RoleDoc.find({"role_id": {"$in": role_ids}}).count()
        if count != len(set(role_ids)):
            raise RoleNotFoundError("role not found")

    async def _ensure_permissions_exist(self, permission_ids: List[str]) -> None:
        """验证权限 IDs 是否全部存在。

        Args:
            permission_ids: 待验证的权限 ID 列表

        Raises:
            PermissionNotFoundError: 当任意权限 ID 不存在时抛出
        """
        if not permission_ids:
            return
        count = await PermissionDoc.find({"perm_id": {"$in": permission_ids}}).count()
        if count != len(set(permission_ids)):
            raise PermissionNotFoundError("permission not found")

    @staticmethod
    def _nav_views_in_order(nav_pages: List[Dict[str, Any]]) -> List[str]:
        """从导航页面配置中提取视图名称列表。

        Args:
            nav_pages: 导航页面配置列表，每项包含 view 字段

        Returns:
            按原始顺序排列的视图名称列表（去除了空值）
        """
        views = [str(item.get("view", "")).strip() for item in nav_pages]
        return [view for view in views if view]

    @staticmethod
    def _sanitize_nav_views(views: List[str], all_nav_views: List[str]) -> List[str]:
        """清理和规范化导航视图列表。

        去除重复项，保留首次出现的顺序，并确保所有视图都在合法范围内。

        Args:
            views: 原始视图列表（可能包含重复和非法值）
            all_nav_views: 所有合法的导航视图列表

        Returns:
            去重后的合法视图列表，按首次出现顺序排列
        """
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
        """根据用户权限推导出可访问的导航视图。

        遍历导航页面配置，将用户拥有权限的页面视图加入结果列表。

        Args:
            permissions: 用户拥有的权限 ID 列表
            nav_pages: 导航页面配置列表，每项包含 view 和 permission 字段
            all_nav_views: 所有合法的导航视图列表

        Returns:
            用户可访问的导航视图列表（已清理和去重）
        """
        permission_set = set(permissions)
        derived = []
        for item in nav_pages:
            view = item.get("view")
            permission = item.get("permission")
            if not view:
                continue
            # nav:public 或无权限要求的页面对所有用户可见
            if permission == "nav:public" or permission is None:
                derived.append(view)
            elif permission in permission_set:
                derived.append(view)
        return cls._sanitize_nav_views(derived, all_nav_views)

    @classmethod
    def _ensure_mandatory_nav_views(cls, views: List[str], all_nav_views: List[str]) -> List[str]:
        """确保强制导航视图存在。

        验证必选视图列表的合法性并去除非法值。

        Args:
            views: 强制要求的导航视图列表
            all_nav_views: 所有合法的导航视图列表

        Returns:
            清理后的导航视图列表
        """
        return cls._sanitize_nav_views(views, all_nav_views)
