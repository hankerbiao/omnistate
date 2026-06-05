#!/usr/bin/env python3
"""Remove workflow/requirement junk left by integration tests.

Targets bus_work_items and test_requirements with integration-test title patterns.

Usage:
  cd backend
  python scripts/cleanup_integration_workflow_junk.py
  python scripts/cleanup_integration_workflow_junk.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings

WORK_ITEM_TITLE_PATTERNS = (
    re.compile(r"^Test Requirement test_\d+$"),
    re.compile(r"^Searchable Item test_\d+$"),
    re.compile(r"^Test Transitions test_\d+$"),
    re.compile(r"^Requirement test_\d+$"),
    re.compile(r"^Get Test test_\d+$"),
    re.compile(r"^Original Title test_\d+$"),
    re.compile(r"^Updated Title test_\d+$"),
    re.compile(r"^Delete Test test_\d+$"),
    re.compile(r"^Test Requirement for (Cases|Lifecycle|Reject) test_\d+$"),
)

REQ_TITLE_PATTERNS = (
    re.compile(r"^Test Requirement test_\d+$"),
    re.compile(r"^Req test_\d+$"),
    re.compile(r"^Get Test test_\d+$"),
    re.compile(r"^Original Title test_\d+$"),
    re.compile(r"^Updated Title test_\d+$"),
    re.compile(r"^Delete Test test_\d+$"),
    re.compile(r"^Test desc$"),
)


def _is_junk_work_item(doc: dict) -> bool:
    title = str(doc.get("title") or "")
    return any(p.match(title) for p in WORK_ITEM_TITLE_PATTERNS)


def _is_junk_requirement(doc: dict) -> bool:
    title = str(doc.get("title") or "")
    if any(p.match(title) for p in REQ_TITLE_PATTERNS):
        return True
    desc = str(doc.get("description") or "")
    return desc == "catalog test"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean integration-test workflow/requirement junk from MongoDB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print counts only, do not delete")
    args = parser.parse_args()

    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    all_items = list(
        db["bus_work_items"].find(
            {"is_deleted": False},
            {"title": 1, "type_code": 1},
        )
    )
    junk_items = [doc for doc in all_items if _is_junk_work_item(doc)]
    junk_item_ids = [doc["_id"] for doc in junk_items]

    all_reqs = list(
        db["test_requirements"].find(
            {"is_deleted": False},
            {"req_id": 1, "title": 1, "description": 1, "workflow_item_id": 1},
        )
    )
    junk_reqs = [doc for doc in all_reqs if _is_junk_requirement(doc)]
    junk_req_ids = [doc["req_id"] for doc in junk_reqs if doc.get("req_id")]

    print(
        f"Found {len(junk_items)} junk work item(s), "
        f"{len(junk_reqs)} junk requirement(s)"
    )
    for doc in junk_items[:15]:
        print(f"  work_item: {doc['_id']} | {doc.get('title')}")
    if len(junk_items) > 15:
        print(f"  ... and {len(junk_items) - 15} more")
    for doc in junk_reqs[:15]:
        print(f"  requirement: {doc.get('req_id')} | {doc.get('title')}")
    if len(junk_reqs) > 15:
        print(f"  ... and {len(junk_reqs) - 15} more")

    if args.dry_run:
        print("Dry run — no documents deleted.")
        client.close()
        return

    if junk_item_ids:
        db["bus_work_items"].update_many(
            {"_id": {"$in": junk_item_ids}},
            {"$set": {"is_deleted": True}},
        )
    if junk_req_ids:
        db["test_requirements"].update_many(
            {"req_id": {"$in": junk_req_ids}},
            {"$set": {"is_deleted": True}},
        )
        for doc in junk_reqs:
            wf_id = doc.get("workflow_item_id")
            if wf_id and ObjectId.is_valid(str(wf_id)):
                db["bus_work_items"].update_one(
                    {"_id": ObjectId(str(wf_id))},
                    {"$set": {"is_deleted": True}},
                )

    print(f"Soft-deleted {len(junk_item_ids)} work item(s), {len(junk_req_ids)} requirement(s)")
    client.close()


if __name__ == "__main__":
    main()
