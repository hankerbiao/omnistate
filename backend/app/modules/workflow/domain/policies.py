from typing import Any, Iterable


def _read_value(source: Any, field: str, default: Any = None) -> Any:
    """
    安全地从对象或字典中读取属性值。

    Args:
        source: 源对象（字典或对象）
        field: 要读取的字段名
        default: 当字段不存在时返回的默认值

    Returns:
        字段值或默认值
    """
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(field, default)
    return getattr(source, field, default)


def actor_id(actor: Any) -> str:
    """
    获取参与者的唯一标识符。

    优先从actor_id字段获取，如果没有则从user_id字段获取，
    最终转换为字符串并去除首尾空格。

    Args:
        actor: 参与者对象

    Returns:
        参与者ID字符串
    """
    return str(_read_value(actor, "actor_id", _read_value(actor, "user_id", ""))).strip()


def actor_role_ids(actor: Any) -> list[str]:
    """
    获取参与者的所有角色ID列表。

    Args:
        actor: 参与者对象

    Returns:
        角色ID字符串列表
    """
    return [str(role_id) for role_id in (_read_value(actor, "role_ids", []) or [])]


def is_admin_actor(actor: Any) -> bool:
    """
    检查当前参与者是否为管理员。

    通过检查角色ID中是否包含"ADMIN"字符串来判断是否为管理员。

    Args:
        actor: 参与者对象

    Returns:
        True如果参与者是管理员，否则False
    """
    return any("ADMIN" in role_id.upper() for role_id in actor_role_ids(actor))


def _matches_actor_type(actor: Any, work_item: Any, actor_type: str) -> bool:
    """
    检查参与者是否匹配指定的参与者类型。

    支持的参与者类型包括：
    - admin: 管理员参与者
    - creator: 工作项创建者
    - owner/current_owner: 当前负责人
    - system: 系统参与者
    - reviewer: 审核员

    Args:
        actor: 参与者对象
        work_item: 工作项对象
        actor_type: 参与者类型字符串

    Returns:
        True如果参与者匹配指定类型，否则False
    """
    normalized = str(actor_type).strip().lower()
    current_actor_id = actor_id(actor)
    if normalized == "admin":
        return is_admin_actor(actor)
    if normalized == "creator":
        return current_actor_id == str(_read_value(work_item, "creator_id", "")).strip()
    if normalized in {"owner", "current_owner"}:
        return current_actor_id == str(_read_value(work_item, "current_owner_id", "")).strip()
    if normalized == "system":
        return current_actor_id.lower() == "system"
    if normalized == "reviewer":
        return _has_any_role(actor, ["REVIEWER", "ROLE_REVIEWER"])
    return False


def _has_any_role(actor: Any, allowed_role_ids: Iterable[str]) -> bool:
    """
    检查参与者是否具有任何指定角色。

    Args:
        actor: 参与者对象
        allowed_role_ids: 允许的角色ID集合

    Returns:
        True如果参与者具有任何指定角色，否则False
    """
    actor_roles = {role_id.upper() for role_id in actor_role_ids(actor)}
    expected_roles = {str(role_id).upper() for role_id in allowed_role_ids if str(role_id).strip()}
    return not expected_roles.isdisjoint(actor_roles)


def can_transition(actor: Any, work_item: Any, workflow_config: Any) -> bool:
    """
    检查参与者是否可以对工作项执行状态转换。

    管理员总是可以执行转换。
    如果配置了owner_only或creator_only限制，则按相应规则检查。
    否则检查allowed_actor_types或allowed_role_ids配置。
    如果都没有配置，则默认允许创建者和当前负责人执行转换。

    Args:
        actor: 参与者对象
        work_item: 工作项对象
        workflow_config: 工作流配置对象

    Returns:
        True如果参与者可以执行转换，否则False
    """
    if is_admin_actor(actor):
        return True

    properties = _read_value(workflow_config, "properties", {}) or {}
    if properties.get("owner_only"):
        return _matches_actor_type(actor, work_item, "current_owner")
    if properties.get("creator_only"):
        return _matches_actor_type(actor, work_item, "creator")

    allowed_actor_types = properties.get("allowed_actor_types") or []
    allowed_role_ids = properties.get("allowed_role_ids") or []

    if allowed_actor_types:
        if not any(_matches_actor_type(actor, work_item, actor_type) for actor_type in allowed_actor_types):
            return False
    elif allowed_role_ids:
        if not _has_any_role(actor, allowed_role_ids):
            return False
    else:
        if not (
                _matches_actor_type(actor, work_item, "creator")
                or _matches_actor_type(actor, work_item, "current_owner")
        ):
            return False

    return True


def can_reassign(actor: Any, work_item: Any) -> bool:
    """
    检查参与者是否可以重新分配工作项。

    只有管理员或当前负责人可以重新分配工作项。

    Args:
        actor: 参与者对象
        work_item: 工作项对象

    Returns:
        True如果参与者可以重新分配，否则False
    """
    return is_admin_actor(actor) or _matches_actor_type(actor, work_item, "current_owner")


def can_delete_work_item(actor: Any, work_item: Any) -> bool:
    """
    检查参与者是否可以删除工作项。

    只有管理员或工作项创建者可以删除工作项。

    Args:
        actor: 参与者对象
        work_item: 工作项对象

    Returns:
        True如果参与者可以删除工作项，否则False
    """
    return is_admin_actor(actor) or _matches_actor_type(actor, work_item, "creator")
