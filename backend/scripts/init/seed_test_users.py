#!/usr/bin/env python3
"""一键创建测试用户和角色。

为开发和演示环境创建多个测试账号，方便用户切换和查看不同角色视角。
默认密码统一为 Test@123。

用法:
  python scripts/seed_test_users.py                           # 创建所有测试用户
  python scripts/seed_test_users.py --reset                   # 覆盖已存在的用户
  python scripts/seed_test_users.py --password Pass@456       # 自定义密码
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
from app.modules.auth.repository.models import UserDoc, RoleDoc, PermissionDoc

# 与 init_rbac.py 保持一致的权限名称/说明（完整列表请运行 init_rbac.py）
ALL_PERMISSIONS = [
    ("work_items:read", "工作流查看", "查看工作事项列表、详情、排序检索、流转日志及关联测试用例。"),
    ("work_items:write", "工作流创建编辑", "创建、编辑、删除工作事项（需求/用例等工作流实体）。"),
    ("work_items:transition", "工作流流转", "执行状态流转、改派负责人等流程操作。"),
    ("users:read", "用户查看", "查看用户列表、用户详情及当前用户权限信息。"),
    ("users:write", "用户管理", "创建、编辑、删除用户，修改密码与角色分配。"),
    ("roles:read", "角色查看", "查看系统角色列表及角色已绑定的权限。"),
    ("roles:write", "角色管理", "创建、编辑、删除角色，配置角色权限集合。"),
    ("permissions:read", "权限查看", "查看系统权限项列表及权限说明。"),
    ("permissions:write", "权限管理", "创建、编辑、删除权限定义（一般仅管理员使用）。"),
    ("requirements:read", "需求查看", "查看测试需求列表、详情及关联信息。"),
    ("requirements:write", "需求编辑", "创建、更新、删除测试需求业务数据。"),
    ("test_cases:read", "测试用例查看", "查看测试用例列表、详情、目录路径及关联需求。"),
    ("test_cases:write", "测试用例编辑", "创建、更新、删除测试用例及目录字段。"),
    ("navigation:read", "导航配置查看", "查看侧边栏导航页面配置。"),
    ("navigation:write", "导航配置管理", "创建、编辑、删除导航页面及可见性配置。"),
]

# 测试角色定义: (role_id, name, permission_codes)
TEST_ROLES = [
    ("TPM", "项目经理", ["work_items:read", "work_items:write", "work_items:transition",
                         "requirements:read", "requirements:write",
                         "test_cases:read",
                         "users:read", "navigation:read"]),
    ("REVIEWER", "审核人", ["work_items:read", "work_items:transition",
                           "requirements:read",
                           "test_cases:read",
                           "users:read", "navigation:read"]),
    ("MANUAL_DEV", "测试开发", ["work_items:read", "work_items:transition",
                                "requirements:read",
                                "test_cases:read", "test_cases:write",
                                "users:read", "navigation:read"]),
    ("QA", "质量保证", ["work_items:read", "work_items:transition",
                        "requirements:read",
                        "test_cases:read",
                        "users:read", "navigation:read"]),
    ("TESTER", "测试执行", ["work_items:read", "work_items:transition",
                           "requirements:read", "test_cases:read",
                           "users:read", "navigation:read"]),
]

# 测试用户定义: (user_id, username, role_ids)
TEST_USERS = [
    ("admin", "管理员", ["ADMIN"]),
    ("tpm", "项目经理", ["TPM"]),
    ("reviewer", "审核人", ["REVIEWER"]),
    ("dev", "开发人员", ["MANUAL_DEV"]),
    ("qa", "质量保证", ["QA"]),
    ("tester", "测试人员", ["TESTER"]),
]


async def ensure_permissions():
    """确保所有预置权限存在。"""
    for code, name, description in ALL_PERMISSIONS:
        await PermissionDoc.find_one(PermissionDoc.perm_id == code).upsert(
            {"$set": {"code": code, "name": name, "description": description}},
            on_insert=PermissionDoc(
                perm_id=code, code=code, name=name, description=description
            ),
        )
    print(f"  ✓ 已确保 {len(ALL_PERMISSIONS)} 个权限存在")


async def ensure_roles():
    """创建测试角色。"""
    for role_id, name, perm_codes in TEST_ROLES:
        exists = await RoleDoc.find_one(RoleDoc.role_id == role_id)
        if exists:
            print(f"  - 角色已存在: {role_id}")
            continue
        await RoleDoc(
            role_id=role_id,
            name=name,
            permission_ids=perm_codes,
        ).insert()
        print(f"  ✓ 角色创建: {role_id} ({name})")


async def ensure_admin_role():
    """创建 ADMIN 角色（全部权限）。"""
    exists = await RoleDoc.find_one(RoleDoc.role_id == "ADMIN")
    if exists:
        print(f"  - 角色已存在: ADMIN")
        return
    all_ids = [code for code, _ in ALL_PERMISSIONS]
    await RoleDoc(
        role_id="ADMIN",
        name="管理员",
        permission_ids=all_ids,
    ).insert()
    print(f"  ✓ 角色创建: ADMIN (管理员)")


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
    parser = argparse.ArgumentParser(description="一键创建测试用户")
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
            document_models=[UserDoc, RoleDoc, PermissionDoc],
        )

        print("\n[1/3] 初始化权限...")
        await ensure_permissions()

        print("\n[2/3] 初始化角色...")
        await ensure_admin_role()
        await ensure_roles()

        print(f"\n[3/3] 创建测试用户 (密码: {args.password})...")
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
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    asyncio.run(main())
