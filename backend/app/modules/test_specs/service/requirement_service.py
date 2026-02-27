"""测试需求服务"""
from typing import Dict, Any, Optional, List
from app.modules.test_specs.repository.models import TestRequirementDoc, TestCaseDoc
from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.shared.service import BaseService


class RequirementService(BaseService):
    """测试需求 CRUD 服务（异步）"""
    _UPDATABLE_FIELDS = {
        "title",
        "description",
        "target_components",
        "tpm_owner_id",
        "manual_dev_id",
        "auto_dev_id",
        "status",
    }

    async def create_requirement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == data["req_id"]
        )
        if existing:
            raise ValueError("req_id already exists")

        # 1) 创建工作流事项（使用 tpm_owner_id 作为创建者）
        workflow_service = AsyncWorkflowService()
        workflow_item = await workflow_service.create_item(
            type_code="REQUIREMENT",
            title=data["title"],
            content=data.get("description") or data["title"],
            creator_id=data["tpm_owner_id"],
            parent_item_id=None,
        )

        # 2) 写回 workflow_item_id 与初始状态
        data["workflow_item_id"] = workflow_item["id"]
        data["status"] = workflow_item["current_state"]
        doc = TestRequirementDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_requirement(self, req_id: str) -> Dict[str, Any]:
        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            TestRequirementDoc.is_deleted == False,
        )
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
        query = TestRequirementDoc.find(TestRequirementDoc.is_deleted == False)
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
        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            TestRequirementDoc.is_deleted == False,
        )
        if not doc:
            raise KeyError("requirement not found")
        self._apply_updates(doc, data, self._UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_requirement(self, req_id: str) -> None:
        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            TestRequirementDoc.is_deleted == False,
        )
        if not doc:
            raise KeyError("requirement not found")
        # 若存在关联用例（未删除），则不允许删除需求
        related_cases = await TestCaseDoc.find(
            TestCaseDoc.ref_req_id == req_id,
            TestCaseDoc.is_deleted == False,
        ).count()
        if related_cases > 0:
            raise ValueError("requirement has related test cases")
        doc.is_deleted = True
        await doc.save()
