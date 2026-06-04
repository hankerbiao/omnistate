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
    ("catalog:labs:read", "Catalog labs read"),
    ("catalog:labs:manage", "Catalog labs manage"),
    ("execution_tasks:read", "Execution tasks read"),
    ("execution_tasks:write", "Execution tasks write"),
    ("execution_agents:read", "Execution agents read"),
    ("execution_agents:write", "Execution agents write"),
    ("terminal:connect", "Terminal connect"),
    ("navigation:read", "Navigation read"),
    ("navigation:write", "Navigation write"),
]

# 公共权限分组
_READ = [
    "users:read",
    "requirements:read",
    "test_cases:read",
    "catalog:labs:read",
    "work_items:read",
    "navigation:read",
]
_WORKFLOW = ["work_items:write", "work_items:transition"]
_EXEC_READ = ["execution_tasks:read", "execution_agents:read"]
_EXEC_WRITE = ["execution_tasks:write", "execution_agents:write"]

DEFAULT_ROLES = {
    "ADMIN": {
        "name": "ADMIN", "description": "系统管理员，拥有所有权限", "is_system": True,
        "permission_ids": [code for code, _ in DEFAULT_PERMISSIONS],
    },
    "TPM": {
        "name": "TPM", "description": "测试项目管理员，负责项目管理和协调", "is_system": True,
        "permission_ids": [
            *_READ,
            "requirements:write",
            *_WORKFLOW,
            *_EXEC_READ,
            *_EXEC_WRITE,
            "catalog:labs:manage",
            "terminal:connect",
            "navigation:write",
        ],
    },
    "REVIEWER": {
        "name": "REVIEWER", "description": "评审者，审核需求和测试用例", "is_system": True,
        "permission_ids": ["users:read", "requirements:read", "requirements:write", "test_cases:read", "test_cases:write", "work_items:read", *_WORKFLOW, "execution_tasks:read", "navigation:read"],
    },
    "MANUAL_DEV": {
        "name": "MANUAL_DEV", "description": "手动测试开发工程师", "is_system": True,
        "permission_ids": ["users:read", "requirements:read", "test_cases:read", "test_cases:write", "work_items:read", *_WORKFLOW, *_EXEC_READ, "navigation:read"],
    },
    "QA": {
        "name": "QA", "description": "质量保证工程师", "is_system": True,
        "permission_ids": [*_READ, "requirements:write", "test_cases:write", *_WORKFLOW, *_EXEC_READ, *_EXEC_WRITE],
    },
    "TESTER": {
        "name": "TESTER", "description": "测试执行工程师", "is_system": True,
        "permission_ids": [*_READ, "test_cases:write", *_WORKFLOW, "execution_tasks:read", "terminal:connect", "navigation:write"],
    },
    "AUTO_DEV": {
        "name": "AUTO_DEV", "description": "自动化测试开发工程师", "is_system": True,
        "permission_ids": [_READ[0], "test_cases:read", "test_cases:write", "work_items:read", *_WORKFLOW, *_EXEC_READ, *_EXEC_WRITE, "navigation:read"],
    },
    "AUTOMATION": {
        "name": "AUTOMATION", "description": "自动化测试运行角色", "is_system": True,
        "permission_ids": [*_READ, "test_cases:write", *_WORKFLOW, *_EXEC_READ, *_EXEC_WRITE, "terminal:connect", "navigation:write"],
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
            # 如果角色已存在，更新字段（但保留系统角色标志）
            existing.name = cfg["name"]
            existing.description = cfg.get("description")
            if not existing.is_system:  # 不覆盖系统角色的 is_system 标志
                existing.is_system = cfg.get("is_system", False)
            existing.permission_ids = cfg["permission_ids"]
            await existing.save()
        else:
            # 如果角色不存在，创建新的角色
            new_role = RoleDoc(
                role_id=role_id,
                name=cfg["name"],
                description=cfg.get("description"),
                is_system=cfg.get("is_system", False),
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
