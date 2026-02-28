"""测试用例服务"""
from copy import deepcopy
from typing import Dict, Any, Optional, List
from pymongo import AsyncMongoClient
from app.modules.test_specs.repository.models import TestCaseDoc, TestRequirementDoc
from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.shared.core.logger import log as logger
from app.shared.core.mongo_client import get_mongo_client
from app.shared.service import BaseService


class TestCaseService(BaseService):
    """测试用例 CRUD 服务（异步）"""
    _UPDATABLE_FIELDS = {
        "ref_req_id",
        "title",
        "version",
        "is_active",
        "change_log",
        "owner_id",
        "reviewer_id",
        "priority",
        "estimated_duration_sec",
        "target_components",
        "required_env",
        "tags",
        "test_category",
        "tooling_req",
        "is_destructive",
        "pre_condition",
        "post_condition",
        "steps",
        "is_need_auto",
        "is_automated",
        "automation_type",
        "script_entity_id",
        "risk_level",
        "failure_analysis",
        "confidentiality",
        "visibility_scope",
        "attachments",
        "custom_fields",
        "deprecation_reason",
        "approval_history",
    }

    async def create_test_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = deepcopy(data)
        client = self._get_mongo_client_or_none()

        if client is not None:
            try:
                return await self._create_test_case_with_transaction(client, payload)
            except Exception as exc:
                if self._is_transaction_not_supported(exc):
                    logger.warning("MongoDB 不支持事务，降级为补偿写入模式: create_test_case")
                else:
                    raise

        return await self._create_test_case_with_compensation(payload)

    async def get_test_case(self, case_id: str) -> Dict[str, Any]:
        doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
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
        query = TestCaseDoc.find({"is_deleted": False})
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
        doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("test case not found")
        if "ref_req_id" in data:
            await self._ensure_requirement_exists(data["ref_req_id"])
        self._apply_updates(doc, data, self._UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_test_case(self, case_id: str) -> None:
        doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("test case not found")
        doc.is_deleted = True
        await doc.save()

    async def _create_test_case_with_transaction(
        self,
        client: AsyncMongoClient,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        workflow_service = AsyncWorkflowService()

        async with client.start_session() as session:
            async with await session.start_transaction():
                requirement = await self._ensure_requirement_exists(payload["ref_req_id"], session=session)
                existing = await TestCaseDoc.find_one(
                    TestCaseDoc.case_id == payload["case_id"],
                    session=session,
                )
                if existing:
                    raise ValueError("case_id already exists")

                workflow_item = await workflow_service.create_item(
                    type_code="TEST_CASE",
                    title=payload["title"],
                    content=payload.get("pre_condition") or payload.get("post_condition") or payload["title"],
                    creator_id=payload.get("owner_id") or payload.get("reviewer_id") or "system",
                    parent_item_id=requirement.workflow_item_id,
                    session=session,
                )
                payload["workflow_item_id"] = workflow_item["id"]
                payload["status"] = workflow_item["current_state"]

                doc = TestCaseDoc(**payload)
                await doc.insert(session=session)
                return self._doc_to_dict(doc)

    async def _create_test_case_with_compensation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        requirement = await self._ensure_requirement_exists(payload["ref_req_id"])
        existing = await TestCaseDoc.find_one(TestCaseDoc.case_id == payload["case_id"])
        if existing:
            raise ValueError("case_id already exists")

        workflow_service = AsyncWorkflowService()
        workflow_item_id: Optional[str] = None

        try:
            workflow_item = await workflow_service.create_item(
                type_code="TEST_CASE",
                title=payload["title"],
                content=payload.get("pre_condition") or payload.get("post_condition") or payload["title"],
                creator_id=payload.get("owner_id") or payload.get("reviewer_id") or "system",
                parent_item_id=requirement.workflow_item_id,
            )
            workflow_item_id = workflow_item["id"]
            payload["workflow_item_id"] = workflow_item_id
            payload["status"] = workflow_item["current_state"]

            doc = TestCaseDoc(**payload)
            await doc.insert()
            return self._doc_to_dict(doc)
        except Exception:
            if workflow_item_id:
                await self._compensate_delete_workflow_item(workflow_item_id)
            raise

    @staticmethod
    def _get_mongo_client_or_none() -> Optional[AsyncMongoClient]:
        try:
            return get_mongo_client()
        except RuntimeError:
            return None

    @staticmethod
    def _is_transaction_not_supported(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "transaction numbers are only allowed on a replica set member" in message
            or "this mongodb deployment does not support retryable writes" in message
            or "sessions are not supported" in message
        )

    @staticmethod
    async def _compensate_delete_workflow_item(workflow_item_id: str) -> None:
        try:
            await AsyncWorkflowService().delete_item(workflow_item_id)
            logger.warning(f"测试用例创建失败，已补偿删除工作流事项: {workflow_item_id}")
        except Exception as rollback_error:
            logger.exception(
                f"测试用例创建失败且补偿删除工作流事项失败: work_item_id={workflow_item_id}, error={rollback_error}"
            )

    @staticmethod
    async def _ensure_requirement_exists(req_id: str, session=None) -> TestRequirementDoc:
        existing = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            {"is_deleted": False},
            session=session,
        )
        if not existing:
            raise KeyError("requirement not found")
        return existing
