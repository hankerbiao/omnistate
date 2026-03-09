"""测试用例服务

负责测试用例的CRUD操作，以及与需求、自动化用例的关联。
使用MongoDB事务确保原子性：在一个事务中完成workflow + test_case的创建。

主要功能：
1. 测试用例的增删改查
2. 与需求文档的关联验证
3. 与自动化测试用例的关联管理
4. 分布式ID生成（基于MongoDB计数器）

一致性策略：
- 事务模式（唯一模式）：
   - 在同一个session/transaction中完成workflow + test_case的创建。
   - 任一步失败，事务整体回滚，不产生孤儿数据。
   - 要求：MongoDB必须支持事务（Replica Set或Sharded Cluster）
"""

from copy import deepcopy
from typing import Dict, Any, Optional, List
from datetime import datetime
from pymongo import AsyncMongoClient
from app.modules.test_specs.repository.models import (
    TestCaseDoc,
    TestRequirementDoc,
    AutomationTestCaseDoc,
    AutomationCaseRef,
)
from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.shared.core.logger import log as logger
from app.shared.core.mongo_client import get_mongo_client
from app.shared.service import BaseService, SequenceIdService


class TestCaseService(BaseService):
    """测试用例 CRUD 服务（异步）"""
    _UPDATABLE_FIELDS = {
        "title",
        "version",
        "is_active",
        "change_log",
        "owner_id",
        "reviewer_id",
        "auto_dev_id",
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
        "cleanup_steps",
        "steps",
        "is_need_auto",
        "is_automated",
        "automation_type",
        "script_entity_id",
        "automation_case_ref",
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
        """创建测试用例（仅事务模式）

        要求：
        - 环境必须支持MongoDB事务
        - 事务内完成workflow + test_case的原子写入
        """
        payload = deepcopy(data)
        payload["case_id"] = await self._generate_case_id()
        client = self._get_mongo_client_or_none()

        if client is None:
            raise RuntimeError("MongoDB客户端未初始化，无法创建测试用例")

        # 仅使用事务模式，确保workflow与test_case原子写入
        return await self._create_test_case_with_transaction(client, payload)

    async def get_test_case(self, case_id: str) -> Dict[str, Any]:
        """根据case_id获取单个测试用例"""
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
        """分页查询测试用例列表，支持多种过滤条件"""
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
        """更新测试用例信息

        注意：status字段是工作流状态的投影，不能通过此方法直接修改。
        状态变更必须通过工作流转换进行。
        """
        # 明确禁止修改status字段（投影字段）
        if "status" in data:
            raise ValueError(
                "status is a workflow state projection and cannot be updated directly. "
                "Use workflow transition to change state."
            )

        doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("test case not found")
        self._apply_updates(doc, data, self._UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_test_case(self, case_id: str) -> None:
        """逻辑删除测试用例。

        当前阶段要求已绑定 workflow 的用例必须走 workflow-aware 删除路径，
        避免业务文档与工作项出现分裂删除状态。
        """
        doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("test case not found")
        if doc.workflow_item_id:
            raise ValueError("delete test case through workflow-aware path only")
        doc.is_deleted = True
        await doc.save()

    async def link_automation_case(
        self,
        case_id: str,
        auto_case_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """将自动化测试用例关联到手工测试用例"""
        case_doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not case_doc:
            raise KeyError("test case not found")

        # 查找自动化测试用例
        auto_query = AutomationTestCaseDoc.find(
            AutomationTestCaseDoc.auto_case_id == auto_case_id,
            {"is_deleted": False},
        )
        if version:
            auto_query = auto_query.find(AutomationTestCaseDoc.version == version)
        auto_doc = await auto_query.sort("-updated_at").first_or_none()
        if not auto_doc:
            raise KeyError("automation test case not found")

        # 关联自动化用例
        case_doc.automation_case_ref = AutomationCaseRef(
            auto_case_id=auto_doc.auto_case_id,
            version=auto_doc.version,
        )
        case_doc.is_need_auto = True
        case_doc.is_automated = True
        case_doc.automation_type = auto_doc.automation_type or case_doc.automation_type
        case_doc.script_entity_id = auto_doc.script_entity_id or case_doc.script_entity_id

        if not case_doc.custom_fields:
            case_doc.custom_fields = {}
        case_doc.custom_fields["automation_case_id"] = auto_doc.auto_case_id
        case_doc.custom_fields["automation_case_version"] = auto_doc.version

        await case_doc.save()
        return self._doc_to_dict(case_doc)

    async def unlink_automation_case(self, case_id: str) -> Dict[str, Any]:
        """解除自动化测试用例的关联"""
        case_doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not case_doc:
            raise KeyError("test case not found")

        case_doc.automation_case_ref = None
        case_doc.is_automated = False
        if case_doc.custom_fields:
            case_doc.custom_fields.pop("automation_case_id", None)
            case_doc.custom_fields.pop("automation_case_version", None)

        await case_doc.save()
        return self._doc_to_dict(case_doc)

    async def _create_test_case_with_transaction(
        self,
        client: AsyncMongoClient,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """使用事务模式创建测试用例（推荐）"""
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
    @staticmethod
    def _get_mongo_client_or_none() -> Optional[AsyncMongoClient]:
        """获取MongoDB客户端，如果未初始化则返回None"""
        try:
            return get_mongo_client()
        except RuntimeError:
            return None

    @staticmethod
    async def _ensure_requirement_exists(req_id: str, session=None) -> TestRequirementDoc:
        """验证需求是否存在"""
        existing = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            {"is_deleted": False},
            session=session,
        )
        if not existing:
            raise KeyError("requirement not found")
        return existing

    async def _generate_case_id(self) -> str:
        """自动生成测试用例编号。

        格式：TC-YYYY-XXXXX（例如：TC-2026-00001）
        确保在并发场景下唯一性。
        """
        year = datetime.now().year
        prefix = f"TC-{year}-"
        counter_key = f"test_case:{year}"
        next_seq = await SequenceIdService().next(counter_key)

        return f"{prefix}{str(next_seq).zfill(5)}"
