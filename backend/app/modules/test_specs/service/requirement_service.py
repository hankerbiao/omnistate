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
        "tpm_owner_id",
        "manual_dev_id",
        "auto_dev_id",
        "attachments",
    }

    def __init__(self):
        super().__init__()

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
        """分页查询需求列表，支持按状态/角色负责人过滤。

        说明：
        - 默认只查询未逻辑删除数据（is_deleted=False）。
        - 各过滤条件采用 AND 关系叠加。
        """
        query = TestRequirementDoc.find({"is_deleted": False})
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
        """更新需求可编辑字段（白名单控制）。"""
        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("requirement not found")
        self._apply_updates(doc, data, self._UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_requirement(self, req_id: str) -> None:
        """逻辑删除需求。

        业务约束：
        - 若需求下存在未删除的测试用例，不允许删除该需求。
        """
        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == req_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("requirement not found")
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
            async with  session.start_transaction():
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
