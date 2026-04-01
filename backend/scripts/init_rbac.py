#!/usr/bin/env python3
"""初始化 RBAC 默认权限与角色。

用途：
- 初始化 permissions 集合
- 初始化 roles 集合（包含 ADMIN 全量权限）
- 可重复执行，幂等更新

用法：
python scripts/init_rbac.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from beanie import init_beanie
from pymongo import AsyncMongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings
from app.modules.auth.repository.models import PermissionDoc, RoleDoc

DEFAULT_PERMISSIONS = [
    ("nav:public", "Public navigation (all logged-in users)"),  # 公共页面权限
    ("work_items:read", "Workflow read"),
    ("work_items:write", "Workflow write"),
    ("work_items:transition", "Workflow transition"),
    ("users:read", "Users read"),
    ("users:write", "Users write"),
    ("roles:read", "Roles read"),
    ("roles:write", "Roles write"),
    ("permissions:read", "Permissions read"),
    ("permissions:write", "Permissions write"),
    ("requirements:read", "Requirements read"),
    ("requirements:write", "Requirements write"),
    ("test_cases:read", "Test cases read"),
    ("test_cases:write", "Test cases write"),
    ("execution_tasks:read", "Execution tasks read"),
    ("execution_tasks:write", "Execution tasks write"),
    ("terminal:connect", "Terminal connect"),
    ("navigation:read", "Navigation read"),
    ("navigation:write", "Navigation write"),
]

DEFAULT_ROLES = {
    "ADMIN": {
        "name": "ADMIN",
        "permission_ids": [code for code, _ in DEFAULT_PERMISSIONS],
    },
    "TPM": {
        "name": "TPM",
        "permission_ids": [
            "users:read",
            "requirements:read",
            "requirements:write",
            "test_cases:read",
            "work_items:read",
            "work_items:write",
            "work_items:transition",
            "execution_tasks:read",
            "execution_tasks:write",
            "terminal:connect",
            "navigation:read",
            "navigation:write",
        ],
    },
    "TESTER": {
        "name": "TESTER",
        "permission_ids": [
            "users:read",
            "requirements:read",
            "test_cases:read",
            "test_cases:write",
            "work_items:read",
            "work_items:write",
            "work_items:transition",
            "execution_tasks:read",
            "terminal:connect",
            "navigation:read",
            "navigation:write",
        ],
    },
    "AUTOMATION": {
        "name": "AUTOMATION",
        "permission_ids": [
            "users:read",
            "test_cases:read",
            "test_cases:write",
            "assets:read",
            "work_items:read",
            "work_items:write",
            "execution_tasks:read",
            "terminal:connect",
            "navigation:read",
            "navigation:write",
        ],
    },
}


async def init_permissions() -> None:
    for code, name in DEFAULT_PERMISSIONS:
        existing = await PermissionDoc.find_one(PermissionDoc.perm_id == code)
        if existing:
            # 如果权限已存在，更新名称
            existing.name = name
            await existing.save()
        else:
            # 如果权限不存在，创建新的权限
            new_permission = PermissionDoc(
                perm_id=code,
                code=code,
                name=name,
                description=None
            )
            await new_permission.insert()


async def init_roles() -> None:
    for role_id, cfg in DEFAULT_ROLES.items():
        existing = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if existing:
            # 如果角色已存在，更新名称和权限
            existing.name = cfg["name"]
            existing.permission_ids = cfg["permission_ids"]
            await existing.save()
        else:
            # 如果角色不存在，创建新的角色
            new_role = RoleDoc(
                role_id=role_id,
                name=cfg["name"],
                permission_ids=cfg["permission_ids"]
            )
            await new_role.insert()


async def main() -> None:
    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[PermissionDoc, RoleDoc],
        )
        await init_permissions()
        await init_roles()
        print("RBAC 初始化完成")
    finally:
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    asyncio.run(main())
