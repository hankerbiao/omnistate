"""导航页面管理服务。

该服务负责管理系统的前端导航页面，包括：
1. 默认导航页面的初始化和兜底保障
2. 导航页面的完整CRUD操作（创建、查询、更新、删除）
3. 基于权限和状态的页面过滤逻辑
4. 软删除机制支持

核心特性：
- 惰性初始化：首次访问时自动创建默认导航页面
- 权限控制：每个导航页面都关联具体的权限码
- 软删除：物理删除数据，逻辑删除标记
- 顺序控制：通过order字段控制导航显示顺序
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.modules.auth.repository.models import NavigationPageDoc
from app.modules.auth.service.exceptions import NavigationPageNotFoundError
from app.shared.service import BaseService


# ========== 默认导航页面配置 ==========
# 系统预定义的导航页面，包含视图标识、显示名称、权限码等信息
# 这些配置在系统首次启动时自动初始化到数据库中
#
# 权限策略说明：
# - nav:public: 公共页面，所有登录用户可见
# - nav:xxx:view: 需要特定权限码的页面
# - None: 默认情况下会转换为 nav:public，表示公共页面

DEFAULT_NAVIGATION_PAGES: List[Dict[str, Any]] = [
    {
        "view": "req_list",
        "label": "测试需求",
        "permission": "nav:req_list:view",
        "description": "允许访问测试需求列表页",
        "order": 10,
        "is_active": True,
    },
    {
        "view": "case_list",
        "label": "测试用例",
        "permission": "nav:case_list:view",
        "description": "允许访问测试用例列表页",
        "order": 20,
        "is_active": True,
    },
    {
        "view": "my_tasks",
        "label": "我的任务",
        "permission": "nav:public",  # 全员默认可访问的公共页面
        "description": "允许访问当前用户名下任务列表页",
        "order": 30,
        "is_active": True,
    },
    {
        "view": "user_mgmt",
        "label": "用户管理",
        "permission": "nav:user_mgmt:view",
        "description": "允许访问用户与权限管理页",
        "order": 40,
        "is_active": True,
    },
]


class NavigationPageService(BaseService):
    """导航页面 CRUD + 默认数据初始化服务。

    该服务继承自BaseService，提供完整的导航页面管理功能，包括：
    - 导航页面的增删改查操作
    - 默认导航页面的自动初始化
    - 软删除机制和状态管理
    - 权限控制和访问限制
    """

    # 定义允许更新的字段集合，用于更新操作的安全控制
    _UPDATABLE_FIELDS = {"label", "permission", "description", "order", "is_active"}

    async def ensure_default_pages(self) -> None:
        """确保默认导航页面已存在（惰性初始化）。

        该方法实现了懒加载模式：
        1. 首先检查数据库中是否已存在未删除的导航页面
        2. 如果没有，则使用DEFAULT_NAVIGATION_PAGES配置初始化默认页面
        3. 这个方法在每次查询导航页面时被调用，确保系统始终有默认导航可用

        这是系统的兜底机制，确保即使数据库被清空，核心导航功能仍能正常工作。
        """
        # 查询当前活跃（非删除）的导航页面数量
        active_count = await NavigationPageDoc.find({"is_deleted": False}).count()

        # 如果已存在活跃页面，直接返回，避免重复初始化
        if active_count > 0:
            return

        # 遍历默认页面配置，逐个插入到数据库
        for item in DEFAULT_NAVIGATION_PAGES:
            view = item["view"]
            existing = await NavigationPageDoc.find_one(NavigationPageDoc.view == view)
            if existing:
                # 如果页面已存在，执行更新操作
                existing.label = item["label"]
                existing.permission = item.get("permission")
                existing.description = item.get("description")
                existing.order = item.get("order", 0)
                existing.is_active = bool(item.get("is_active", True))
                existing.is_deleted = False
                existing.updated_at = datetime.now(timezone.utc)
                await existing.save()
            else:
                # 如果页面不存在，执行插入操作
                new_doc = NavigationPageDoc(
                    view=view,
                    label=item["label"],
                    permission=item.get("permission"),
                    description=item.get("description"),
                    order=item.get("order", 0),
                    is_active=bool(item.get("is_active", True)),
                    is_deleted=False,
                )
                await new_doc.insert()

    async def list_pages(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        """获取导航页面列表。

        Args:
            include_inactive: 是否包含非激活状态的页面
                             - True: 包含所有状态的页面（默认）
                             - False: 仅包含激活状态的页面

        Returns:
            导航页面列表，按order升序、view升序排序

        功能说明：
        1. 确保默认页面已存在
        2. 根据include_inactive参数过滤查询条件
        3. 按order和view字段排序返回结果
        """
        # 确保有默认页面可用
        await self.ensure_default_pages()

        # 构建基础查询条件：排除已删除的页面
        query = NavigationPageDoc.find({"is_deleted": False})

        # 根据include_inactive参数决定是否过滤非激活状态
        if not include_inactive:
            query = query.find(NavigationPageDoc.is_active == True)  # noqa: E712

        # 执行排序和获取结果
        docs = await query.sort("order", "view").to_list()

        # 将文档对象转换为字典格式
        return [self._doc_to_dict(doc) for doc in docs]

    async def list_active_pages(self) -> List[Dict[str, Any]]:
        """获取激活状态的导航页面列表。

        这是list_pages(include_inactive=False)的便捷方法，
        专门用于获取当前可用的导航页面。

        Returns:
            仅激活状态的导航页面列表
        """
        return await self.list_pages(include_inactive=False)

    async def get_page(self, view: str) -> Dict[str, Any]:
        """根据视图标识获取单个导航页面。

        Args:
            view: 导航页面的唯一视图标识符

        Returns:
            导航页面的详细信息字典

        Raises:
            NavigationPageNotFoundError: 当指定的视图不存在时抛出异常

        功能说明：
        1. 首先确保默认页面已存在
        2. 根据view字段查找对应的导航页面
        3. 只返回未被删除的页面
        4. 如果未找到页面，抛出相应的异常
        """
        await self.ensure_default_pages()
        doc = await NavigationPageDoc.find_one(
            NavigationPageDoc.view == view,
            {"is_deleted": False},
        )
        if not doc:
            raise NavigationPageNotFoundError("navigation page not found")
        return self._doc_to_dict(doc)

    async def create_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的导航页面。

        Args:
            data: 包含导航页面信息的字典，必须包含以下字段：
                 - view: 唯一视图标识符（必填）
                 - label: 导航显示名称（必填）
                 - permission: 访问权限码（可选，默认为 "nav:public"）
                               * "nav:public": 所有登录用户可见的公共页面
                               * "nav:xxx:view": 需要特定权限的页面
                 - description: 页面描述（可选）
                 - order: 显示顺序，数值越小越靠前（可选，默认为0）
                 - is_active: 是否激活状态（可选，默认为True）

        Returns:
            创建的导航页面信息字典

        Raises:
            ValueError: 当view字段为空或已存在时抛出异常

        功能说明：
        1. 验证必填字段（view不能为空）
        2. 检查view的唯一性，防止重复创建
        3. 处理软删除的页面恢复逻辑
        4. 权限字段优化：未提供permission时自动设置为nav:public（公共页面）
        5. 构造完整的页面数据并插入数据库
        6. 返回创建后的页面信息
        """
        view = str(data.get("view", "")).strip()
        if not view:
            raise ValueError("view must not be empty")

        existing = await NavigationPageDoc.find_one(NavigationPageDoc.view == view)
        if existing and not existing.is_deleted:
            raise ValueError("view already exists")

        # 改进权限处理逻辑
        permission = data.get("permission")
        if permission is None:
            # 如果未提供permission，默认为公共页面（所有登录用户可见）
            permission = "nav:public"

        payload = {
            "view": view,
            "label": data["label"],
            "permission": permission,
            "description": data.get("description"),
            "order": int(data.get("order", 0)),
            "is_active": bool(data.get("is_active", True)),
            "is_deleted": False,
        }

        if existing and existing.is_deleted:
            # 如果页面存在但已被标记为删除，则恢复该页面
            self._apply_updates(existing, payload, set(payload.keys()))
            await existing.save()
            return self._doc_to_dict(existing)

        doc = NavigationPageDoc(**payload)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def update_page(self, view: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新现有的导航页面。

        Args:
            view: 要更新的页面视图标识符
            data: 包含更新数据的字典，仅允许更新以下字段：
                 - label: 导航显示名称
                 - permission: 访问权限码
                 - description: 页面描述
                 - order: 显示顺序
                 - is_active: 激活状态

        Returns:
            更新后的导航页面信息字典

        Raises:
            NavigationPageNotFoundError: 当指定的页面不存在时抛出异常

        功能说明：
        1. 根据view查找要更新的页面
        2. 只允许更新_UPDATABLE_FIELDS中定义的字段，保证数据安全
        3. 如果页面不存在则抛出异常
        4. 执行更新操作并返回更新后的结果
        """
        doc = await NavigationPageDoc.find_one(
            NavigationPageDoc.view == view,
            {"is_deleted": False},
        )
        if not doc:
            raise NavigationPageNotFoundError("navigation page not found")
        self._apply_updates(doc, data, self._UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_page(self, view: str) -> None:
        """软删除指定的导航页面。

        Args:
            view: 要删除的页面视图标识符

        Raises:
            NavigationPageNotFoundError: 当指定的页面不存在时抛出异常

        功能说明：
        1. 软删除机制：将is_deleted字段设置为True，而不是物理删除
        2. 保持数据完整性，便于后续的数据恢复和审计
        3. 被软删除的页面在正常查询中不可见，但可通过管理接口恢复
        4. 如果页面不存在则抛出相应的异常

        注意：该方法不会真的删除数据库记录，只是标记为已删除状态
        """
        doc = await NavigationPageDoc.find_one(
            NavigationPageDoc.view == view,
            {"is_deleted": False},
        )
        if not doc:
            raise NavigationPageNotFoundError("navigation page not found")
        doc.is_deleted = True
        await doc.save()
