#!/usr/bin/env python3
"""创建 RBAC 用户脚本。

前提：必须先执行 scripts/init/sync_rbac.py 初始化角色。

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
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.auth.repository.models import UserDoc, RoleDoc  # noqa: E402
from scripts.common.database import database_runtime  # noqa: E402
from scripts.common.users import write_user  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建 RBAC 用户")
    parser.add_argument("--user-id", required=True, help="用户唯一 ID")
    parser.add_argument("--username", required=True, help="用户名")
    password_group = parser.add_mutually_exclusive_group(required=True)
    password_group.add_argument("--password", help="登录密码（明文输入，脚本内加密）")
    password_group.add_argument(
        "--password-env",
        metavar="ENV_NAME",
        help="从环境变量读取密码，避免密码出现在进程参数中",
    )
    parser.add_argument("--roles", default="", help="角色列表，逗号分隔，例如 ADMIN,TESTER")
    parser.add_argument("--email", default=None, help="邮箱")
    parser.add_argument("--status", default="ACTIVE", choices=["ACTIVE", "DISABLED"], help="用户状态")
    parser.add_argument("--upsert", action="store_true", help="若用户存在则更新用户信息和密码")
    return parser.parse_args()


def resolve_password(args: argparse.Namespace) -> str:
    """Resolve the password without requiring it in the process command line."""
    if args.password_env:
        password = os.getenv(args.password_env)
        if not password:
            raise RuntimeError(f"密码环境变量未设置或为空: {args.password_env}")
        return password
    if not args.password:
        raise RuntimeError("必须提供密码")
    return args.password


async def main() -> None:
    args = parse_args()
    password = resolve_password(args)
    role_ids = [r.strip() for r in args.roles.split(",") if r.strip()]

    async with database_runtime(document_models=[UserDoc, RoleDoc]):
        result = await write_user(
            user_id=args.user_id,
            username=args.username,
            email=args.email,
            status=args.status,
            role_ids=role_ids,
            password=password,
            existing_policy="update" if args.upsert else "error",
        )
        action = "更新" if result == "updated" else "创建"
        print(f"用户{action}成功: {args.user_id}")


if __name__ == "__main__":
    asyncio.run(main())
