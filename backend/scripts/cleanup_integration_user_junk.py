#!/usr/bin/env python3
"""Remove user junk left by integration tests.

Targets artifacts from tests/integration/:
  - user_id matching test_tpm_*, test_reviewer_*, user_test_*, etc.
  - ephemeral users with @test.local email (except preserved accounts)

Preserves: test_admin, seed_test_users (admin/tpm/reviewer/...), integ_* reuse accounts.

Usage:
  cd backend
  python scripts/cleanup_integration_user_junk.py
  python scripts/cleanup_integration_user_junk.py --dry-run
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

PRESERVED_USER_IDS = frozenset(
    {
        "test_admin",
        "admin",
        "tpm",
        "reviewer",
        "dev",
        "qa",
        "tester",
        "integ_tpm",
        "integ_reviewer",
        "integ_dev",
        "integ_qa",
        "integ_tester",
        "integ_auto_dev",
        "integ_no_role",
    }
)

EPHEMERAL_USER_ID_PREFIXES = (
    "test_tpm_",
    "test_reviewer_",
    "test_dev_",
    "test_qa_",
    "test_tester_",
    "test_auto_dev_",
    "test_no_role_",
    "user_test_",
    "user_user_",
)


def _is_integration_user(doc: dict) -> bool:
    user_id = str(doc.get("user_id") or "")
    if not user_id or user_id in PRESERVED_USER_IDS:
        return False
    if user_id.startswith(EPHEMERAL_USER_ID_PREFIXES):
        return True
    email = str(doc.get("email") or "")
    if email.endswith("@test.local") and user_id not in PRESERVED_USER_IDS:
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean integration-test user junk from MongoDB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print counts only, do not delete")
    args = parser.parse_args()

    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    all_users = list(
        db["users"].find(
            {},
            {"user_id": 1, "username": 1, "email": 1},
        )
    )
    junk_users = [doc for doc in all_users if _is_integration_user(doc)]
    junk_user_ids = [doc["user_id"] for doc in junk_users if doc.get("user_id")]

    print(f"Found {len(junk_users)} integration user(s)")
    for doc in junk_users[:20]:
        print(f"  user: {doc.get('user_id')} | {doc.get('username')} | {doc.get('email')}")
    if len(junk_users) > 20:
        print(f"  ... and {len(junk_users) - 20} more")

    if args.dry_run:
        print("Dry run — no documents deleted.")
        client.close()
        return

    if junk_user_ids:
        result = db["users"].delete_many({"user_id": {"$in": junk_user_ids}})
        print(f"Deleted {result.deleted_count} user(s)")
    else:
        print("Deleted 0 user(s)")

    client.close()


if __name__ == "__main__":
    main()
