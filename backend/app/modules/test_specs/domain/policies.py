from typing import Any

from app.modules.workflow.domain.policies import (
    actor_role_ids,
    can_delete_work_item,
    is_admin_actor,
)
from app.modules.workflow.repository.models.enums import WorkItemState


def _read_value(source: Any, field: str, default: Any = None) -> Any:
    """从 dict 或对象中读取字段，统一兼容测试中的轻量假对象和真实文档对象。"""
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(field, default)
    return getattr(source, field, default)


def _actor_id(actor: Any) -> str:
    """提取操作者 ID，并去除空白字符，避免权限比较时受输入格式影响。"""
    if isinstance(actor, dict):
        return str(actor.get("actor_id") or actor.get("user_id") or "").strip()
    return str(getattr(actor, "actor_id", "")).strip()


def _normalized_roles(actor: Any) -> set[str]:
    roles: set[str] = set()
    for role_id in actor_role_ids(actor):
        normalized = role_id.strip().upper()
        if normalized.startswith("ROLE_"):
            normalized = normalized[5:]
        if normalized:
            roles.add(normalized)
    return roles


def _can_edit_via_work_item(actor: Any, work_item: Any) -> bool:
    """工作流驱动的编辑权限：待办主责可改，草稿阶段创建人可改。

    - 评审态（PENDING_REVIEW）禁止编辑正文/步骤，评审意见仅通过流转提交。
    - ADMIN 不享有编辑直通（改派/删除见 workflow policies）。
    """
    if work_item is None:
        return False

    current_actor_id = _actor_id(actor)
    if not current_actor_id:
        return False

    state = str(_read_value(work_item, "current_state", "") or "").strip().upper()
    if state == WorkItemState.PENDING_REVIEW.value:
        return False

    owner_id = str(_read_value(work_item, "current_owner_id", "") or "").strip()
    if owner_id and current_actor_id == owner_id:
        return True

    if state == WorkItemState.DRAFT.value:
        creator_id = str(_read_value(work_item, "creator_id", "") or "").strip()
        if creator_id and current_actor_id == creator_id:
            return True

    return False


def can_create_requirement(actor: Any) -> bool:
    """
    需求创建策略：
    - 管理员始终允许；
    - TPM 角色允许创建需求。
    """
    return is_admin_actor(actor) or "TPM" in _normalized_roles(actor)


def can_update_requirement(actor: Any, requirement: Any, work_item: Any = None) -> bool:
    """
    需求可编辑策略（只认工作流）：
    - 当前处理人（current_owner_id）允许（评审态除外）；
    - DRAFT 状态下创建人（creator_id）允许；
    - PENDING_REVIEW 禁止编辑；ADMIN 不直通。
    """
    return _can_edit_via_work_item(actor, work_item)


def can_delete_requirement(actor: Any, requirement: Any, work_item: Any = None) -> bool:
    """
    需求可删除策略（只认工作流）：
    - 管理员始终允许；
    - 关联工作项存在时复用工作项删除策略（创建人或管理员）。
    """
    if is_admin_actor(actor):
        return True
    if work_item is not None and can_delete_work_item(actor, work_item):
        return True
    return False


def can_update_test_case(actor: Any, test_case: Any, work_item: Any = None) -> bool:
    """
    测试用例可编辑策略：
    放开工作流限制，API 层权限（test_cases:write）通过即可编辑。
    """
    return True


def can_delete_test_case(actor: Any, test_case: Any, work_item: Any = None) -> bool:
    """
    测试用例可删除策略（只认工作流）：
    - 管理员始终允许；
    - 关联工作项存在时复用工作项删除策略（创建人或管理员）。
    """
    if is_admin_actor(actor):
        return True
    if work_item is not None and can_delete_work_item(actor, work_item):
        return True
    return False
