#!/usr/bin/env python3
"""Migrate legacy test cases to catalog fields (DEFAULT lab + 未分类 path).

Usage:
  python scripts/migrate_test_case_catalog.py
  python scripts/migrate_test_case_catalog.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from beanie import init_beanie
from pymongo import AsyncMongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings
from app.modules.test_specs.repository.models import (
    TestCaseDoc,
    TestCatalogSegmentDoc,
    TestLabDoc,
)
from app.modules.test_specs.service.catalog_service import CatalogService

DEFAULT_LAB_ID = "LAB-DEFAULT"
DEFAULT_CODE = "DEFAULT"
DEFAULT_NAME = "默认"
DEFAULT_PATH = ["未分类"]


async def ensure_default_lab(dry_run: bool) -> None:
    existing = await TestLabDoc.find_one({"lab_id": DEFAULT_LAB_ID})
    if existing:
        print(f"Default lab exists: {DEFAULT_LAB_ID}")
        return

    if dry_run:
        print(f"[dry-run] Would create lab {DEFAULT_LAB_ID}")
        return

    await TestLabDoc(
        lab_id=DEFAULT_LAB_ID,
        code=DEFAULT_CODE,
        name=DEFAULT_NAME,
        description="历史数据默认 Lab",
        sort_order=0,
        is_active=True,
    ).insert()
    print(f"Created default lab: {DEFAULT_LAB_ID}")


async def migrate_cases(dry_run: bool) -> int:
    catalog = CatalogService()
    path_key = catalog.build_path_key(DEFAULT_PATH)
    collection = TestCaseDoc.get_pymongo_collection()

    cursor = collection.find(
        {
            "is_deleted": False,
            "$or": [
                {"lab_id": {"$exists": False}},
                {"lab_id": None},
                {"lab_id": ""},
                {"catalog_path": {"$exists": False}},
                {"catalog_path": None},
                {"catalog_path": []},
            ],
        }
    )

    migrated = 0
    async for doc in cursor:
        case_id = doc.get("case_id", "unknown")
        update = {
            "lab_id": DEFAULT_LAB_ID,
            "catalog_path": DEFAULT_PATH,
            "catalog_path_key": path_key,
            "updated_at": datetime.now(timezone.utc),
        }
        if dry_run:
            print(f"[dry-run] Would migrate case {case_id}")
        else:
            await collection.update_one({"_id": doc["_id"]}, {"$set": update})
            await catalog.register_path(DEFAULT_LAB_ID, DEFAULT_PATH, delta=1)
        migrated += 1

    return migrated


async def backfill_path_keys(dry_run: bool) -> int:
    collection = TestCaseDoc.get_pymongo_collection()
    catalog = CatalogService()
    cursor = collection.find(
        {
            "is_deleted": False,
            "lab_id": {"$exists": True, "$ne": None},
            "catalog_path": {"$exists": True, "$ne": []},
            "$or": [
                {"catalog_path_key": {"$exists": False}},
                {"catalog_path_key": None},
                {"catalog_path_key": ""},
            ],
        }
    )
    updated = 0
    async for doc in cursor:
        key = catalog.build_path_key(doc.get("catalog_path") or [])
        if dry_run:
            print(f"[dry-run] Would set catalog_path_key for {doc.get('case_id')}")
        else:
            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"catalog_path_key": key}},
            )
        updated += 1
    return updated


async def main(dry_run: bool) -> None:
    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[TestLabDoc, TestCaseDoc, TestCatalogSegmentDoc],
        )
        await ensure_default_lab(dry_run)
        migrated = await migrate_cases(dry_run)
        backfilled = await backfill_path_keys(dry_run)
        print(f"Migrated cases: {migrated}, backfilled keys: {backfilled}")
    finally:
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate test cases to catalog fields")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
