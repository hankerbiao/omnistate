"""测试需求服务"""
from typing import Dict, Any, Optional, List
from app.modules.test_specs.repository.models import TestRequirementDoc


class RequirementService:
    """测试需求 CRUD 服务（异步）"""

    async def create_requirement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == data["req_id"]
        )
        if existing:
            raise ValueError("req_id already exists")
        doc = TestRequirementDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_requirement(self, req_id: str) -> Dict[str, Any]:
        doc = await TestRequirementDoc.find_one(TestRequirementDoc.req_id == req_id)
        if not doc:
            raise KeyError("requirement not found")
        return self._doc_to_dict(doc)

    async def list_requirements(
        self,
        status: Optional[str] = None,
        tpm_owner_id: Optional[str] = None,
        manual_dev_id: Optional[str] = None,
        auto_dev_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = TestRequirementDoc.find()
        if status:
            query = query.find(TestRequirementDoc.status == status)
        if tpm_owner_id:
            query = query.find(TestRequirementDoc.tpm_owner_id == tpm_owner_id)
        if manual_dev_id:
            query = query.find(TestRequirementDoc.manual_dev_id == manual_dev_id)
        if auto_dev_id:
            query = query.find(TestRequirementDoc.auto_dev_id == auto_dev_id)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_requirement(self, req_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await TestRequirementDoc.find_one(TestRequirementDoc.req_id == req_id)
        if not doc:
            raise KeyError("requirement not found")
        for key, value in data.items():
            setattr(doc, key, value)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_requirement(self, req_id: str) -> None:
        doc = await TestRequirementDoc.find_one(TestRequirementDoc.req_id == req_id)
        if not doc:
            raise KeyError("requirement not found")
        await doc.delete()

    @staticmethod
    def _doc_to_dict(doc) -> Dict[str, Any]:
        data = doc.model_dump()
        data["id"] = str(doc.id)
        return data
