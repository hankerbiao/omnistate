from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable, Mapping
from typing import Any

from pymongo import AsyncMongoClient

from app.shared.db.config import settings


TEST_REQUIREMENTS = "test_requirements"
TEST_CASES = "test_cases"
WORK_ITEMS = "bus_work_items"


def collect_status_index_names(indexes: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Return index names whose key definition includes the legacy status field."""
    status_index_names: list[str] = []
    for name, spec in indexes.items():
        keys = spec.get("key", [])
        if any(field == "status" for field, _direction in keys):
            status_index_names.append(name)
    return status_index_names


def find_orphan_workflow_refs(
    requirement_docs: Iterable[Mapping[str, Any]],
    test_case_docs: Iterable[Mapping[str, Any]],
    existing_workflow_ids: set[str],
) -> list[dict[str, str]]:
    """Find test spec documents whose workflow_item_id no longer exists."""
    orphans: list[dict[str, str]] = []
    sources = (
        (TEST_REQUIREMENTS, "req_id", requirement_docs),
        (TEST_CASES, "case_id", test_case_docs),
    )

    for collection, business_id_field, docs in sources:
        for doc in docs:
            workflow_item_id = doc.get("workflow_item_id")
            if not workflow_item_id or str(workflow_item_id) in existing_workflow_ids:
                continue
            orphans.append(
                {
                    "collection": collection,
                    "business_id": str(doc.get(business_id_field, "")),
                    "workflow_item_id": str(workflow_item_id),
                }
            )
    return orphans


async def _load_docs(db: Any, collection: str, fields: dict[str, int]) -> list[dict[str, Any]]:
    cursor = db[collection].find({"workflow_item_id": {"$exists": True, "$ne": None}}, fields)
    return await cursor.to_list(length=None)


async def inspect_status_projection() -> dict[str, Any]:
    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        db = client[settings.MONGO_DB_NAME]

        requirement_indexes = await db[TEST_REQUIREMENTS].index_information()
        test_case_indexes = await db[TEST_CASES].index_information()
        requirement_docs = await _load_docs(db, TEST_REQUIREMENTS, {"req_id": 1, "workflow_item_id": 1})
        test_case_docs = await _load_docs(db, TEST_CASES, {"case_id": 1, "workflow_item_id": 1})

        workflow_ids = {
            str(doc["_id"])
            async for doc in db[WORK_ITEMS].find({}, {"_id": 1})
        }

        return {
            "status_indexes": {
                TEST_REQUIREMENTS: collect_status_index_names(requirement_indexes),
                TEST_CASES: collect_status_index_names(test_case_indexes),
            },
            "orphans": find_orphan_workflow_refs(requirement_docs, test_case_docs, workflow_ids),
        }
    finally:
        close_result = client.close()
        if hasattr(close_result, "__await__"):
            await close_result


async def apply_status_projection_cleanup() -> dict[str, Any]:
    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        db = client[settings.MONGO_DB_NAME]
        before = await inspect_status_projection()

        for collection, names in before["status_indexes"].items():
            for name in names:
                await db[collection].drop_index(name)

        requirement_update = await db[TEST_REQUIREMENTS].update_many({}, {"$unset": {"status": ""}})
        test_case_update = await db[TEST_CASES].update_many({}, {"$unset": {"status": ""}})

        return {
            **before,
            "unset_status": {
                TEST_REQUIREMENTS: requirement_update.modified_count,
                TEST_CASES: test_case_update.modified_count,
            },
        }
    finally:
        close_result = client.close()
        if hasattr(close_result, "__await__"):
            await close_result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove legacy test_specs status projection fields and indexes."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply cleanup. Without this flag the script only reports findings.",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    result = (
        await apply_status_projection_cleanup()
        if args.apply
        else await inspect_status_projection()
    )

    print("status indexes:", result["status_indexes"])
    print("orphan workflow refs:", result["orphans"])
    if "unset_status" in result:
        print("unset status counts:", result["unset_status"])


if __name__ == "__main__":
    asyncio.run(_main())
