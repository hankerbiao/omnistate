from __future__ import annotations

from typing import Any, Awaitable, Callable, Iterable

from pymongo import AsyncMongoClient

from app.modules.test_specs.service._workflow_status_support import get_workflow_states, get_workflow_details


async def load_workflow_states_for_entities(
    *,
    doc_cls: Any,
    ids: list[str],
    id_field: str,
) -> dict[str, str]:
    """Load workflow states for business entities by their business identifier."""
    if not ids:
        return {}

    docs = await doc_cls.find(
        {
            id_field: {"$in": ids},
            "is_deleted": False,
        }
    ).to_list()
    return await get_workflow_states(docs, id_field)


def apply_workflow_status_projection(
    *,
    docs: list[Any],
    id_getter: Callable[[Any], str],
    to_dict: Callable[[Any], dict[str, Any]],
    workflow_states: dict[str, str],
    default_status: str = "未开始",
) -> list[dict[str, Any]]:
    """Project workflow states into serialized entity payloads."""
    details = {k: {"status": v} for k, v in workflow_states.items()}
    return apply_workflow_details_projection(
        docs=docs, id_getter=id_getter, to_dict=to_dict,
        workflow_details=details, default_status=default_status,
    )


def apply_workflow_details_projection(
    *,
    docs: list[Any],
    id_getter: Callable[[Any], str],
    to_dict: Callable[[Any], dict[str, Any]],
    workflow_details: dict[str, dict[str, Any]],
    default_status: str = "未开始",
) -> list[dict[str, Any]]:
    """Project workflow details (status, creator, current_owner) into serialized entity payloads."""
    result: list[dict[str, Any]] = []
    for doc in docs:
        doc_dict = to_dict(doc)
        details = workflow_details.get(id_getter(doc), {})
        doc_dict["status"] = details.get("status", default_status)
        doc_dict["creator"] = details.get("creator")
        doc_dict["current_owner"] = details.get("current_owner")
        doc_dict["creator_name"] = details.get("creator_name")
        doc_dict["current_owner_name"] = details.get("current_owner_name")
        result.append(doc_dict)
    return result


def ensure_safe_generic_update(
    *,
    data: dict[str, Any],
    high_risk_fields: Iterable[str],
    allowed_fields: Iterable[str],
) -> None:
    """Reject updates to fields that must go through explicit commands."""
    conflicts = set(data.keys()) & set(high_risk_fields)
    if conflicts:
        raise ValueError(
            f"cannot update high-risk fields through generic update: {conflicts}. "
            f"Use explicit commands instead. Allowed fields: {set(allowed_fields)}"
        )

    if "status" in data:
        raise ValueError(
            "status is a workflow state projection and cannot be updated directly. "
            "Use workflow transition to change state."
        )


async def workflow_aware_soft_delete(
    *,
    doc: Any,
    workflow_item_id: str | None,
    workflow_error_message: str,
    extra_guard: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """Soft delete an entity only when it is no longer bound to workflow state.

    如果 workflow_item_id 非空但对应的工作项已不存在（孤立引用），
    视为可安全删除，跳过 workflow-aware 守卫。
    """
    if workflow_item_id:
        from app.modules.workflow.repository.models import BusWorkItemDoc
        work_item = await BusWorkItemDoc.get(workflow_item_id)
        if work_item is not None and not work_item.is_deleted:
            raise ValueError(workflow_error_message)
    if extra_guard is not None:
        await extra_guard()
    doc.is_deleted = True
    await doc.save()


async def create_with_workflow_transaction(
    *,
    client: AsyncMongoClient,
    payload: dict[str, Any],
    doc_cls: Any,
    unique_lookup: Callable[[dict[str, Any]], Any],
    duplicate_error_message: str,
    workflow_gateway: Any,
    workflow_item_factory: Callable[[dict[str, Any]], dict[str, Any]],
    enrich_result: Callable[[Any], Awaitable[dict[str, Any]]] | Callable[[Any], dict[str, Any]],
    prepare_payload: Callable[[dict[str, Any], Any], Awaitable[None]] | None = None,
    # 冗余字段回填：将业务 ID 写入 BusWorkItemDoc，避免后续跨集合查询
    redundant_fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create business entity and workflow item in one transaction."""
    async with client.start_session() as session:
        async with await session.start_transaction():
            if prepare_payload is not None:
                await prepare_payload(payload, session)

            existing = await doc_cls.find_one(unique_lookup(payload), session=session)
            if existing:
                raise ValueError(duplicate_error_message)

            # 先验证 payload 合法性，再创建 workflow item，避免 orphan
            doc = doc_cls(**payload)

            workflow_item = await workflow_gateway.create_work_item(
                **workflow_item_factory(payload),
                session=session,
            )
            payload["workflow_item_id"] = workflow_item["id"]
            doc.workflow_item_id = workflow_item["id"]

            # 将冗余字段回填到 BusWorkItemDoc（如 req_id → BusWorkItemDoc.req_id）
            if redundant_fields:
                from app.modules.workflow.repository.models import BusWorkItemDoc
                work_item_doc = await BusWorkItemDoc.get(workflow_item["id"], session=session)
                if work_item_doc:
                    for payload_key, doc_field in redundant_fields.items():
                        if payload_key in payload and payload[payload_key] is not None:
                            setattr(work_item_doc, doc_field, payload[payload_key])
                    await work_item_doc.save(session=session)

            await doc.insert(session=session)

            result = enrich_result(doc)
            if hasattr(result, "__await__"):
                return await result
            return result
