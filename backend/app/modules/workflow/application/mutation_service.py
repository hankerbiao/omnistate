from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import DuplicateKeyError

from app.modules.workflow.application.common import get_work_item_doc, insert_doc, save_doc, serialize_work_item
from app.modules.workflow.domain.exceptions import (
    InvalidTransitionError,
    PermissionDeniedError,
    WorkItemNotFoundError,
)
from app.modules.workflow.domain.policies import can_delete_work_item, can_reassign, can_transition
from app.modules.workflow.domain.rules import build_process_payload, ensure_required_fields, resolve_owner
from app.modules.workflow.repository.models import (
    BusFlowLogDoc,
    BusWorkItemDoc,
    SysWorkflowConfigDoc,
    WorkItemState,
)
from app.shared.core.logger import log as logger
from app.shared.core.mongo_client import get_mongo_client


class WorkflowMutationService:
    """工作流写操作服务。

    负责工作项的创建、状态流转、删除和重新分配。
    这里把事务控制、权限校验、状态机校验和审计日志统一收敛在一起，
    避免这些规则散落到 API 层或仓储层。
    """

    @staticmethod
    def get_mongo_client_or_none() -> AsyncMongoClient | None:
        # 从全局上下文读取 Mongo 客户端；如果还没有初始化就返回 None。
        try:
            return get_mongo_client()
        except RuntimeError:
            return None

    @staticmethod
    def is_transaction_not_supported(exc: Exception) -> bool:
        # 兼容不同 MongoDB 部署的报错文案，用于判断当前环境是否支持事务。
        message = str(exc).lower()
        return (
            "transaction numbers are only allowed on a replica set member" in message
            or "this mongodb deployment does not support retryable writes" in message
            or "sessions are not supported" in message
        )

    async def create_item(
        self,
        type_code: str,
        title: str,
        content: str,
        creator_id: str,
        parent_item_id: str | None = None,
        session: AsyncClientSession | None = None,
    ) -> dict[str, Any]:
        """创建新的工作项。

        主要流程：
        1. 检查同类型、同标题的工作项是否已存在
        2. 校验并转换父节点 ID
        3. 以 DRAFT 状态创建工作项
        4. 返回序列化后的结果
        """
        try:
            # 避免同一业务类型下出现重复标题，减少后续检索和流转歧义。
            existing_item = await BusWorkItemDoc.find_one(
                {"type_code": type_code, "title": title, "is_deleted": False},
                session=session,
            )
            if existing_item:
                raise ValueError(f"已存在相同标题的{type_code}: {title}")

            # 父事项 ID 只在合法 ObjectId 时才保留，非法值直接忽略并记录告警。
            parent_oid = None
            if parent_item_id:
                if PydanticObjectId.is_valid(parent_item_id):
                    parent_oid = PydanticObjectId(parent_item_id)
                else:
                    logger.warning(f"无效的父事项 ID: {parent_item_id}，将忽略 parent_item_id")

            new_item = BusWorkItemDoc(
                type_code=type_code,
                title=title,
                content=content,
                parent_item_id=parent_oid,
                creator_id=creator_id,
                current_owner_id=creator_id,
                current_state=WorkItemState.DRAFT.value,
            )
            await new_item.insert(session=session)
            logger.success(f"业务事项创建成功: ID={new_item.id}, state={new_item.current_state}")
            return serialize_work_item(new_item)
        except DuplicateKeyError as exc:
            logger.warning(f"业务事项并发创建冲突(type_code={type_code}, title={title}): {exc}")
            raise ValueError(f"已存在相同标题的{type_code}: {title}")
        except Exception as exc:
            logger.error(f"创建业务事项失败: {exc}")
            raise

    async def handle_transition(
        self,
        work_item_id: str,
        action: str,
        operator_id: str,
        form_data: dict[str, Any],
        actor_role_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """处理工作项状态流转。

        这里使用 MongoDB session + transaction，确保“读取当前状态、校验规则、
        更新工作项、写入流转日志”这几个步骤要么同时成功，要么同时失败。
        """
        logger.info(f"开始处理状态流转: work_item_id={work_item_id}, action={action}, operator={operator_id}")
        client = self.get_mongo_client_or_none()
        if client is None:
            logger.error("MongoDB 客户端未初始化，无法执行原子状态流转")
            raise RuntimeError("workflow transition requires initialized MongoDB client")

        try:
            async with client.start_session() as session:
                async with await session.start_transaction():
                    return await self._handle_transition_core(
                        work_item_id=work_item_id,
                        action=action,
                        operator_id=operator_id,
                        form_data=form_data,
                        actor_role_ids=actor_role_ids,
                        session=session,
                    )
        except Exception as exc:
            if self.is_transaction_not_supported(exc):
                logger.error("MongoDB 部署不支持事务，已拒绝执行非原子状态流转")
                raise RuntimeError("workflow transition requires MongoDB transaction support") from exc
            raise

    async def _handle_transition_core(
        self,
        work_item_id: str,
        action: str,
        operator_id: str,
        form_data: dict[str, Any],
        actor_role_ids: list[str] | None,
        session: AsyncClientSession | None,
    ) -> dict[str, Any]:
        # 先读取当前工作项，确认它存在且没有被软删除。
        item_doc = await get_work_item_doc(work_item_id, session=session)
        if not item_doc or item_doc.is_deleted:
            logger.error(f"流转失败: 未找到业务事项 ID={work_item_id}")
            raise WorkItemNotFoundError(work_item_id)

        # 按 type_code + 当前状态 + action 查找允许的流转配置。
        config_doc = await SysWorkflowConfigDoc.find_one(
            {"type_code": item_doc.type_code, "from_state": item_doc.current_state, "action": action},
            session=session,
        )
        if not config_doc:
            logger.error(f"流转失败: 非法操作。当前状态 {item_doc.current_state} 不支持动作 {action}")
            raise InvalidTransitionError(item_doc.current_state, action)

        # 先做权限校验，再做字段校验和状态变更。
        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_transition(actor, item_doc, config_doc):
            raise PermissionDeniedError(operator_id, "transition")

        # 校验流转所需表单字段，并组装审计/流程处理载荷。
        ensure_required_fields(config_doc.required_fields, form_data)
        process_payload = build_process_payload(config_doc.required_fields, form_data)

        old_state = item_doc.current_state
        new_state = config_doc.to_state
        new_owner_id = resolve_owner(
            strategy=config_doc.target_owner_strategy,
            work_item=item_doc.model_dump(),
            form_data=form_data,
        )

        # 更新工作项状态和当前处理人。
        item_doc.current_state = new_state
        item_doc.current_owner_id = new_owner_id
        await save_doc(item_doc, session=session)

        # 写入流转日志，保留审计轨迹。
        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(work_item_id),
            from_state=old_state,
            to_state=new_state,
            action=action,
            operator_id=operator_id,
            payload=process_payload,
        )
        await insert_doc(log_entry, session=session)

        logger.success(f"状态流转完成: ID={work_item_id}, new_state={new_state}")
        item_dict = serialize_work_item(item_doc)
        return {
            "work_item_id": str(item_doc.id),
            "from_state": old_state,
            "to_state": new_state,
            "action": action,
            "new_owner_id": new_owner_id,
            "work_item": item_dict,
        }

    async def delete_item(
        self,
        item_id: str,
        operator_id: str,
        actor_role_ids: list[str] | None = None,
    ) -> bool:
        """逻辑删除工作项。

        这里不做物理删除，而是先写日志，再标记 `is_deleted=True`，
        以保留历史审计信息和后续追踪能力。
        """
        client = self.get_mongo_client_or_none()
        if client is None:
            logger.error("MongoDB 客户端未初始化，无法执行原子删除")
            raise RuntimeError("workflow delete requires initialized MongoDB client")
        try:
            async with client.start_session() as session:
                async with await session.start_transaction():
                    return await self._delete_item_core(
                        item_id=item_id,
                        operator_id=operator_id,
                        actor_role_ids=actor_role_ids,
                        session=session,
                    )
        except Exception as exc:
            if self.is_transaction_not_supported(exc):
                logger.error("MongoDB 部署不支持事务，已拒绝执行非原子删除")
                raise RuntimeError("workflow delete requires MongoDB transaction support") from exc
            raise

    async def _delete_item_core(
        self,
        item_id: str,
        operator_id: str,
        actor_role_ids: list[str] | None,
        session: AsyncClientSession | None,
    ) -> bool:
        # 先确认目标工作项存在且未删除。
        item_doc = await get_work_item_doc(item_id, session=session)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)
        # 删除同样需要权限控制。
        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_delete_work_item(actor, item_doc):
            raise PermissionDeniedError(operator_id, "delete")

        # 删除前先写审计日志，记录这一动作和当时状态。
        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(item_id),
            from_state=item_doc.current_state,
            to_state=item_doc.current_state,
            action="DELETE",
            operator_id=operator_id,
            payload={"info": "Soft deleted"},
        )
        await insert_doc(log_entry, session=session)

        # 这里采用软删除，保留历史数据和流转痕迹。
        item_doc.is_deleted = True
        await save_doc(item_doc, session=session)
        logger.success(f"事项 ID={item_id} 已逻辑删除")
        return True

    async def reassign_item(
        self,
        item_id: str,
        operator_id: str,
        target_owner_id: str,
        remark: str | None = None,
        actor_role_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """重新分配工作项当前负责人。

        该操作不改变状态，只改变 `current_owner_id`，同时写入一条流转日志，
        便于后续审计和追踪。
        """
        item_doc = await BusWorkItemDoc.get(item_id)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)

        # 重新分配同样受权限策略控制。
        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_reassign(actor, item_doc):
            raise PermissionDeniedError(operator_id, "reassign")

        # 记录新的负责人和可选备注，作为审计载荷。
        payload: dict[str, Any] = {"target_owner_id": target_owner_id}
        if remark is not None:
            payload["remark"] = remark

        # 记录一次“负责人变更”日志，但状态本身不变。
        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(item_id),
            from_state=item_doc.current_state,
            to_state=item_doc.current_state,
            action="REASSIGN",
            operator_id=operator_id,
            payload=payload,
        )
        await log_entry.insert()

        item_doc.current_owner_id = target_owner_id
        await item_doc.save()
        return serialize_work_item(item_doc)
