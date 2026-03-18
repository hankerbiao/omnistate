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
)
from app.modules.test_specs.service._workflow_status_support import enrich_projected_status, get_workflow_states
from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.shared.core.mongo_client import get_mongo_client
from app.shared.service import BaseService, SequenceIdService


class TestCaseService(BaseService):
    """测试用例 CRUD 服务（异步）"""
    _UPDATABLE_FIELDS = {
        "title",
        "version",
        "is_active",
        "change_log",
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
        "risk_level",
        "failure_analysis",
        "confidentiality",
        "visibility_scope",
        "attachments",
        "custom_fields",
        "deprecation_reason",
        "approval_history",
        # Phase 4: 高风险字段已移至显式命令，不允许通过通用更新修改
        # - ref_req_id：通过 move_to_requirement 命令修改
        # - 负责人字段：通过 assign_owners 命令修改
        # - 工作流字段：通过工作流命令修改
        # - 业务ID和关联：通过显式命令修改
    }

    async def _enrich_test_case_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """使用工作流状态覆盖业务文档中的状态投影字段。"""
        return await enrich_projected_status(data)

    async def _get_workflow_states_for_test_cases(self, case_ids: List[str]) -> Dict[str, str]:
        """批量获取测试用例的工作流状态。

        使用这个方法比逐个查询更高效。
        """
        if not case_ids:
            return {}

        # 先获取测试用例文档和对应的workflow_item_id
        test_cases = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False
        }).to_list()

        return await get_workflow_states(test_cases, "case_id")

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
        return await self._enrich_test_case_status(self._doc_to_dict(doc))

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
        """分页查询测试用例列表，支持多种过滤条件。

        Phase 3B重构：状态过滤从工作流源查询，确保单一真实来源。
        """
        # Phase 3B: 先从业务文档查询非状态条件
        query = TestCaseDoc.find({"is_deleted": False})
        if ref_req_id:
            query = query.find(TestCaseDoc.ref_req_id == ref_req_id)
        if owner_id:
            query = query.find(TestCaseDoc.owner_id == owner_id)
        if reviewer_id:
            query = query.find(TestCaseDoc.reviewer_id == reviewer_id)
        if priority:
            query = query.find(TestCaseDoc.priority == priority)
        if is_active is not None:
            query = query.find(TestCaseDoc.is_active == is_active)

        # 获取候选文档（如果需要状态过滤，先获取更大的集合）
        if status:
            docs = await query.sort("-created_at").to_list()
            if not docs:
                return []

            case_ids = [doc.case_id for doc in docs]
            workflow_states = await self._get_workflow_states_for_test_cases(case_ids)
            filtered_docs = [
                doc for doc in docs
                if (
                    workflow_states.get(doc.case_id) == status
                    or (workflow_states.get(doc.case_id) is None and status == "未开始")
                )
            ]
            docs = filtered_docs[offset:offset + limit]
        else:
            docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()

        # Phase 3B: 转换时确保使用工作流状态作为真实来源
        result = []
        if docs:
            case_ids = [doc.case_id for doc in docs]
            workflow_states = await self._get_workflow_states_for_test_cases(case_ids)

            for doc in docs:
                doc_dict = self._doc_to_dict(doc)
                # 关键：使用工作流状态覆盖业务文档中的投影状态
                workflow_state = workflow_states.get(doc.case_id)
                if workflow_state:
                    doc_dict["status"] = workflow_state
                result.append(doc_dict)

        return result

    async def update_test_case(self, case_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新测试用例内容字段（仅限安全的内容更新）。

        Phase 4: 高风险操作必须通过显式命令进行，不允许通过此通用更新方法。
        - 需求关联修改：使用 move_to_requirement 命令
        - 负责人修改：使用 assign_owners 命令
        - 工作流状态：使用工作流转换
        - 业务ID和关联：使用显式命令

        Args:
            case_id: 测试用例ID
            data: 内容更新数据（仅限内容字段）

        Returns:
            更新后的测试用例文档

        Raises:
            KeyError: 测试用例不存在时抛出
            ValueError: 尝试更新高风险字段时抛出
        """
        # Phase 4: 强化验证 - 检查是否尝试更新高风险字段
        high_risk_fields = {
            'case_id', 'ref_req_id', 'workflow_item_id', 'status', 'is_deleted',
            'owner_id', 'reviewer_id', 'auto_dev_id',
            'created_at', 'updated_at'
        }
        conflicts = set(data.keys()) & high_risk_fields
        if conflicts:
            raise ValueError(
                f"cannot update high-risk fields through generic update: {conflicts}. "
                f"Use explicit commands instead. Allowed fields: {self._UPDATABLE_FIELDS}"
            )

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

        # 查找自动化测试用例。当前模型仅保留最新版本，version 参数仅用于兼容接口签名。
        auto_doc = await AutomationTestCaseDoc.find_one(
            AutomationTestCaseDoc.auto_case_id == auto_case_id,
            {"is_deleted": False},
        )
        if not auto_doc:
            raise KeyError("automation test case not found")

        if auto_doc.source_case_id != case_doc.case_id:
            raise ValueError("automation test case source_case_id does not match test case case_id")
        await case_doc.save()
        return self._doc_to_dict(case_doc)

    async def assign_owners(self, case_id: str, owner_id: str | None = None, reviewer_id: str | None = None,
                            auto_dev_id: str | None = None) -> Dict[str, Any]:
        """分配测试用例负责人（Phase 4显式命令）。

        这是Phase 4的核心实现：负责人分配必须通过显式命令，不能通过通用更新。

        Args:
            case_id: 测试用例ID
            owner_id: 负责人ID
            reviewer_id: 审核人ID
            auto_dev_id: 自动化开发工程师ID

        Returns:
            更新后的测试用例文档

        Raises:
            KeyError: 测试用例不存在时抛出
            ValueError: 没有任何负责人被指定时抛出
        """
        if not any([owner_id, reviewer_id, auto_dev_id]):
            raise ValueError("at least one owner must be specified")

        doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("test case not found")

        # 更新负责人字段（明确指定每个字段的更新）
        if owner_id is not None:
            doc.owner_id = owner_id
        if reviewer_id is not None:
            doc.reviewer_id = reviewer_id
        if auto_dev_id is not None:
            doc.auto_dev_id = auto_dev_id

        await doc.save()
        return self._doc_to_dict(doc)

    async def move_to_requirement(self, case_id: str, target_req_id: str) -> Dict[str, Any]:
        """将测试用例移动到不同需求（Phase 4显式命令）。

        这是Phase 4的核心实现：用例迁移必须通过显式命令，不能通过通用更新。

        Args:
            case_id: 测试用例ID
            target_req_id: 目标需求ID

        Returns:
            更新后的测试用例文档

        Raises:
            KeyError: 测试用例或目标需求不存在时抛出
            ValueError: 目标需求ID与当前相同时抛出
        """
        # 验证测试用例存在
        case_doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not case_doc:
            raise KeyError("test case not found")

        # 验证目标需求存在
        target_req = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == target_req_id,
            {"is_deleted": False},
        )
        if not target_req:
            raise KeyError("target requirement not found")

        if case_doc.ref_req_id == target_req_id:
            raise ValueError("test case is already linked to the target requirement")

        # 更新ref_req_id
        case_doc.ref_req_id = target_req_id
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
