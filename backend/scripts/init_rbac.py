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

# (perm_id/code, 显示名称, 权限说明)
DEFAULT_PERMISSIONS: list[tuple[str, str, str]] = [
    (
        "nav:public",
        "公共导航",
        "登录后即可访问的公共页面（如首页、个人资料），不绑定具体业务角色。",
    ),
    (
        "nav:dashboard:view",
        "数据统计查看",
        "访问数据统计仪表盘页面，仅系统管理员默认拥有。",
    ),
    (
        "work_items:read",
        "工作流查看",
        "查看工作事项列表、详情、排序检索、流转日志及关联测试用例。",
    ),
    (
        "work_items:write",
        "工作流创建编辑",
        "创建、编辑、删除工作事项（需求/用例等工作流实体）。",
    ),
    (
        "work_items:transition",
        "工作流流转",
        "执行状态流转、改派负责人等流程操作。",
    ),
    (
        "users:read",
        "用户查看",
        "查看用户列表、用户详情及当前用户权限信息。",
    ),
    (
        "users:write",
        "用户管理",
        "创建、编辑、删除用户，修改密码与角色分配。",
    ),
    (
        "roles:read",
        "角色查看",
        "查看系统角色列表及角色已绑定的权限。",
    ),
    (
        "roles:write",
        "角色管理",
        "创建、编辑、删除角色，配置角色权限集合。",
    ),
    (
        "permissions:read",
        "权限查看",
        "查看系统权限项列表及权限说明。",
    ),
    (
        "permissions:write",
        "权限管理",
        "创建、编辑、删除权限定义（一般仅管理员使用）。",
    ),
    (
        "requirements:read",
        "需求查看",
        "查看测试需求列表、详情及关联信息。",
    ),
    (
        "requirements:write",
        "需求编辑",
        "创建、更新、删除测试需求业务数据。",
    ),
    (
        "test_cases:read",
        "测试用例查看",
        "查看测试用例列表、详情、目录路径及关联需求。",
    ),
    (
        "test_cases:write",
        "测试用例编辑",
        "创建、更新、删除测试用例及目录字段。",
    ),
    (
        "catalog:labs:read",
        "Lab 目录查看",
        "查看 Lab 列表、目录树与路径联想建议。",
    ),
    (
        "catalog:labs:manage",
        "Lab 目录管理",
        "创建/编辑/停用 Lab，维护目录结构。",
    ),
    (
        "duts:read",
        "被测设备查看",
        "查看被测设备（DUT）列表、配置与关联信息。",
    ),
    (
        "duts:write",
        "被测设备管理",
        "创建、编辑、删除被测设备（DUT）及绑定关系。",
    ),
    (
        "execution_tasks:read",
        "执行任务查看",
        "查看测试执行任务列表、状态与执行结果。",
    ),
    (
        "execution_tasks:write",
        "执行任务操作",
        "创建、调度、重跑、取消测试执行任务。",
    ),
    (
        "execution_agents:read",
        "执行 Agent 查看",
        "查看已注册的执行 Agent 及其在线状态。",
    ),
    (
        "execution_agents:write",
        "执行 Agent 管理",
        "注册、编辑、下线执行 Agent。",
    ),
    (
        "terminal:connect",
        "终端连接",
        "通过 Web 终端连接执行环境（调试/执行场景）。",
    ),
    (
        "navigation:read",
        "导航配置查看",
        "查看侧边栏导航页面配置。",
    ),
    (
        "navigation:write",
        "导航配置管理",
        "创建、编辑、删除导航页面及可见性配置。",
    ),
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
        "permission_ids": [code for code, _, _ in DEFAULT_PERMISSIONS],
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
    for code, name, description in DEFAULT_PERMISSIONS:
        existing = await PermissionDoc.find_one(PermissionDoc.perm_id == code)
        if existing:
            existing.name = name
            existing.description = description
            await existing.save()
        else:
            await PermissionDoc(
                perm_id=code,
                code=code,
                name=name,
                description=description,
            ).insert()


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
