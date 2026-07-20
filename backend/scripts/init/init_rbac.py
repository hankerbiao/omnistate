#!/usr/bin/env python3
"""Initialize default RBAC roles.

Permissions are static application constants. This script only persists role
records and their selected permission codes.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from beanie import init_beanie
from pymongo import AsyncMongoClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.auth.permissions import PERMISSION_CODES
from app.modules.auth.repository.models import RoleDoc
from app.shared.config import get_settings

_READ = [
    "users:read",
    "requirements:read",
    "test_cases:read",
    "attachments:read",
    "catalog:labs:read",
    "work_items:read",
    "projects:read",
    "collections:read",
    "search:global",
]
_WORKFLOW = ["work_items:write", "work_items:transition"]
_ATTACHMENT_WRITE = ["attachments:upload", "attachments:delete"]
_EXEC_READ = ["execution_tasks:read", "execution_agents:read", "execution_plans:read"]
_EXEC_WRITE = ["execution_tasks:write", "execution_agents:write", "execution_plans:write"]

DEFAULT_ROLES = {
    "ADMIN": {
        "name": "ADMIN",
        "description": "系统管理员，拥有所有权限",
        "is_system": True,
        "permission_ids": sorted(PERMISSION_CODES),
    },
    "TPM": {
        "name": "TPM",
        "description": "测试项目管理员，负责项目管理和协调",
        "is_system": True,
        "permission_ids": [
            *_READ,
            "requirements:write",
            *_ATTACHMENT_WRITE,
            *_WORKFLOW,
            *_EXEC_READ,
            *_EXEC_WRITE,
            "catalog:labs:manage",
            "terminal:connect",
            "projects:write",
            "collections:write",
            "case_governance:read",
            "system:config",
        ],
    },
    "REVIEWER": {
        "name": "REVIEWER",
        "description": "评审者，审核需求和测试用例",
        "is_system": True,
        "permission_ids": [
            "users:read",
            "requirements:read",
            "requirements:write",
            "test_cases:read",
            "test_cases:write",
            "attachments:read",
            *_ATTACHMENT_WRITE,
            "work_items:read",
            *_WORKFLOW,
            "execution_tasks:read",
            "projects:read",
            "collections:read",
            "search:global",
            "case_governance:read",
        ],
    },
    "MANUAL_DEV": {
        "name": "MANUAL_DEV",
        "description": "手动测试开发工程师",
        "is_system": True,
        "permission_ids": [
            "users:read",
            "requirements:read",
            "test_cases:read",
            "test_cases:write",
            "attachments:read",
            *_ATTACHMENT_WRITE,
            "work_items:read",
            *_WORKFLOW,
            *_EXEC_READ,
            "collections:read",
            "search:global",
        ],
    },
    "QA": {
        "name": "QA",
        "description": "质量保证工程师",
        "is_system": True,
        "permission_ids": [
            *_READ,
            "requirements:write",
            "test_cases:write",
            *_ATTACHMENT_WRITE,
            *_WORKFLOW,
            *_EXEC_READ,
            *_EXEC_WRITE,
            "collections:write",
            "case_governance:read",
        ],
    },
    "TESTER": {
        "name": "TESTER",
        "description": "测试执行工程师",
        "is_system": True,
        "permission_ids": [
            *_READ,
            "test_cases:write",
            *_ATTACHMENT_WRITE,
            *_WORKFLOW,
            *_EXEC_READ,
            "execution_tasks:write",
            "execution_plans:write",
            "terminal:connect",
            "case_governance:read",
        ],
    },
    "AUTO_DEV": {
        "name": "AUTO_DEV",
        "description": "自动化测试开发工程师",
        "is_system": True,
        "permission_ids": [
            "users:read",
            "test_cases:read",
            "test_cases:write",
            "attachments:read",
            *_ATTACHMENT_WRITE,
            "work_items:read",
            *_WORKFLOW,
            *_EXEC_READ,
            *_EXEC_WRITE,
            "collections:read",
            "search:global",
        ],
    },
    "AUTOMATION": {
        "name": "AUTOMATION",
        "description": "自动化测试运行角色",
        "is_system": True,
        "permission_ids": [
            *_READ,
            "test_cases:write",
            "attachments:upload",
            *_WORKFLOW,
            *_EXEC_READ,
            *_EXEC_WRITE,
            "terminal:connect",
        ],
    },
}


def _valid_permission_ids(permission_ids: list[str]) -> list[str]:
    return sorted(pid for pid in set(permission_ids) if pid in PERMISSION_CODES)


async def init_roles() -> None:
    for role_id, cfg in DEFAULT_ROLES.items():
        payload = {
            "name": cfg["name"],
            "description": cfg.get("description"),
            "is_system": cfg.get("is_system", False),
            "permission_ids": _valid_permission_ids(cfg["permission_ids"]),
        }
        existing = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if existing:
            existing.name = payload["name"]
            existing.description = payload["description"]
            existing.is_system = payload["is_system"]
            existing.permission_ids = payload["permission_ids"]
            await existing.save()
        else:
            await RoleDoc(role_id=role_id, **payload).insert()


async def main() -> None:
    client = AsyncMongoClient(get_settings().mongodb.uri)
    try:
        await init_beanie(
            database=client[get_settings().mongodb.db_name],
            document_models=[RoleDoc],
        )
        await init_roles()
        print("RBAC 角色初始化完成")
    finally:
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    asyncio.run(main())
