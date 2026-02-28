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
    ("work_items:read", "Workflow read"),
    ("work_items:write", "Workflow write"),
    ("work_items:transition", "Workflow transition"),
    ("users:read", "Users read"),
    ("users:write", "Users write"),
    ("roles:read", "Roles read"),
    ("roles:write", "Roles write"),
    ("permissions:read", "Permissions read"),
    ("permissions:write", "Permissions write"),
    ("menu:read", "Menu read"),
    ("menu:write", "Menu write"),
    ("assets:read", "Assets read"),
    ("assets:write", "Assets write"),
    ("requirements:read", "Requirements read"),
    ("requirements:write", "Requirements write"),
    ("test_cases:read", "Test cases read"),
    ("test_cases:write", "Test cases write"),
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
            "work_items:transition",
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
            "work_items:transition",
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
        ],
    },
}


async def init_permissions() -> None:
    for code, name in DEFAULT_PERMISSIONS:
        await PermissionDoc.find_one(PermissionDoc.perm_id == code).upsert(
            {"$set": {"code": code, "name": name}},
            on_insert=PermissionDoc(perm_id=code, code=code, name=name),
        )


async def init_roles() -> None:
    for role_id, cfg in DEFAULT_ROLES.items():
        await RoleDoc.find_one(RoleDoc.role_id == role_id).upsert(
            {"$set": {"name": cfg["name"], "permission_ids": cfg["permission_ids"]}},
            on_insert=RoleDoc(role_id=role_id, name=cfg["name"], permission_ids=cfg["permission_ids"]),
        )


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
