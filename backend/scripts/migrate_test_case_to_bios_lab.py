#!/usr/bin/env python3
"""为缺少 Lab 目录字段的历史测试用例补全数据，默认归入 BIOS LAB。

目标字段（TestCaseDoc）：
  - lab_id: LAB-BIOS（code=BIOS）
  - catalog_path: ["未分类"]（可经 --path 覆盖）
  - catalog_path_key: 由 catalog_path 规范化后生成

用法:
  cd backend
  python scripts/migrate_test_case_to_bios_lab.py --dry-run
  python scripts/migrate_test_case_to_bios_lab.py
  python scripts/migrate_test_case_to_bios_lab.py --include-default-lab
  python scripts/migrate_test_case_to_bios_lab.py --path 未分类,基础用例

说明:
  - 默认只处理缺少 lab_id / catalog_path 的用例
  - --include-default-lab 会额外把 lab_id=LAB-DEFAULT 的用例迁到 BIOS LAB
  - 会确保 test_labs 中存在 LAB-BIOS，并更新目录段 usage_count
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

TARGET_LAB_CODE = "BIOS"
TARGET_LAB_ID = "LAB-BIOS"
TARGET_LAB_NAME = "BIOS LAB"
DEFAULT_PATH = ["未分类"]
LEGACY_DEFAULT_LAB_ID = "LAB-DEFAULT"


def _parse_path(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_PATH)
    segments = [part.strip() for part in raw.split(",") if part.strip()]
    if not segments:
        raise ValueError("catalog path 至少需要 1 个段")
    return segments


def _missing_catalog_query(include_default_lab: bool) -> dict:
    missing = {
        "$or": [
            {"lab_id": {"$exists": False}},
            {"lab_id": None},
            {"lab_id": ""},
            {"catalog_path": {"$exists": False}},
            {"catalog_path": None},
            {"catalog_path": []},
            {"catalog_path_key": {"$exists": False}},
            {"catalog_path_key": None},
            {"catalog_path_key": ""},
        ],
    }
    if include_default_lab:
        return {
            "$or": [
                missing,
                {"lab_id": LEGACY_DEFAULT_LAB_ID},
            ],
        }
    return missing


async def ensure_bios_lab(dry_run: bool) -> None:
    existing = await TestLabDoc.find_one({"lab_id": TARGET_LAB_ID})
    if existing:
        print(f"BIOS lab exists: {TARGET_LAB_ID} ({existing.name})")
        return

    if dry_run:
        print(f"[dry-run] Would create lab {TARGET_LAB_ID} ({TARGET_LAB_NAME})")
        return

    await TestLabDoc(
        lab_id=TARGET_LAB_ID,
        code=TARGET_LAB_CODE,
        name=TARGET_LAB_NAME,
        description="历史测试用例默认归属 Lab",
        sort_order=1,
        is_active=True,
    ).insert()
    print(f"Created BIOS lab: {TARGET_LAB_ID}")


async def print_status() -> None:
    """打印当前库中用例 Lab/目录字段概况，便于判断为何迁移数为 0。"""
    collection = TestCaseDoc.get_pymongo_collection()
    active = await collection.count_documents({"is_deleted": False})
    missing = await collection.count_documents(
        {"is_deleted": False, **_missing_catalog_query(include_default_lab=True)},
    )
    bios = await collection.count_documents(
        {"is_deleted": False, "lab_id": TARGET_LAB_ID},
    )
    default_lab = await collection.count_documents(
        {"is_deleted": False, "lab_id": LEGACY_DEFAULT_LAB_ID},
    )
    print(
        f"当前状态: 有效用例 {active} 条 | "
        f"待迁移 {missing} 条 | "
        f"{TARGET_LAB_ID}={bios} | {LEGACY_DEFAULT_LAB_ID}={default_lab}"
    )
    if active and missing == 0:
        print("所有有效用例已具备 lab_id / catalog_path，无需再次迁移。")


async def migrate_cases(
    dry_run: bool,
    catalog_path: list[str],
    include_default_lab: bool,
) -> int:
    catalog = CatalogService()
    normalized_path = catalog.normalize_path_segments(catalog_path)
    path_key = catalog.build_path_key(normalized_path)
    collection = TestCaseDoc.get_pymongo_collection()

    query = {"is_deleted": False, **_missing_catalog_query(include_default_lab)}
    cursor = collection.find(query)

    migrated = 0
    async for doc in cursor:
        case_id = doc.get("case_id", "unknown")
        old_lab_id = doc.get("lab_id")
        old_path = list(doc.get("catalog_path") or [])

        update = {
            "lab_id": TARGET_LAB_ID,
            "catalog_path": normalized_path,
            "catalog_path_key": path_key,
            "updated_at": datetime.now(timezone.utc),
        }

        if dry_run:
            print(
                f"[dry-run] {case_id}: "
                f"lab {old_lab_id!r} -> {TARGET_LAB_ID}, "
                f"path {old_path!r} -> {normalized_path}"
            )
        else:
            await collection.update_one({"_id": doc["_id"]}, {"$set": update})
            if old_lab_id and old_path and (
                old_lab_id != TARGET_LAB_ID or old_path != normalized_path
            ):
                await catalog.register_path(old_lab_id, old_path, delta=-1)
            await catalog.register_path(TARGET_LAB_ID, normalized_path, delta=1)

        migrated += 1

    return migrated


async def main(
    dry_run: bool,
    catalog_path: list[str],
    include_default_lab: bool,
) -> None:
    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[TestLabDoc, TestCaseDoc, TestCatalogSegmentDoc],
        )
        await ensure_bios_lab(dry_run)
        migrated = await migrate_cases(dry_run, catalog_path, include_default_lab)
        action = "Would migrate" if dry_run else "Migrated"
        print(f"{action} cases: {migrated}")
        if migrated and not dry_run:
            print(f"Target: {TARGET_LAB_ID} / {catalog_path}")
        if migrated == 0:
            await print_status()
    finally:
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate legacy test cases to BIOS LAB catalog fields",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument(
        "--path",
        default=None,
        help='默认目录路径，逗号分隔，如 "未分类" 或 "未分类,基础用例"',
    )
    parser.add_argument(
        "--include-default-lab",
        action="store_true",
        help=f"同时迁移 lab_id={LEGACY_DEFAULT_LAB_ID} 的历史用例",
    )
    args = parser.parse_args()
    asyncio.run(
        main(
            dry_run=args.dry_run,
            catalog_path=_parse_path(args.path),
            include_default_lab=args.include_default_lab,
        )
    )
