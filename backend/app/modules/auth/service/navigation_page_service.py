"""导航页面管理服务。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.modules.auth.repository.models import NavigationPageDoc
from app.modules.auth.service.exceptions import NavigationPageNotFoundError
from app.shared.service import BaseService


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
        "permission": "nav:my_tasks:view",
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
    """导航页面 CRUD + 默认数据初始化。"""

    _UPDATABLE_FIELDS = {"label", "permission", "description", "order", "is_active"}

    async def ensure_default_pages(self) -> None:
        """在导航集合为空时初始化默认页面（惰性兜底）。"""
        active_count = await NavigationPageDoc.find({"is_deleted": False}).count()
        if active_count > 0:
            return

        for item in DEFAULT_NAVIGATION_PAGES:
            view = item["view"]
            await NavigationPageDoc.find_one(NavigationPageDoc.view == view).upsert(
                {
                    "$set": {
                        "label": item["label"],
                        "permission": item.get("permission"),
                        "description": item.get("description"),
                        "order": item.get("order", 0),
                        "is_active": bool(item.get("is_active", True)),
                        "is_deleted": False,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                on_insert=NavigationPageDoc(
                    view=view,
                    label=item["label"],
                    permission=item.get("permission"),
                    description=item.get("description"),
                    order=item.get("order", 0),
                    is_active=bool(item.get("is_active", True)),
                    is_deleted=False,
                ),
            )

    async def list_pages(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        await self.ensure_default_pages()
        query = NavigationPageDoc.find({"is_deleted": False})
        if not include_inactive:
            query = query.find(NavigationPageDoc.is_active == True)  # noqa: E712
        docs = await query.sort("order", "view").to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def list_active_pages(self) -> List[Dict[str, Any]]:
        return await self.list_pages(include_inactive=False)

    async def get_page(self, view: str) -> Dict[str, Any]:
        await self.ensure_default_pages()
        doc = await NavigationPageDoc.find_one(
            NavigationPageDoc.view == view,
            {"is_deleted": False},
        )
        if not doc:
            raise NavigationPageNotFoundError("navigation page not found")
        return self._doc_to_dict(doc)

    async def create_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        view = str(data.get("view", "")).strip()
        if not view:
            raise ValueError("view must not be empty")

        existing = await NavigationPageDoc.find_one(NavigationPageDoc.view == view)
        if existing and not existing.is_deleted:
            raise ValueError("view already exists")

        payload = {
            "view": view,
            "label": data["label"],
            "permission": data.get("permission"),
            "description": data.get("description"),
            "order": int(data.get("order", 0)),
            "is_active": bool(data.get("is_active", True)),
            "is_deleted": False,
        }

        if existing and existing.is_deleted:
            self._apply_updates(existing, payload, set(payload.keys()))
            await existing.save()
            return self._doc_to_dict(existing)

        doc = NavigationPageDoc(**payload)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def update_page(self, view: str, data: Dict[str, Any]) -> Dict[str, Any]:
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
        doc = await NavigationPageDoc.find_one(
            NavigationPageDoc.view == view,
            {"is_deleted": False},
        )
        if not doc:
            raise NavigationPageNotFoundError("navigation page not found")
        doc.is_deleted = True
        await doc.save()
