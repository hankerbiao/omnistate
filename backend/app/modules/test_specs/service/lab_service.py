"""Test Lab CRUD and lifecycle service."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.modules.test_specs.domain.exceptions import LabConflictError, LabNotFoundError
from app.modules.test_specs.repository.models import TestCaseDoc, TestLabDoc
from app.shared.core.mongo_client import get_mongo_client
from app.shared.service import BaseService


class LabService(BaseService):
    """Manage catalog L1 labs."""

    _UPDATABLE_FIELDS = {"name", "description", "sort_order"}

    async def list_labs(self, active_only: bool = False) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if active_only:
            query["is_active"] = True

        docs = await TestLabDoc.find(query).sort("+sort_order", "+code").to_list()
        results: list[dict[str, Any]] = []
        for doc in docs:
            data = self._doc_to_dict(doc)
            data["case_count"] = await self._count_cases(doc.lab_id)
            results.append(data)
        return results

    async def create_lab(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(data)
        code = str(payload.get("code", "")).strip()
        name = str(payload.get("name", "")).strip()

        if not code:
            raise ValueError("Lab code 不能为空")
        if not name:
            raise ValueError("Lab 名称不能为空")

        existing = await TestLabDoc.find_one({"code": code})
        if existing:
            raise LabConflictError(f"Lab code={code} 已存在")

        lab_id = f"LAB-{code}"
        if await TestLabDoc.find_one({"lab_id": lab_id}):
            raise LabConflictError(f"Lab ID={lab_id} 已存在")

        doc = TestLabDoc(
            lab_id=lab_id,
            code=code,
            name=name,
            description=payload.get("description"),
            sort_order=int(payload.get("sort_order") or 0),
            is_active=True,
        )
        await doc.insert()
        result = self._doc_to_dict(doc)
        result["case_count"] = 0
        return result

    async def update_lab(self, lab_id: str, data: dict[str, Any]) -> dict[str, Any]:
        doc = await self._get_lab_or_raise(lab_id)
        updates = self._filter_updates(data, self._UPDATABLE_FIELDS)

        if "name" in updates:
            name = str(updates["name"]).strip()
            if not name:
                raise ValueError("Lab 名称不能为空")
            updates["name"] = name

        self._apply_updates(doc, updates, self._UPDATABLE_FIELDS)
        await doc.save()

        result = self._doc_to_dict(doc)
        result["case_count"] = await self._count_cases(lab_id)
        return result

    async def deactivate_lab(self, lab_id: str, target_lab_id: str) -> dict[str, Any]:
        if lab_id == target_lab_id:
            raise ValueError("目标 Lab 不能与源 Lab 相同")

        source = await self._get_lab_or_raise(lab_id)
        target = await self._get_lab_or_raise(target_lab_id)

        if not target.is_active:
            raise LabConflictError(f"目标 Lab {target_lab_id} 未启用")

        migrated = await self._migrate_cases(lab_id, target_lab_id)
        source.is_active = False
        await source.save()

        result = self._doc_to_dict(source)
        result["case_count"] = 0
        result["migrated_case_count"] = migrated
        return result

    async def delete_lab(self, lab_id: str) -> None:
        doc = await self._get_lab_or_raise(lab_id)
        case_count = await self._count_cases(lab_id)
        if case_count > 0:
            raise LabConflictError(f"Lab {lab_id} 下仍有 {case_count} 条用例，无法删除")
        await doc.delete()

    async def _get_lab_or_raise(self, lab_id: str) -> TestLabDoc:
        doc = await TestLabDoc.find_one({"lab_id": lab_id})
        if not doc:
            raise LabNotFoundError(lab_id)
        return doc

    async def _count_cases(self, lab_id: str) -> int:
        collection = TestCaseDoc.get_pymongo_collection()
        return await collection.count_documents({"lab_id": lab_id, "is_deleted": False})

    async def _migrate_cases(self, source_lab_id: str, target_lab_id: str) -> int:
        client = get_mongo_client()
        if client is None:
            return await self._migrate_cases_without_transaction(source_lab_id, target_lab_id)

        async with client.start_session() as session:
            async with await session.start_transaction():
                return await self._migrate_cases_without_transaction(
                    source_lab_id,
                    target_lab_id,
                    session=session,
                )

    async def _migrate_cases_without_transaction(
        self,
        source_lab_id: str,
        target_lab_id: str,
        session=None,
    ) -> int:
        collection = TestCaseDoc.get_pymongo_collection()
        now = datetime.now(timezone.utc)
        result = await collection.update_many(
            {"lab_id": source_lab_id, "is_deleted": False},
            {"$set": {"lab_id": target_lab_id, "updated_at": now}},
            session=session,
        )
        return result.modified_count
