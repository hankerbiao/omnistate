#!/usr/bin/env python3
"""Remove catalog/test-case junk left by integration tests.

Targets artifacts from tests/integration/test_specs/:
  - test_labs with integration-style names/codes (not production presets)
  - test_cases with titles like "Test Case test_*" or known fixture titles
  - test_catalog_segments for removed labs

Preserves common presets: DEFAULT, BIOS, DDR5, BMC, etc.

Usage:
  cd backend
  python scripts/cleanup_integration_catalog_junk.py
  python scripts/cleanup_integration_catalog_junk.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings

# Production / seed lab codes to never delete
PRESERVED_LAB_CODES = frozenset(
    {
        "DEFAULT",
        "BIOS",
        "DDR5",
        "BMC",
        "CPU",
        "GPU",
        "NET",
        "PWR",
        "STORAGE",
    }
)

LAB_NAME_PATTERNS = (
    re.compile(r"^Lab test_\d+$"),
    re.compile(r"^Mixed Case test_\d+$"),
    re.compile(r"^Updated Lab Name$"),
    re.compile(r"^First$"),
    re.compile(r"^Second$"),
    re.compile(r"^TPM Lab$"),
    re.compile(r"^Forbidden$"),
)

LAB_CODE_PATTERNS = (
    re.compile(r"^L\d{8,}$"),  # L + timestamp fragment from unique_id()
    re.compile(r"^DUP[A-Z0-9]+$"),
    re.compile(r"^Mixed_test_\d+$"),
    re.compile(r"^T[A-Z0-9]{6,}$"),  # TPM test lab codes
    re.compile(r"^X[A-Z0-9]{1,6}$"),  # forbidden-create attempt codes
)

CASE_TITLE_PATTERNS = (
    re.compile(r"^Test Case test_\d+$"),
    re.compile(r"^Catalog migration case$"),
    re.compile(r"^Block delete$"),
    re.compile(r"^No catalog test_\d+$"),
)


def _is_integration_lab(doc: dict) -> bool:
    code = str(doc.get("code") or "")
    if code.upper() in PRESERVED_LAB_CODES:
        return False
    name = str(doc.get("name") or "")
    if any(p.match(name) for p in LAB_NAME_PATTERNS):
        return True
    if any(p.match(code) for p in LAB_CODE_PATTERNS):
        return True
    lab_id = str(doc.get("lab_id") or "")
    if lab_id.startswith("LAB-L") and re.match(r"^LAB-L\d{8,}$", lab_id):
        return True
    return False


def _is_integration_case(doc: dict) -> bool:
    title = str(doc.get("title") or "")
    if any(p.match(title) for p in CASE_TITLE_PATTERNS):
        return True
    if title.startswith("Req test_"):
        return True
    catalog_path = doc.get("catalog_path") or []
    if catalog_path == ["integration"]:
        return True
    if catalog_path and str(catalog_path[0]).startswith("prefix_"):
        return True
    if catalog_path and str(catalog_path[0]).startswith("seg_"):
        return True
    case_id = str(doc.get("case_id") or "")
    if case_id.startswith("TC-CAT-test_") or case_id.startswith("TC-BLOCK-test_"):
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean integration-test catalog lab and test case junk from MongoDB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print counts only, do not delete")
    args = parser.parse_args()

    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    all_labs = list(db["test_labs"].find({}))
    junk_labs = [doc for doc in all_labs if _is_integration_lab(doc)]
    junk_lab_ids = [doc["lab_id"] for doc in junk_labs if doc.get("lab_id")]

    case_filter = {
        "$or": [
            {"title": {"$regex": r"^Test Case test_\d+$"}},
            {"title": {"$in": ["Catalog migration case", "Block delete"]}},
            {"catalog_path": ["integration"]},
            {"case_id": {"$regex": r"^TC-(CAT|BLOCK)-test_"}},
        ]
    }
    if junk_lab_ids:
        case_filter["$or"].append({"lab_id": {"$in": junk_lab_ids}})

    junk_cases = list(
        db["test_cases"].find(
            {"$or": case_filter["$or"]},
            {"case_id": 1, "title": 1, "lab_id": 1, "workflow_item_id": 1, "catalog_path": 1},
        )
    )
    junk_cases = [doc for doc in junk_cases if _is_integration_case(doc)]
    junk_case_ids = [doc["case_id"] for doc in junk_cases if doc.get("case_id")]

    print(
        f"Found {len(junk_labs)} integration lab(s), "
        f"{len(junk_cases)} integration test case(s)"
    )
    for doc in junk_labs[:15]:
        print(f"  lab:  {doc.get('lab_id')} | {doc.get('code')} | {doc.get('name')}")
    if len(junk_labs) > 15:
        print(f"  ... and {len(junk_labs) - 15} more")
    for doc in junk_cases[:15]:
        print(f"  case: {doc.get('case_id')} | {doc.get('title')} | {doc.get('lab_id')}")
    if len(junk_cases) > 15:
        print(f"  ... and {len(junk_cases) - 15} more")

    if args.dry_run:
        print("Dry run — no documents deleted.")
        client.close()
        return

    if junk_case_ids:
        db["test_cases"].update_many(
            {"case_id": {"$in": junk_case_ids}},
            {"$set": {"is_deleted": True}},
        )
        for doc in junk_cases:
            workflow_item_id = doc.get("workflow_item_id")
            if workflow_item_id:
                from bson import ObjectId

                if ObjectId.is_valid(str(workflow_item_id)):
                    db["bus_work_items"].update_one(
                        {"_id": ObjectId(str(workflow_item_id))},
                        {"$set": {"is_deleted": True}},
                    )

    if junk_lab_ids:
        db["test_catalog_segments"].delete_many({"lab_id": {"$in": junk_lab_ids}})
        lab_result = db["test_labs"].delete_many({"lab_id": {"$in": junk_lab_ids}})
        print(f"Deleted {lab_result.deleted_count} lab(s)")
    else:
        print("Deleted 0 lab(s)")

    print(f"Soft-deleted {len(junk_case_ids)} test case(s)")
    client.close()


if __name__ == "__main__":
    main()
