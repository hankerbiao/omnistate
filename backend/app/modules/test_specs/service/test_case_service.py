"""测试用例服务"""
from typing import Dict, Any, Optional, List
from app.modules.test_specs.repository.models import TestCaseDoc, TestRequirementDoc


class TestCaseService:
    """测试用例 CRUD 服务（异步）"""

    async def create_test_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure_requirement_exists(data["ref_req_id"])
        existing = await TestCaseDoc.find_one(TestCaseDoc.case_id == data["case_id"])
        if existing:
            raise ValueError("case_id already exists")
        doc = TestCaseDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_test_case(self, case_id: str) -> Dict[str, Any]:
        doc = await TestCaseDoc.find_one(TestCaseDoc.case_id == case_id)
        if not doc:
            raise KeyError("test case not found")
        return self._doc_to_dict(doc)

    async def list_test_cases(
        self,
        ref_req_id: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        priority: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = TestCaseDoc.find()
        if ref_req_id:
            query = query.find(TestCaseDoc.ref_req_id == ref_req_id)
        if status:
            query = query.find(TestCaseDoc.status == status)
        if owner_id:
            query = query.find(TestCaseDoc.owner_id == owner_id)
        if reviewer_id:
            query = query.find(TestCaseDoc.reviewer_id == reviewer_id)
        if priority:
            query = query.find(TestCaseDoc.priority == priority)
        if is_active is not None:
            query = query.find(TestCaseDoc.is_active == is_active)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_test_case(self, case_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await TestCaseDoc.find_one(TestCaseDoc.case_id == case_id)
        if not doc:
            raise KeyError("test case not found")
        if "ref_req_id" in data:
            await self._ensure_requirement_exists(data["ref_req_id"])
        for key, value in data.items():
            setattr(doc, key, value)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_test_case(self, case_id: str) -> None:
        doc = await TestCaseDoc.find_one(TestCaseDoc.case_id == case_id)
        if not doc:
            raise KeyError("test case not found")
        await doc.delete()

    @staticmethod
    async def _ensure_requirement_exists(req_id: str) -> None:
        existing = await TestRequirementDoc.find_one(TestRequirementDoc.req_id == req_id)
        if not existing:
            raise KeyError("requirement not found")

    @staticmethod
    def _doc_to_dict(doc) -> Dict[str, Any]:
        data = doc.model_dump()
        data["id"] = str(doc.id)
        return data
