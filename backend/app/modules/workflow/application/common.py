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
    query = BusWorkItemDoc.find({"is_deleted": False})

    if type_code:
        query = query.find(BusWorkItemDoc.type_code == type_code)
    if state:
        query = query.find(BusWorkItemDoc.current_state == state)

    or_conditions = []
    if owner_id is not None:
        or_conditions.append(BusWorkItemDoc.current_owner_id == owner_id)
    if creator_id is not None:
        or_conditions.append(BusWorkItemDoc.creator_id == creator_id)

    if or_conditions:
        query = query.find({"$or": or_conditions})

    return query


def docs_to_dicts(docs: list[BusWorkItemDoc]) -> list[dict[str, Any]]:
    return [serialize_work_item(doc) for doc in docs]


def serialize_work_item(doc: BusWorkItemDoc) -> dict[str, Any]:
    data = doc.model_dump()
    data["id"] = str(doc.id)
    data["item_id"] = str(doc.id)
    if data.get("parent_item_id") is not None:
        data["parent_item_id"] = str(data["parent_item_id"])
    return data


async def get_work_item_doc(
    work_item_id: str,
    session: AsyncClientSession | None = None,
) -> BusWorkItemDoc | None:
    if session is None:
        return await BusWorkItemDoc.get(work_item_id)
    try:
        return await BusWorkItemDoc.get(work_item_id, session=session)
    except TypeError:
        return await BusWorkItemDoc.get(work_item_id)


async def save_doc(doc: Any, session: AsyncClientSession | None = None) -> None:
    if session is None:
        await doc.save()
        return
    try:
        await doc.save(session=session)
    except TypeError:
        await doc.save()


async def insert_doc(doc: Any, session: AsyncClientSession | None = None) -> None:
    if session is None:
        await doc.insert()
        return
    try:
        await doc.insert(session=session)
    except TypeError:
        await doc.insert()


def validate_object_id(item_id: str) -> PydanticObjectId | None:
    if not PydanticObjectId.is_valid(item_id):
        return None
    return PydanticObjectId(item_id)
