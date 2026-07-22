#!/usr/bin/env python3
"""为开发环境创建测试用户。

前提：必须先执行 scripts/init/sync_rbac.py 初始化角色，并显式设置 DML_ENV=dev/test/local。
默认密码统一为 Test@123。

用法:
  DML_ENV=dev python scripts/dev/seed_test_users.py
  DML_ENV=dev python scripts/dev/seed_test_users.py --reset
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.auth.repository.models import RoleDoc, UserDoc  # noqa: E402
from scripts.common.database import database_runtime  # noqa: E402
from scripts.common.users import write_user  # noqa: E402

# 测试用户定义: (user_id, username, role_ids)
TEST_USERS = [
    ("admin", "管理员", ["ADMIN"]),
    ("tpm", "项目经理", ["TPM"]),
    ("reviewer", "审核人", ["REVIEWER"]),
    ("dev", "开发人员", ["MANUAL_DEV"]),
    ("qa", "质量保证", ["QA"]),
    ("tester", "测试人员", ["TESTER"]),
]


def ensure_development_environment(environment: str | None = None) -> str:
    """Reject predictable development accounts in production-like environments."""
    normalized = (environment or os.getenv("DML_ENV", "production")).strip().lower()
    normalized = {"development": "dev", "testing": "test"}.get(normalized, normalized)
    if normalized not in {"dev", "test", "local"}:
        raise RuntimeError(
            "测试用户只能在 DML_ENV=dev、test 或 local 时创建；当前环境为 "
            f"{normalized or '未设置'}"
        )
    return normalized


async def create_users(password: str, reset: bool) -> None:
    """创建测试用户。"""
    for user_id, username, role_ids in TEST_USERS:
        result = await write_user(
            user_id=user_id,
            username=username,
            password=password,
            role_ids=role_ids,
            existing_policy="update" if reset else "skip",
        )
        if result == "skipped":
            print(f"  - 用户已存在: {user_id}（跳过，加 --reset 覆盖）")
        elif result == "updated":
            print(f"  用户已更新: {user_id} ({username})")
        else:
            print(f"  用户已创建: {user_id} ({username})")


async def main():
    parser = argparse.ArgumentParser(description="为开发环境创建测试用户")
    parser.add_argument("--password", default="Test@123", help="统一登录密码 (默认: Test@123)")
    parser.add_argument("--reset", action="store_true", help="覆盖已存在的用户信息")
    args = parser.parse_args()
    ensure_development_environment()

    print("=" * 50)
    print("  测试用户初始化")
    print("=" * 50)

    async with database_runtime(document_models=[UserDoc, RoleDoc]):
        print("\n创建测试用户...")
        await create_users(args.password, args.reset)

        print("\n" + "=" * 50)
        print("  初始化完成")
        print("=" * 50)
        print("\n  用户名    显示名")
        print(f"  {'-' * 32}")
        for user_id, username, _ in TEST_USERS:
            print(f"  {user_id:<10} {username:<10}")
        print(f"\n  共处理 {len(TEST_USERS)} 个用户")


if __name__ == "__main__":
    asyncio.run(main())
