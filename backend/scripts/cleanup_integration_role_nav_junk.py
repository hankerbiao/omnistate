#!/usr/bin/env python3
"""Remove role and navigation junk left by integration tests.

Usage:
  cd backend
  python scripts/cleanup_integration_role_nav_junk.py
  python scripts/cleanup_integration_role_nav_junk.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings

PRESERVED_ROLE_IDS = frozenset(
    {"ADMIN", "TPM", "REVIEWER", "MANUAL_DEV", "QA", "TESTER", "AUTO_DEV"}
)

ROLE_ID_PREFIXES = ("role_test_", "role_role_")

NAV_VIEW_PREFIXES = ("test_view_", "test_update_", "test_delete_")


def _is_integration_role(doc: dict) -> bool:
    role_id = str(doc.get("role_id") or "")
    if not role_id or role_id in PRESERVED_ROLE_IDS:
        return False
    return role_id.startswith(ROLE_ID_PREFIXES)


def _is_integration_nav(doc: dict) -> bool:
    view = str(doc.get("view") or "")
    return view.startswith(NAV_VIEW_PREFIXES)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean integration-test role/navigation junk from MongoDB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print counts only, do not delete")
    args = parser.parse_args()

    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    junk_roles = [
        doc for doc in db["roles"].find({}, {"role_id": 1, "name": 1})
        if _is_integration_role(doc)
    ]
    junk_nav = [
        doc for doc in db["navigation_pages"].find({}, {"view": 1, "title": 1})
        if _is_integration_nav(doc)
    ]

    print(f"Found {len(junk_roles)} junk role(s), {len(junk_nav)} navigation page(s)")
    for doc in junk_roles[:15]:
        print(f"  role: {doc.get('role_id')} | {doc.get('name')}")
    for doc in junk_nav[:15]:
        print(f"  nav: {doc.get('view')} | {doc.get('title')}")

    if args.dry_run:
        print("Dry run — no documents deleted.")
        client.close()
        return

    if junk_roles:
        role_ids = [d["role_id"] for d in junk_roles if d.get("role_id")]
        result = db["roles"].delete_many({"role_id": {"$in": role_ids}})
        print(f"Deleted {result.deleted_count} role(s)")
    else:
        print("Deleted 0 role(s)")

    if junk_nav:
        views = [d["view"] for d in junk_nav if d.get("view")]
        result = db["navigation_pages"].delete_many({"view": {"$in": views}})
        print(f"Deleted {result.deleted_count} navigation page(s)")
    else:
        print("Deleted 0 navigation page(s)")

    client.close()


if __name__ == "__main__":
    main()
