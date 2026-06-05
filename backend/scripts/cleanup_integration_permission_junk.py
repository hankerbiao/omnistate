#!/usr/bin/env python3
"""Remove permission junk left by integration tests.

Targets artifacts from tests/integration/test_auth/:
  - permissions with perm_id matching test_perm_* or test_perm_update_*
  - permissions with code matching test.code.test_*

Usage:
  cd backend
  python scripts/cleanup_integration_permission_junk.py
  python scripts/cleanup_integration_permission_junk.py --dry-run
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

PERM_ID_PREFIXES = ("test_perm_", "test_perm_update_")
CODE_PREFIX = "test.code.test_"


def _is_integration_permission(doc: dict) -> bool:
    perm_id = str(doc.get("perm_id") or "")
    if perm_id.startswith(PERM_ID_PREFIXES):
        return True
    code = str(doc.get("code") or "")
    return code.startswith(CODE_PREFIX)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean integration-test permission junk from MongoDB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print counts only, do not delete")
    args = parser.parse_args()

    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    all_perms = list(
        db["permissions"].find(
            {},
            {"perm_id": 1, "code": 1, "name": 1},
        )
    )
    junk_perms = [doc for doc in all_perms if _is_integration_permission(doc)]
    junk_perm_ids = [doc["perm_id"] for doc in junk_perms if doc.get("perm_id")]

    print(f"Found {len(junk_perms)} integration permission(s)")
    for doc in junk_perms[:20]:
        print(f"  perm: {doc.get('perm_id')} | {doc.get('code')} | {doc.get('name')}")
    if len(junk_perms) > 20:
        print(f"  ... and {len(junk_perms) - 20} more")

    if args.dry_run:
        print("Dry run — no documents deleted.")
        client.close()
        return

    if junk_perm_ids:
        result = db["permissions"].delete_many({"perm_id": {"$in": junk_perm_ids}})
        print(f"Deleted {result.deleted_count} permission(s)")
    else:
        print("Deleted 0 permission(s)")

    client.close()


if __name__ == "__main__":
    main()
