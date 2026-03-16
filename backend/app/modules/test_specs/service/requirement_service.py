"""测试需求服务（RequirementService）

- 负责「测试需求」的 CRUD，以及与工作流事项（work_item）的联动。
- 需求创建是跨集合写入：先创建 workflow 事项，再写入 requirement 文档。
- 使用 MongoDB 事务确保原子性：在一个事务中完成 workflow + requirement 的创建。

一致性策略：
- 事务模式（唯一模式）：
   - 在同一个 session/transaction 中完成 workflow + requirement 的创建。
   - 任一步失败，事务整体回滚，不产生孤儿数据。
   - 要求：MongoDB 必须支持事务（Replica Set 或 Sharded Cluster）
"""
from copy import deepcopy
from typing import Dict, Any, Optional, List
from datetime import datetime
from pymongo import AsyncMongoClient
from app.modules.test_specs.repository.models import TestRequirementDoc, TestCaseDoc
from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.modules.workflow.repository.models.business import BusWorkItemDoc
from app.shared.core.logger import log as logger
from app.shared.core.mongo_client import get_mongo_client
from app.shared.service import BaseService, SequenceIdService


class RequirementService(BaseService):
    """测试需求 CRUD 服务（异步）"""
    _UPDATABLE_FIELDS = {
        "title",
        "description",
        "technical_spec",
        "target_components",
        "firmware_version",
        "priority",
        "key_parameters",
        "risk_points",
        "attachments",
        # Phase 4: 高风险字段已移至显式命令，不允许通过通用更新修改
        # - 负责人字段：通过 assign_owners 命令修改
        # - 工作流字段：通过工作流命令修改
        # - 业务ID和关联：通过显式命令修改
    }

    def __init__(self):
        super().__init__()
        self.workflow_service = AsyncWorkflowService()
        self._workflow_service = self.workflow_service

    async def _enrich_requirement_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """使用工作流状态覆盖业务文档中的状态投影字段。"""
        workflow_item_id = str(data.get("workflow_item_id") or "").strip()
        if not workflow_item_id:
            return data

        work_item = await BusWorkItemDoc.get(workflow_item_id)
        if work_item and not work_item.is_deleted:
            data["status"] = work_item.current_state
        return data

    async def _get_workflow_state_for_requirement(self, req_id: str) -> Optional[str]:
        """从工作流获取需求的真实状态（单一真实来源）。

        这是Phase 3B的关键实现：确保状态从工作流源读取，而不是业务文档投影字段。
        """
        # 先获取需求文档的workflow_item_id
        requirement = await TestRequirementDoc.find_one({
            "req_id": req_id,
            "is_deleted": False
        })
        if not requirement or not requirement.workflow_item_id:
            return None

        # 根据workflow_item_id查找对应的工作项状态
        work_item = await BusWorkItemDoc.get(requirement.workflow_item_id)
        return work_item.current_state if work_item and not work_item.is_deleted else None

    async def _get_workflow_states_for_requirements(self, req_ids: List[str]) -> Dict[str, str]:
        """批量获取需求的工作流状态。

        使用这个方法比逐个查询更高效。
        """
        if not req_ids:
            return {}

        # 先获取需求文档和对应的workflow_item_id
        requirements = await TestRequirementDoc.find({
            "req_id": {"$in": req_ids},
            "is_deleted": False
        }).to_list()

        workflow_id_map = {req.req_id: req.workflow_item_id for req in requirements if req.workflow_item_id}
        if not workflow_id_map:
            return {}

        # 批量获取工作项状态
        workflow_ids = list(workflow_id_map.values())
        work_items = await BusWorkItemDoc.find({
            "id": {"$in": workflow_ids},
            "is_deleted": False
        }).to_list()

        # 构建映射：req_id -> current_state
        state_map = {}
        for req_id, workflow_id in workflow_id_map.items():
            work_item = next((item for item in work_items if str(item.id) == workflow_id), None)
            if work_item:
                state_map[req_id] = work_item.current_state

        return state_map

    async def create_requirement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建测试需求（仅事务模式）。

        要求：
        - 环境必须支持MongoDB事务
        - 事务内完成workflow + requirement的原子写入

        输入：
        - data: 前端/上层传入的需求字段，至少包含 title/tpm_owner_id。
                注意：req_id 不允许由前端提供，必须由后端强制生成以保证唯一性。

        返回：
        - 标准化后的 requirement 字典（包含 id/workflow_item_id/status 等）。
        """
        payload = deepcopy(data)

        # 强制生成新的 req_id，不接受前端提供的任何值
        # 这是为了保证唯一性和避免冲突
        payload["req_id"] = await self._generate_req_id()
        logger.info(f"后端生成需求编号: req_id={payload['req_id']}")

        client = self._get_mongo_client_or_none()
        if client is None:
            raise RuntimeError("MongoDB客户端未初始化，无法创建需求")

        # 仅使用事务模式，确保workflow与requirement原子写入
        return await self._create_requirement_with_transaction(client, payload)

    async def get_requirement(self, req_id: str) -> Dict[str, Any]:
        """按 req_id 查询单条需求（仅返回未逻辑删除数据）。"""
        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("requirement not found")
        return await self._enrich_requirement_status(self._doc_to_dict(doc))

    async def list_requirements(
        self,
        status: Optional[str] = None,
        tpm_owner_id: Optional[str] = None,
        manual_dev_id: Optional[str] = None,
        auto_dev_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """分页查询需求列表，支持按状态/角色负责人过滤。

        Phase 3B重构：状态过滤从工作流源查询，确保单一真实来源。

        说明：
        - 默认只查询未逻辑删除数据（is_deleted=False）。
        - 各过滤条件采用 AND 关系叠加。
        - 状态过滤通过工作流查询实现，其他条件在业务文档上过滤。
        """
        # Phase 3B: 先从业务文档查询非状态条件
        query = TestRequirementDoc.find({"is_deleted": False})
        if tpm_owner_id:
            query = query.find(TestRequirementDoc.tpm_owner_id == tpm_owner_id)
        if manual_dev_id:
            query = query.find(TestRequirementDoc.manual_dev_id == manual_dev_id)
        if auto_dev_id:
            query = query.find(TestRequirementDoc.auto_dev_id == auto_dev_id)

        # 获取候选文档（如果需要状态过滤，先获取更大的集合）
        if status:
            docs = await query.sort("-created_at").to_list()
            if not docs:
                return []

            req_ids = [doc.req_id for doc in docs]
            workflow_states = await self._get_workflow_states_for_requirements(req_ids)
            filtered_docs = [
                doc for doc in docs
                if workflow_states.get(doc.req_id) == status
                or (workflow_states.get(doc.req_id) is None and status == "未开始")
            ]
            docs = filtered_docs[offset:offset + limit]
        else:
            docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()

        # Phase 3B: 转换时确保使用工作流状态作为真实来源
        result = []
        if docs:
            req_ids = [doc.req_id for doc in docs]
            workflow_states = await self._get_workflow_states_for_requirements(req_ids)

            for doc in docs:
                doc_dict = self._doc_to_dict(doc)
                # 关键：使用工作流状态覆盖业务文档中的投影状态
                workflow_state = workflow_states.get(doc.req_id)
                if workflow_state:
                    doc_dict["status"] = workflow_state
                result.append(doc_dict)

        return result

    async def update_requirement(self, req_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新需求内容字段（仅限安全的内容更新）。

        Phase 4: 高风险操作必须通过显式命令进行，不允许通过此通用更新方法。
        - 负责人修改：使用 assign_owners 命令
        - 工作流状态：使用工作流转换
        - 业务ID和关联：使用显式命令

        Args:
            req_id: 需求ID
            data: 内容更新数据（仅限内容字段）

        Returns:
            更新后的需求文档

        Raises:
            KeyError: 需求不存在时抛出
            ValueError: 尝试更新高风险字段时抛出
        """
        # Phase 4: 强化验证 - 检查是否尝试更新高风险字段
        high_risk_fields = {
            'req_id', 'workflow_item_id', 'status', 'is_deleted',
            'tpm_owner_id', 'manual_dev_id', 'auto_dev_id',
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

        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("requirement not found")
        self._apply_updates(doc, data, self._UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def assign_owners(self, req_id: str, tpm_owner_id: str | None = None, manual_dev_id: str | None = None, auto_dev_id: str | None = None) -> Dict[str, Any]:
        """分配需求负责人（Phase 4显式命令）。

        这是Phase 4的核心实现：负责人分配必须通过显式命令，不能通过通用更新。

        Args:
            req_id: 需求ID
            tpm_owner_id: 项目经理/产品经理ID
            manual_dev_id: 手工测试开发工程师ID
            auto_dev_id: 自动化开发工程师ID

        Returns:
            更新后的需求文档

        Raises:
            KeyError: 需求不存在时抛出
            ValueError: 没有任何负责人被指定时抛出
        """
        if not any([tpm_owner_id, manual_dev_id, auto_dev_id]):
            raise ValueError("at least one owner must be specified")

        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("requirement not found")

        # 更新负责人字段（明确指定每个字段的更新）
        if tpm_owner_id is not None:
            doc.tpm_owner_id = tpm_owner_id
        if manual_dev_id is not None:
            doc.manual_dev_id = manual_dev_id
        if auto_dev_id is not None:
            doc.auto_dev_id = auto_dev_id

        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_requirement(self, req_id: str) -> None:
        """逻辑删除需求。

        业务约束：
        - 若需求下存在未删除的测试用例，不允许删除该需求。
        - 若需求已绑定 workflow 事项，当前阶段必须走 workflow-aware 删除路径。
        """
        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("requirement not found")
        if doc.workflow_item_id:
            raise ValueError("delete requirement through workflow-aware path only")
        # 若存在关联用例（未删除），则不允许删除需求
        related_cases = await TestCaseDoc.find(
            TestCaseDoc.ref_req_id == req_id,
            {"is_deleted": False},
        ).count()
        if related_cases > 0:
            raise ValueError("requirement has related test cases")
        doc.is_deleted = True
        await doc.save()

    async def _create_requirement_with_transaction(
        self,
        client: AsyncMongoClient,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """事务模式创建需求（推荐路径）。

        事务内步骤：
        1. 校验 req_id 唯一性。
        2. 创建 workflow 事项（type=REQUIREMENT）。
        3. 将 workflow_item_id/current_state 回填到需求文档。
        4. 插入 requirement 文档并提交事务。
        """
        workflow_service = AsyncWorkflowService()

        async with client.start_session() as session:
            async with await session.start_transaction():
                existing = await TestRequirementDoc.find_one(
                    TestRequirementDoc.req_id == payload["req_id"],
                    session=session,
                )
                if existing:
                    raise ValueError("req_id already exists")

                # 在同一事务上下文内创建 workflow 事项，确保跨集合原子性。
                workflow_item = await workflow_service.create_item(
                    type_code="REQUIREMENT",
                    title=payload["title"],
                    content=payload.get("description") or payload["title"],
                    creator_id=payload["tpm_owner_id"],
                    parent_item_id=None,
                    session=session,
                )

                payload["workflow_item_id"] = workflow_item["id"]
                payload["status"] = payload.get("status") or workflow_item.get("current_state") or "待指派"
                doc = TestRequirementDoc(**payload)
                await doc.insert(session=session)
                return self._doc_to_dict(doc)

    @staticmethod
    def _get_mongo_client_or_none() -> Optional[AsyncMongoClient]:
        """获取全局 Mongo 客户端。

        返回 None 表示当前运行上下文未初始化客户端（例如某些测试环境）。
        """
        try:
            return get_mongo_client()
        except RuntimeError:
            return None

    async def _generate_req_id(self) -> str:
        """自动生成需求编号。

        格式：TR-YYYY-XXXXX（例如：TR-2026-00001）
        确保在并发场景下唯一性。
        """
        year = datetime.now().year
        prefix = f"TR-{year}-"
        counter_key = f"test_requirement:{year}"
        next_seq = await SequenceIdService().next(counter_key)

        return f"{prefix}{str(next_seq).zfill(5)}"
