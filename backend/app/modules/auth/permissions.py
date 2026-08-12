"""Static permission registry for RBAC.

Permissions are application contract, not runtime data. API routes use these codes
for authorization, and role records store the selected codes directly.
"""
from __future__ import annotations

from typing import TypedDict


class PermissionDef(TypedDict):
    perm_id: str
    code: str
    name: str
    description: str


_PERMISSION_ROWS: list[tuple[str, str, str]] = [
    ("nav:public", "公共导航", "登录后即可访问的公共页面。"),
    ("work_items:read", "工作流查看", "查看工作事项列表、详情、流转日志及关联测试用例。"),
    ("work_items:write", "工作流创建编辑", "创建、编辑、删除工作事项。"),
    ("work_items:transition", "工作流流转", "执行状态流转、改派负责人等流程操作。"),
    ("users:read", "用户查看", "查看用户列表、用户详情及当前用户权限信息。"),
    ("users:write", "用户管理", "创建、编辑、删除用户与角色分配。"),
    ("roles:read", "角色查看", "查看系统角色列表及角色已绑定的权限。"),
    ("roles:write", "角色管理", "创建、编辑、删除角色，配置角色权限集合。"),
    ("permissions:read", "权限查看", "查看系统权限项列表及权限说明。"),
    ("requirements:read", "需求查看", "查看测试需求列表、详情及关联信息。"),
    ("requirements:write", "需求编辑", "创建、更新、删除测试需求业务数据。"),
    ("test_cases:read", "测试用例查看", "查看测试用例列表、详情、目录路径及关联需求。"),
    ("test_cases:write", "测试用例编辑", "创建、更新、删除测试用例及目录字段。"),
    ("attachments:read", "附件查看", "查看附件元数据、列表及下载链接。"),
    ("attachments:upload", "附件上传", "上传附件并创建附件元数据。"),
    ("attachments:delete", "附件删除", "删除本人上传且未被业务引用的附件。"),
    ("attachments:manage", "附件管理", "跨用户查看、下载和删除附件。"),
    ("catalog:labs:read", "Lab 目录查看", "查看 Lab 列表、目录树与路径联想建议。"),
    ("catalog:labs:manage", "Lab 目录管理", "创建/编辑/停用 Lab，维护目录结构。"),
    ("projects:read", "项目查看", "查看项目列表、详情和统计数据。"),
    ("projects:create", "项目创建", "创建新的测试项目。"),
    ("projects:write", "项目编辑", "编辑项目及修改项目配置。"),
    ("projects:delete", "项目删除", "删除项目及其关联数据。"),
]

PERMISSIONS: tuple[PermissionDef, ...] = tuple(
    {"perm_id": code, "code": code, "name": name, "description": description}
    for code, name, description in _PERMISSION_ROWS
)

PERMISSION_CODES: frozenset[str] = frozenset(item["code"] for item in PERMISSIONS)
PERMISSION_BY_ID: dict[str, PermissionDef] = {item["perm_id"]: item for item in PERMISSIONS}


def list_permissions() -> list[PermissionDef]:
    # Keep both identifiers for API consumers: ``perm_id`` is the domain
    # identifier, while ``id`` preserves the generic response contract.
    return [{**item, "id": item["perm_id"]} for item in PERMISSIONS]


def permission_exists(permission_id: str) -> bool:
    return permission_id in PERMISSION_BY_ID


def permission_codes_by_ids(permission_ids: list[str]) -> list[str]:
    return sorted({pid for pid in permission_ids if pid in PERMISSION_BY_ID})
