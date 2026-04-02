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
    @staticmethod
    def get_mongo_client_or_none() -> AsyncMongoClient | None:
        try:
            return get_mongo_client()
        except RuntimeError:
            return None

    @staticmethod
    def is_transaction_not_supported(exc: Exception) -> bool:
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
        try:
            existing_item = await BusWorkItemDoc.find_one(
                {"type_code": type_code, "title": title, "is_deleted": False},
                session=session,
            )
            if existing_item:
                raise ValueError(f"已存在相同标题的{type_code}: {title}")

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
        item_doc = await get_work_item_doc(work_item_id, session=session)
        if not item_doc or item_doc.is_deleted:
            logger.error(f"流转失败: 未找到业务事项 ID={work_item_id}")
            raise WorkItemNotFoundError(work_item_id)

        config_doc = await SysWorkflowConfigDoc.find_one(
            {"type_code": item_doc.type_code, "from_state": item_doc.current_state, "action": action},
            session=session,
        )
        if not config_doc:
            logger.error(f"流转失败: 非法操作。当前状态 {item_doc.current_state} 不支持动作 {action}")
            raise InvalidTransitionError(item_doc.current_state, action)

        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_transition(actor, item_doc, config_doc):
            raise PermissionDeniedError(operator_id, "transition")

        ensure_required_fields(config_doc.required_fields, form_data)
        process_payload = build_process_payload(config_doc.required_fields, form_data)

        old_state = item_doc.current_state
        new_state = config_doc.to_state
        new_owner_id = resolve_owner(
            strategy=config_doc.target_owner_strategy,
            work_item=item_doc.model_dump(),
            form_data=form_data,
        )

        item_doc.current_state = new_state
        item_doc.current_owner_id = new_owner_id
        await save_doc(item_doc, session=session)

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
        item_doc = await get_work_item_doc(item_id, session=session)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)
        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_delete_work_item(actor, item_doc):
            raise PermissionDeniedError(operator_id, "delete")

        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(item_id),
            from_state=item_doc.current_state,
            to_state=item_doc.current_state,
            action="DELETE",
            operator_id=operator_id,
            payload={"info": "Soft deleted"},
        )
        await insert_doc(log_entry, session=session)

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
        item_doc = await BusWorkItemDoc.get(item_id)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)

        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_reassign(actor, item_doc):
            raise PermissionDeniedError(operator_id, "reassign")

        payload: dict[str, Any] = {"target_owner_id": target_owner_id}
        if remark is not None:
            payload["remark"] = remark

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
