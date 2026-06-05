#!/usr/bin/env python3
"""为测试用例随机分配分类目录路径（演示/填充数据用）。

每个用例从预置目录模板中随机选取一条路径，默认保持在原 lab_id（无则归入 LAB-BIOS）。
会同步更新 catalog_path_key 与目录段 usage_count。

用法:
  cd backend
  python scripts/seed_test_case_random_catalog.py --dry-run
  python scripts/seed_test_case_random_catalog.py
  python scripts/seed_test_case_random_catalog.py --force   # 覆盖已有非默认路径
  python scripts/seed_test_case_random_catalog.py --seed 42 # 可复现的随机结果
"""
from __future__ import annotations

import argparse
import asyncio
import random
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

DEFAULT_LAB_ID = "LAB-BIOS"

# 预置分类目录模板（1～2 级路径，写入前会规范化小写）
CATALOG_PATH_TEMPLATES: list[list[str]] = [
    ["未分类"],
    ["功能测试", "启动引导"],
    ["功能测试", "配置项"],
    ["功能测试", "安全启动"],
    ["兼容性", "版本回退"],
    ["兼容性", "硬件平台"],
    ["稳定性", "长时间运行"],
    ["稳定性", "反复重启"],
    ["接口测试", "ipmi"],
    ["接口测试", "redfish"],
    ["回归测试", "冒烟"],
    ["回归测试", "全量"],
    ["性能", "启动耗时"],
    ["安全", "固件校验"],
]


def _pick_path(rng: random.Random) -> list[str]:
    return list(rng.choice(CATALOG_PATH_TEMPLATES))


async def assign_random_catalog(
    dry_run: bool,
    force: bool,
    seed: int | None,
) -> int:
    catalog = CatalogService()
    rng = random.Random(seed)
    collection = TestCaseDoc.get_pymongo_collection()

    query: dict = {"is_deleted": False}
    if not force:
        query["$or"] = [
            {"catalog_path": {"$exists": False}},
            {"catalog_path": None},
            {"catalog_path": []},
            {"catalog_path": ["未分类"]},
        ]

    updated = 0
    async for doc in collection.find(query):
        case_id = doc.get("case_id", "unknown")
        old_lab_id = doc.get("lab_id") or DEFAULT_LAB_ID
        old_path = list(doc.get("catalog_path") or [])
        lab_id = old_lab_id if doc.get("lab_id") else DEFAULT_LAB_ID
        new_path = catalog.normalize_path_segments(_pick_path(rng))
        path_key = catalog.build_path_key(new_path)

        if old_lab_id == lab_id and old_path == new_path:
            continue

        if dry_run:
            print(
                f"[dry-run] {case_id}: "
                f"{old_lab_id}{old_path!r} -> {lab_id}{new_path!r}"
            )
        else:
            await collection.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "lab_id": lab_id,
                        "catalog_path": new_path,
                        "catalog_path_key": path_key,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            if old_path:
                await catalog.register_path(old_lab_id, old_path, delta=-1)
            await catalog.register_path(lab_id, new_path, delta=1)

        updated += 1

    return updated


async def main(dry_run: bool, force: bool, seed: int | None) -> None:
    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[TestLabDoc, TestCaseDoc, TestCatalogSegmentDoc],
        )
        count = await assign_random_catalog(dry_run, force, seed)
        action = "Would update" if dry_run else "Updated"
        print(f"{action} cases: {count}")
        if count:
            print(f"Templates: {len(CATALOG_PATH_TEMPLATES)} paths")
    finally:
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assign random catalog paths to test cases")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已有目录（默认仅处理缺失或「未分类」的用例）",
    )
    parser.add_argument("--seed", type=int, default=None, help="随机种子，便于复现")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run, args.force, args.seed))
