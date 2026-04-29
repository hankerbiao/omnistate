from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from app.modules.workflow.repository.models import BusWorkItemDoc


def base_item_query(
    type_code: str | None = None,
    state: str | None = None,
    owner_id: str | None = None,
    creator_id: str | None = None,
):
    # 所有工作项查询默认排除软删除数据。
    query = BusWorkItemDoc.find({"is_deleted": False})

    # 按业务类型和当前状态继续收窄查询范围。
    if type_code:
        query = query.find(BusWorkItemDoc.type_code == type_code)
    if state:
        query = query.find(BusWorkItemDoc.current_state == state)

    # owner 和 creator 采用 OR 语义，表示只要满足任一条件即可命中。
    or_conditions = []
    if owner_id is not None:
        or_conditions.append(BusWorkItemDoc.current_owner_id == owner_id)
    if creator_id is not None:
        or_conditions.append(BusWorkItemDoc.creator_id == creator_id)

    if or_conditions:
        query = query.find({"$or": or_conditions})

    return query


def docs_to_dicts(docs: list[BusWorkItemDoc]) -> list[dict[str, Any]]:
    # 批量序列化工作项文档，统一输出结构。
    return [serialize_work_item(doc) for doc in docs]


def serialize_work_item(doc: BusWorkItemDoc) -> dict[str, Any]:
    # 将 Beanie 文档转换为前端/接口更易消费的字典结构。
    data = doc.model_dump()
    data["id"] = str(doc.id)
    # 保留 item_id 字段，兼容历史接口或调用方约定。
    data["item_id"] = str(doc.id)
    if data.get("parent_item_id") is not None:
        data["parent_item_id"] = str(data["parent_item_id"])
    return data


async def get_work_item_doc(
    work_item_id: str,
    session: AsyncClientSession | None = None,
) -> BusWorkItemDoc | None:
    # 尽量复用外部传入的 session，以便参与事务。
    if session is None:
        return await BusWorkItemDoc.get(work_item_id)
    try:
        # 某些调用场景下 Beanie 版本/封装对 session 参数支持不一致，做兼容降级。
        return await BusWorkItemDoc.get(work_item_id, session=session)
    except TypeError:
        return await BusWorkItemDoc.get(work_item_id)


async def save_doc(doc: Any, session: AsyncClientSession | None = None) -> None:
    # 保存文档时优先使用事务 session，失败则回退到无 session 模式。
    if session is None:
        await doc.save()
        return
    try:
        await doc.save(session=session)
    except TypeError:
        await doc.save()


async def insert_doc(doc: Any, session: AsyncClientSession | None = None) -> None:
    # 插入文档时优先使用事务 session，失败则回退到无 session 模式。
    if session is None:
        await doc.insert()
        return
    try:
        await doc.insert(session=session)
    except TypeError:
        await doc.insert()


def validate_object_id(item_id: str) -> PydanticObjectId | None:
    # 先校验字符串是否是合法 ObjectId，避免在上层直接抛异常。
    if not PydanticObjectId.is_valid(item_id):
        return None
    return PydanticObjectId(item_id)
