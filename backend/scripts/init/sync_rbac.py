#!/usr/bin/env python3
"""Synchronize default RBAC roles.

Permissions are static application constants. This script only persists role
records and their selected permission codes.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.auth.permissions import PERMISSION_CODES  # noqa: E402
from app.modules.auth.repository.models import RoleDoc  # noqa: E402
from scripts.common.database import database_runtime  # noqa: E402

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


def _validated_permission_ids(permission_ids: list[str]) -> list[str]:
    unknown = sorted(set(permission_ids) - PERMISSION_CODES)
    if unknown:
        raise ValueError(f"默认角色引用了未定义的权限码: {unknown}")
    return sorted(set(permission_ids))


async def init_roles() -> None:
    role_payloads = {
        role_id: {
            "name": cfg["name"],
            "description": cfg.get("description"),
            "is_system": cfg.get("is_system", False),
            "permission_ids": _validated_permission_ids(cfg["permission_ids"]),
        }
        for role_id, cfg in DEFAULT_ROLES.items()
    }
    for role_id, payload in role_payloads.items():
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
    async with database_runtime(document_models=[RoleDoc]):
        await init_roles()
        print("RBAC 角色同步完成")


if __name__ == "__main__":
    asyncio.run(main())
