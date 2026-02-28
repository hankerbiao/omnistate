"""测试需求服务（RequirementService）

AI 友好注释说明：
- 本服务负责「测试需求」的 CRUD，以及与工作流事项（work_item）的联动。
- 需求创建是跨集合写入：先创建 workflow 事项，再写入 requirement 文档。
- 为避免脏数据，优先使用 MongoDB 事务；若部署环境不支持事务，则降级为补偿模式。

一致性策略：
1. 事务模式（首选）：
   - 在同一个 session/transaction 中完成 workflow + requirement 的创建。
   - 任一步失败，事务整体回滚，不产生孤儿数据。
2. 补偿模式（降级）：
   - 若事务不可用，先创建 workflow，再写 requirement。
   - 若写 requirement 失败，尝试补偿删除 workflow 事项。
   - 若补偿也失败，记录异常日志，便于后续人工修复。
"""
from copy import deepcopy
from typing import Dict, Any, Optional, List
from pymongo import AsyncMongoClient
from app.modules.test_specs.repository.models import TestRequirementDoc, TestCaseDoc
from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.shared.core.logger import log as logger
from app.shared.core.mongo_client import get_mongo_client
from app.shared.service import BaseService


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
        "status",
        "attachments",
    }

    async def create_requirement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建测试需求。

        输入：
        - data: 前端/上层传入的需求字段，至少包含 req_id/title/tpm_owner_id。

        核心流程：
        1. 深拷贝输入，避免调用方持有的字典被本方法原地修改。
        2. 尝试获取全局 Mongo 客户端（用于启动事务）。
        3. 若可用，优先走事务创建路径。
        4. 若事务不被当前 Mongo 部署支持，降级为补偿创建路径。

        返回：
        - 标准化后的 requirement 字典（包含 id/workflow_item_id/status 等）。
        """
        payload = deepcopy(data)
        client = self._get_mongo_client_or_none()

        if client is not None:
            try:
                # 优先使用事务，确保 workflow 与 requirement 原子写入。
                return await self._create_requirement_with_transaction(client, payload)
            except Exception as exc:
                if self._is_transaction_not_supported(exc):
                    logger.warning("MongoDB 不支持事务，降级为补偿写入模式: create_requirement")
                else:
                    raise

        return await self._create_requirement_with_compensation(payload)

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

    async def _create_requirement_with_compensation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """补偿模式创建需求（事务不可用时的降级路径）。

        一致性保障思路：
        - 先创建 workflow 事项。
        - 若 requirement 插入失败，则尝试补偿删除 workflow 事项，避免孤儿数据。
        """
        existing = await TestRequirementDoc.find_one(TestRequirementDoc.req_id == payload["req_id"])
        if existing:
            raise ValueError("req_id already exists")

        workflow_service = AsyncWorkflowService()
        workflow_item_id: Optional[str] = None

        try:
            workflow_item = await workflow_service.create_item(
                type_code="REQUIREMENT",
                title=payload["title"],
                content=payload.get("description") or payload["title"],
                creator_id=payload["tpm_owner_id"],
                parent_item_id=None,
            )
            workflow_item_id = workflow_item["id"]

            payload["workflow_item_id"] = workflow_item_id
            payload["status"] = payload.get("status") or workflow_item.get("current_state") or "待指派"
            doc = TestRequirementDoc(**payload)
            await doc.insert()
            return self._doc_to_dict(doc)
        except Exception:
            # requirement 写入失败时，回滚前一步创建的 workflow 事项。
            if workflow_item_id:
                await self._compensate_delete_workflow_item(workflow_item_id)
            raise

    @staticmethod
    def _get_mongo_client_or_none() -> Optional[AsyncMongoClient]:
        """获取全局 Mongo 客户端。

        返回 None 表示当前运行上下文未初始化客户端（例如某些测试环境）。
        """
        try:
            return get_mongo_client()
        except RuntimeError:
            return None

    @staticmethod
    def _is_transaction_not_supported(exc: Exception) -> bool:
        """判断异常是否属于「部署不支持事务」。

        注意：
        - 这里采用关键字匹配是为了兼容不同 Mongo 版本/驱动的报错文本。
        - 仅在确认是能力缺失时降级；其它异常继续抛出。
        """
        message = str(exc).lower()
        return (
            "transaction numbers are only allowed on a replica set member" in message
            or "this mongodb deployment does not support retryable writes" in message
            or "sessions are not supported" in message
        )

    @staticmethod
    async def _compensate_delete_workflow_item(workflow_item_id: str) -> None:
        """执行补偿删除 workflow 事项。

        设计原则：
        - 补偿失败不吞掉，写异常日志（包含 work_item_id）用于审计与修复。
        - 此方法不抛业务异常，避免覆盖原始失败原因。
        """
        try:
            await AsyncWorkflowService().delete_item(workflow_item_id)
            logger.warning(f"需求创建失败，已补偿删除工作流事项: {workflow_item_id}")
        except Exception as rollback_error:
            logger.exception(
                f"需求创建失败且补偿删除工作流事项失败: work_item_id={workflow_item_id}, error={rollback_error}"
            )
