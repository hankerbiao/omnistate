"""用例集合核心服务。"""
import re
from datetime import datetime
from typing import List, Optional

from app.modules.test_case_collection.repository.models import TestCaseCollectionDoc
from app.modules.test_case_collection.schemas import (
    AddCasesRequest,
    CollectionListItem,
    CollectionResponse,
    CreateCollectionRequest,
    RemoveCasesRequest,
    UpdateCollectionRequest,
)
from app.modules.test_case_collection.service.exceptions import (
    CollectionNotFoundError,
)
from app.shared.service import SequenceIdService


class TestCaseCollectionService:
    """用例集合服务。"""

    def __init__(self):
        self._sequence_service = SequenceIdService()

    async def create(self, request: CreateCollectionRequest, creator_id: str) -> CollectionResponse:
        """创建用例集合。"""
        seq = await self._sequence_service.next("test_case_collection")
        collection_id = f"CC-{str(seq).zfill(4)}"

        doc = TestCaseCollectionDoc(
            collection_id=collection_id,
            name=request.name,
            description=request.description,
            tags=request.tags,
            case_ids=list(set(request.case_ids)),
            auto_case_ids=list(set(request.auto_case_ids)),
            created_by=creator_id,
        )
        await doc.insert()
        return CollectionResponse.from_doc(doc)

    async def get(self, collection_id: str) -> CollectionResponse:
        """获取集合详情。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")
        return CollectionResponse.from_doc(doc)

    async def update(self, collection_id: str, request: UpdateCollectionRequest) -> CollectionResponse:
        """更新集合基本信息。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.tags is not None:
            updates["tags"] = request.tags
        updates["updated_at"] = datetime.utcnow()

        await doc.update({"$set": updates})
        doc = await TestCaseCollectionDoc.find_one({"collection_id": collection_id})
        return CollectionResponse.from_doc(doc) if doc else await self.get(collection_id)

    async def delete(self, collection_id: str) -> None:
        """逻辑删除集合。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")
        await doc.update({"$set": {"is_active": False, "updated_at": datetime.utcnow()}})

    async def add_cases(self, collection_id: str, request: AddCasesRequest) -> CollectionResponse:
        """向集合添加用例（去重）。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        new_case_ids = list(set(doc.case_ids + request.case_ids))
        new_auto_ids = list(set(doc.auto_case_ids + request.auto_case_ids))
        await doc.update({
            "$set": {
                "case_ids": new_case_ids,
                "auto_case_ids": new_auto_ids,
                "updated_at": datetime.utcnow(),
            }
        })
        doc.case_ids = new_case_ids
        doc.auto_case_ids = new_auto_ids
        return CollectionResponse.from_doc(doc)

    async def remove_cases(self, collection_id: str, request: RemoveCasesRequest) -> CollectionResponse:
        """从集合移除用例。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        remove_set = set(request.case_ids)
        remove_auto_set = set(request.auto_case_ids)
        new_case_ids = [c for c in doc.case_ids if c not in remove_set]
        new_auto_ids = [c for c in doc.auto_case_ids if c not in remove_auto_set]
        await doc.update({
            "$set": {
                "case_ids": new_case_ids,
                "auto_case_ids": new_auto_ids,
                "updated_at": datetime.utcnow(),
            }
        })
        doc.case_ids = new_case_ids
        doc.auto_case_ids = new_auto_ids
        return CollectionResponse.from_doc(doc)

    async def list_all(self, query: Optional[str] = None) -> List[CollectionListItem]:
        """查询集合列表，支持模糊搜索。"""
        filter_expr: dict = {"is_active": True}

        if query:
            pattern = re.escape(query.strip())
            filter_expr["$or"] = [
                {"name": {"$regex": pattern, "$options": "i"}},
                {"description": {"$regex": pattern, "$options": "i"}},
                {"tags": {"$regex": pattern, "$options": "i"}},
            ]

        docs = await TestCaseCollectionDoc.find(filter_expr).sort(
            -TestCaseCollectionDoc.updated_at
        ).to_list()
        return [CollectionListItem.from_doc(d) for d in docs]

    async def search(self, q: str, limit: int = 10) -> List[CollectionListItem]:
        """快速搜索集合（用于任务创建时的下拉选择）。"""
        pattern = re.escape(q.strip())
        docs = await TestCaseCollectionDoc.find(
            {
                "is_active": True,
                "$or": [
                    {"name": {"$regex": pattern, "$options": "i"}},
                    {"tags": {"$regex": pattern, "$options": "i"}},
                ],
            }
        ).limit(limit).to_list()
        return [CollectionListItem.from_doc(d) for d in docs]
