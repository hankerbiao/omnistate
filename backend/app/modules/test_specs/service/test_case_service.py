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
from app.modules.test_specs.service._service_support import (
    apply_workflow_status_projection,
    create_with_workflow_transaction,
    ensure_safe_generic_update,
    load_workflow_states_for_entities,
    workflow_aware_soft_delete,
)
from app.modules.test_specs.service._workflow_status_support import enrich_projected_status
from app.modules.workflow.application import WorkflowItemGateway
from app.modules.attachments.repository.models import AttachmentDoc
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
        "required_env",
        "tags",
        "test_category",
        "is_destructive",
        "pre_condition",
        "post_condition",
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

    def __init__(self, workflow_gateway: WorkflowItemGateway) -> None:
        self._workflow_gateway = workflow_gateway

    async def _enrich_test_case_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """使用工作流状态补齐测试用例响应中的派生状态字段。"""
        return await enrich_projected_status(data)

    async def _get_workflow_states_for_test_cases(self, case_ids: List[str]) -> Dict[str, str]:
        """批量获取测试用例的工作流状态。"""
        return await load_workflow_states_for_entities(
            doc_cls=TestCaseDoc,
            ids=case_ids,
            id_field="case_id",
        )

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
        if not docs:
            return []

        case_ids = [doc.case_id for doc in docs]
        workflow_states = await self._get_workflow_states_for_test_cases(case_ids)
        return await apply_workflow_status_projection(
            docs=docs,
            id_getter=lambda doc: doc.case_id,
            to_dict=self._doc_to_dict,
            workflow_states=workflow_states,
        )

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
        ensure_safe_generic_update(
            data=data,
            high_risk_fields={
                'case_id', 'ref_req_id', 'workflow_item_id', 'status', 'is_deleted',
                'owner_id', 'reviewer_id', 'auto_dev_id',
                'created_at', 'updated_at'
            },
            allowed_fields=self._UPDATABLE_FIELDS,
        )

        doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("test case not found")
        self._apply_updates(doc, data, self._UPDATABLE_FIELDS)
        await doc.save()
        return await self._enrich_test_case_status(self._doc_to_dict(doc))

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
        await workflow_aware_soft_delete(
            doc=doc,
            workflow_item_id=doc.workflow_item_id,
            workflow_error_message="delete test case through workflow-aware path only",
        )

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

        if auto_doc.dml_manual_case_id != case_doc.case_id:
            raise ValueError("automation test case dml_manual_case_id does not match test case case_id")
        await case_doc.save()
        return await self._enrich_test_case_status(self._doc_to_dict(case_doc))

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
        return await self._enrich_test_case_status(self._doc_to_dict(doc))

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

        return await self._enrich_test_case_status(self._doc_to_dict(case_doc))

    async def _create_test_case_with_transaction(
            self,
            client: AsyncMongoClient,
            payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """使用事务模式创建测试用例（推荐）"""
        async def _prepare_payload(data: Dict[str, Any], session) -> None:
            if data.get("attachments"):
                data["attachments"] = await self._validate_and_enrich_attachments(
                    data["attachments"],
                    session=session,
                )
            requirement = await self._ensure_requirement_exists(data["ref_req_id"], session=session)
            data["_parent_workflow_item_id"] = requirement.workflow_item_id

        def _workflow_item_factory(data: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "type_code": "TEST_CASE",
                "title": data["title"],
                "content": data.get("pre_condition") or data.get("post_condition") or data["title"],
                "creator_id": data.get("owner_id") or data.get("reviewer_id") or "system",
                "parent_item_id": data.pop("_parent_workflow_item_id"),
            }

        return await create_with_workflow_transaction(
            client=client,
            payload=payload,
            doc_cls=TestCaseDoc,
            unique_lookup=lambda data: TestCaseDoc.case_id == data["case_id"],
            duplicate_error_message="case_id already exists",
            workflow_gateway=self._workflow_gateway,
            workflow_item_factory=_workflow_item_factory,
            enrich_result=lambda doc: self._enrich_test_case_status(self._doc_to_dict(doc)),
            prepare_payload=_prepare_payload,
        )

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

    async def _validate_and_enrich_attachments(
        self,
        attachments: List[Dict[str, Any]],
        session=None,
    ) -> List[Dict[str, Any]]:
        """验证附件有效性并补全附件信息

        前端提交表单时携带 file_id，后端需要：
        1. 验证 file_id 对应的附件是否存在且未被删除
        2. 查询并补全完整的附件信息（storage_path, original_filename, size, content_type）

        Args:
            attachments: 附件列表，每个附件应包含 file_id 字段
            session: MongoDB 事务会话（可选）

        Returns:
            补全后的附件列表

        Raises:
            KeyError: 附件不存在或已被删除时抛出
        """
        if not attachments:
            return []

        enriched_attachments = []
        for att in attachments:
            file_id = att.get("file_id")
            if not file_id:
                raise ValueError("attachment missing required field: file_id")

            # 验证附件是否存在
            attachment = await AttachmentDoc.find_one(
                {"file_id": file_id, "is_deleted": False},
                session=session,
            )
            if not attachment:
                raise KeyError(f"attachment not found or deleted: {file_id}")

            # 补全附件信息
            enriched_attachments.append({
                "file_id": attachment.file_id,
                "original_filename": attachment.original_filename,
                "storage_path": f"{attachment.bucket}/{attachment.object_name}",
                "size": attachment.size,
                "content_type": attachment.content_type,
                "uploaded_at": attachment.uploaded_at.isoformat() if attachment.uploaded_at else None,
                # 保留前端可能传递的其他字段（如 description）
                **{k: v for k, v in att.items() if k != "file_id"},
            })

        return enriched_attachments

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
