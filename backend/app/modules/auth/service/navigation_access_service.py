"""导航页面和访问权限服务模块。

提供导航页面的 CRUD 操作以及用户级导航视图权限推导功能。
用于管理系统导航菜单和控制用户可见页面。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.auth.repository.models import UserDoc
from app.modules.auth.service.exceptions import UserNotFoundError
from app.modules.auth.service.navigation_page_service import NavigationPageService
from app.modules.auth.service.support import AuthServiceSupport
from app.shared.auth.jwt_auth import get_permissions_by_role_ids, is_admin_role


class NavigationAccessService(AuthServiceSupport):
    """导航访问服务类。

    负责导航页面定义的增删改查，以及用户可访问导航视图的推导。
    继承自 AuthServiceSupport 以复用权限验证和视图处理逻辑。
    """

    def __init__(self, navigation_page_service: NavigationPageService | None = None) -> None:
        """初始化服务。

        Args:
            navigation_page_service: 可选的导航页面服务实例，用于依赖注入
        """
        self._navigation_service = navigation_page_service or NavigationPageService()

    async def list_navigation_pages(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        """列出所有导航页面配置。

        Args:
            include_inactive: 是否包含已禁用的页面，默认 True

        Returns:
            导航页面配置列表
        """
        return await self._navigation_service.list_pages(include_inactive=include_inactive)

    async def get_navigation_page(self, view: str) -> Dict[str, Any]:
        """获取指定视图的导航页面配置。

        Args:
            view: 视图标识符

        Returns:
            导航页面配置字典
        """
        return await self._navigation_service.get_page(view)

    async def create_navigation_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的导航页面配置。

        Args:
            data: 包含 view、label、permission 等字段的页面配置

        Returns:
            创建成功后的页面配置字典
        """
        return await self._navigation_service.create_page(data)

    async def update_navigation_page(self, view: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新导航页面配置。

        Args:
            view: 要更新的视图标识符
            data: 包含更新字段的字典

        Returns:
            更新后的页面配置字典
        """
        return await self._navigation_service.update_page(view, data)

    async def delete_navigation_page(self, view: str) -> Dict[str, Any]:
        """删除导航页面配置（软删除）。

        Args:
            view: 要删除的视图标识符

        Returns:
            删除结果，包含 deleted 状态和 view 信息
        """
        await self._navigation_service.delete_page(view)
        return {"deleted": True, "view": view}

    async def get_user_navigation(self, user_id: str) -> Dict[str, Any]:
        """获取用户的导航视图权限信息。

        根据用户角色和权限计算出可访问的导航视图列表。

        权限推导规则：
        - 管理员角色：可访问所有导航视图，并自动获得 "all" 权限
        - 普通用户：优先使用用户的个人视图配置，否则根据角色权限推导

        Args:
            user_id: 用户唯一标识符

        Returns:
            包含 user_id、role_ids、permissions、allowed_nav_views 的字典

        Raises:
            UserNotFoundError: 当用户不存在时抛出
        """
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise UserNotFoundError("user not found")

        role_ids = user.role_ids or []
        # 根据角色 IDs 获取合并后的权限列表
        permissions = await get_permissions_by_role_ids(role_ids) if role_ids else []
        nav_pages = await self._navigation_service.list_active_pages()
        all_nav_views = self._nav_views_in_order(nav_pages)

        if is_admin_role(role_ids):
            # 管理员可访问所有视图
            allowed_nav_views = list(all_nav_views)
            if "all" not in permissions:
                permissions = ["all", *permissions]
        else:
            # 普通用户：优先使用个人视图配置
            user_override = self._sanitize_nav_views(user.allowed_nav_views or [], all_nav_views)
            if user_override:
                allowed_nav_views = user_override
            else:
                # 根据角色权限推导可访问视图
                allowed_nav_views = self._derive_nav_views_from_permissions(
                    permissions, nav_pages, all_nav_views
                )
                # 如果没有可用视图，回退到默认视图
                if not allowed_nav_views:
                    allowed_nav_views = self._sanitize_nav_views(
                        self._DEFAULT_NAV_VIEWS, all_nav_views
                    )

        # 确保强制视图存在
        allowed_nav_views = self._ensure_mandatory_nav_views(allowed_nav_views, all_nav_views)
        return {
            "user_id": user_id,
            "role_ids": role_ids,
            "permissions": permissions,
            "allowed_nav_views": allowed_nav_views,
        }

    async def update_user_navigation(self, user_id: str, allowed_nav_views: List[str]) -> Dict[str, Any]:
        """更新用户的导航视图配置。

        设置用户可访问的导航视图列表。管理员自动获得所有视图权限。

        Args:
            user_id: 用户唯一标识符
            allowed_nav_views: 允许访问的视图列表

        Returns:
            更新后的用户导航信息

        Raises:
            UserNotFoundError: 当用户不存在时抛出
            ValueError: 当非管理员用户未提供有效视图时抛出
        """
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            raise UserNotFoundError("user not found")

        nav_pages = await self._navigation_service.list_active_pages()
        all_nav_views = self._nav_views_in_order(nav_pages)
        normalized_views = self._sanitize_nav_views(allowed_nav_views, all_nav_views)

        if is_admin_role(user.role_ids or []):
            # 管理员获得所有视图权限
            normalized_views = list(all_nav_views)
        elif not normalized_views:
            raise ValueError("allowed_nav_views must contain at least one valid view")

        normalized_views = self._ensure_mandatory_nav_views(normalized_views, all_nav_views)

        user.allowed_nav_views = normalized_views
        await user.save()
        return await self.get_user_navigation(user_id)
