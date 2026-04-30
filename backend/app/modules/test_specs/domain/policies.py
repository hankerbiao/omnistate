from typing import Any, Iterable

from app.modules.workflow.domain.policies import can_delete_work_item, is_admin_actor


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


def _matches_any(actor_id: str, candidates: Iterable[Any]) -> bool:
    """判断操作者 ID 是否匹配任一候选负责人 ID，忽略 None 和首尾空白。"""
    normalized = actor_id.strip()
    return any(normalized and normalized == str(candidate).strip() for candidate in candidates if candidate is not None)


def can_update_requirement(actor: Any, requirement: Any, work_item: Any = None) -> bool:
    """
    需求可编辑策略：
    - 管理员始终允许；
    - 关联工作项的当前负责人或创建人允许；
    - 需求的 TPM 负责人允许。
    """
    current_actor_id = _actor_id(actor)
    if is_admin_actor(actor):
        return True
    if work_item is not None and _matches_any(
        current_actor_id,
        [_read_value(work_item, "current_owner_id"), _read_value(work_item, "creator_id")],
    ):
        return True
    return _matches_any(current_actor_id, [_read_value(requirement, "tpm_owner_id")])


def can_delete_requirement(actor: Any, requirement: Any, work_item: Any = None) -> bool:
    """
    需求可删除策略：
    - 管理员始终允许；
    - 如果存在关联工作项，则复用工作项删除策略；
    - 需求的 TPM 负责人允许。
    """
    if is_admin_actor(actor):
        return True
    if work_item is not None and can_delete_work_item(actor, work_item):
        return True
    return _matches_any(_actor_id(actor), [_read_value(requirement, "tpm_owner_id")])


def can_update_test_case(actor: Any, test_case: Any, work_item: Any = None) -> bool:
    """
    测试用例可编辑策略：
    - 管理员始终允许；
    - 关联工作项的当前负责人或创建人允许；
    - 用例负责人、评审人或自动化开发负责人允许。
    """
    current_actor_id = _actor_id(actor)
    if is_admin_actor(actor):
        return True
    if work_item is not None and _matches_any(
        current_actor_id,
        [_read_value(work_item, "current_owner_id"), _read_value(work_item, "creator_id")],
    ):
        return True
    return _matches_any(
        current_actor_id,
        [
            _read_value(test_case, "owner_id"),
            _read_value(test_case, "reviewer_id"),
            _read_value(test_case, "auto_dev_id"),
        ],
    )


def can_delete_test_case(actor: Any, test_case: Any, work_item: Any = None) -> bool:
    """
    测试用例可删除策略：
    - 管理员始终允许；
    - 如果存在关联工作项，则复用工作项删除策略；
    - 用例负责人允许。
    """
    if is_admin_actor(actor):
        return True
    if work_item is not None and can_delete_work_item(actor, work_item):
        return True
    return _matches_any(_actor_id(actor), [_read_value(test_case, "owner_id")])
