#!/usr/bin/env python3
"""创建 RBAC 用户脚本。

前提：必须先执行 scripts/init/init_rbac.py 初始化权限与角色。

用法示例：
python scripts/init/create_user.py \
  --user-id admin001 \
  --username "系统管理员" \
  --password 'Admin@123' \
  --roles ADMIN \
  --email admin@example.com

说明：
- 密码会使用 PBKDF2 进行哈希存储，不会明文落库。
- 会校验 roles 是否都存在于 Role 集合。
- 默认若用户已存在则报错，可加 --upsert 覆盖更新用户信息和密码。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from beanie import init_beanie
from pymongo import AsyncMongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.config import get_settings
from app.shared.auth import hash_password
from app.modules.auth.repository.models import UserDoc, RoleDoc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建 RBAC 用户")
    parser.add_argument("--user-id", required=True, help="用户唯一 ID")
    parser.add_argument("--username", required=True, help="用户名")
    parser.add_argument("--password", required=True, help="登录密码（明文输入，脚本内加密）")
    parser.add_argument("--roles", default="", help="角色列表，逗号分隔，例如 ADMIN,TESTER")
    parser.add_argument("--email", default=None, help="邮箱")
    parser.add_argument("--status", default="ACTIVE", choices=["ACTIVE", "DISABLED"], help="用户状态")
    parser.add_argument("--upsert", action="store_true", help="若用户存在则更新用户信息和密码")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    role_ids = [r.strip() for r in args.roles.split(",") if r.strip()]

    client = AsyncMongoClient(get_settings().mongodb.uri)
    try:
        await init_beanie(
            database=client[get_settings().mongodb.db_name],
            document_models=[UserDoc, RoleDoc],
        )

        # 角色存在性校验
        if role_ids:
            role_count = await RoleDoc.find({"role_id": {"$in": role_ids}}).count()
            if role_count != len(set(role_ids)):
                missing = set(role_ids) - {r.role_id async for r in RoleDoc.find({"role_id": {"$in": role_ids}})}
                raise RuntimeError(
                    f"角色不存在: {missing}。请先执行 scripts/init/init_rbac.py 初始化权限与角色。"
                )

        salt, pwd_hash = hash_password(args.password)
        existing = await UserDoc.find_one(UserDoc.user_id == args.user_id)

        if existing and not args.upsert:
            raise RuntimeError(f"用户已存在: {args.user_id}（如需覆盖请加 --upsert）")

        if existing and args.upsert:
            existing.username = args.username
            existing.email = args.email
            existing.status = args.status
            existing.role_ids = role_ids
            existing.password_salt = salt
            existing.password_hash = pwd_hash
            await existing.save()
            print(f"用户已更新: {args.user_id}")
            return

        await UserDoc(
            user_id=args.user_id,
            username=args.username,
            email=args.email,
            status=args.status,
            role_ids=role_ids,
            password_salt=salt,
            password_hash=pwd_hash,
        ).insert()
        print(f"用户创建成功: {args.user_id}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
