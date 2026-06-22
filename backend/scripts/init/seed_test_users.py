#!/usr/bin/env python3
"""为开发环境创建测试用户。

前提：必须先执行 scripts/init/init_rbac.py 初始化权限与角色。
测试角色 (TPM/REVIEWER/MANUAL_DEV/QA/TESTER) 和 ADMIN 由 init_rbac.py 定义。
默认密码统一为 Test@123。

用法:
  python scripts/init/init_rbac.py                 # 先初始化 RBAC
  python scripts/init/seed_test_users.py           # 再创建测试用户
  python scripts/init/seed_test_users.py --reset   # 覆盖已存在用户
  python scripts/init/seed_test_users.py --password Pass@456  # 自定义密码
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.shared.config import get_settings
from app.shared.auth import hash_password
from app.modules.auth.repository.models import UserDoc

# 测试用户定义: (user_id, username, role_ids)
TEST_USERS = [
    ("admin", "管理员", ["ADMIN"]),
    ("tpm", "项目经理", ["TPM"]),
    ("reviewer", "审核人", ["REVIEWER"]),
    ("dev", "开发人员", ["MANUAL_DEV"]),
    ("qa", "质量保证", ["QA"]),
    ("tester", "测试人员", ["TESTER"]),
]


async def create_users(password: str, reset: bool):
    """创建测试用户。"""
    for user_id, username, role_ids in TEST_USERS:
        salt, pwd_hash = hash_password(password)
        existing = await UserDoc.find_one(UserDoc.user_id == user_id)

        if existing and not reset:
            print(f"  - 用户已存在: {user_id}（跳过，加 --reset 覆盖）")
            continue

        if existing and reset:
            existing.username = username
            existing.email = None
            existing.status = "ACTIVE"
            existing.role_ids = role_ids
            existing.password_salt = salt
            existing.password_hash = pwd_hash
            await existing.save()
            print(f"  ✓ 用户已更新: {user_id} ({username})")
            continue

        await UserDoc(
            user_id=user_id,
            username=username,
            email=None,
            status="ACTIVE",
            role_ids=role_ids,
            password_salt=salt,
            password_hash=pwd_hash,
        ).insert()
        print(f"  ✓ 用户创建: {user_id} ({username})")


async def main():
    parser = argparse.ArgumentParser(description="为开发环境创建测试用户")
    parser.add_argument("--password", default="Test@123", help="统一登录密码 (默认: Test@123)")
    parser.add_argument("--reset", action="store_true", help="覆盖已存在的用户信息")
    args = parser.parse_args()

    print("=" * 50)
    print("  测试用户初始化")
    print("=" * 50)

    client = AsyncMongoClient(get_settings().mongodb.uri)
    try:
        await init_beanie(
            database=client[get_settings().mongodb.db_name],
            document_models=[UserDoc],
        )

        print(f"\n创建测试用户 (密码: {args.password})...")
        await create_users(args.password, args.reset)

        print("\n" + "=" * 50)
        print("  初始化完成")
        print("=" * 50)
        print(f"\n  用户名    角色        密码")
        print(f"  {'─' * 40}")
        for user_id, username, _ in TEST_USERS:
            print(f"  {user_id:<10} {username:<10} {args.password}")
        print(f"\n  共 {len(TEST_USERS)} 个用户，密码统一为: {args.password}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
