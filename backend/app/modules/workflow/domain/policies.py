from typing import Any, Iterable


def _read_value(source: Any, field: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(field, default)
    return getattr(source, field, default)


def actor_id(actor: Any) -> str:
    return str(_read_value(actor, "actor_id", _read_value(actor, "user_id", ""))).strip()


def actor_role_ids(actor: Any) -> list[str]:
    return [str(role_id) for role_id in (_read_value(actor, "role_ids", []) or [])]


def is_admin_actor(actor: Any) -> bool:
    return any("ADMIN" in role_id.upper() for role_id in actor_role_ids(actor))


def _matches_actor_type(actor: Any, work_item: Any, actor_type: str) -> bool:
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
    return False


def _has_any_role(actor: Any, allowed_role_ids: Iterable[str]) -> bool:
    actor_roles = {role_id.upper() for role_id in actor_role_ids(actor)}
    expected_roles = {str(role_id).upper() for role_id in allowed_role_ids if str(role_id).strip()}
    return not expected_roles.isdisjoint(actor_roles)


def can_transition(actor: Any, work_item: Any, workflow_config: Any) -> bool:
    if is_admin_actor(actor):
        return True

    properties = _read_value(workflow_config, "properties", {}) or {}
    if properties.get("owner_only"):
        return _matches_actor_type(actor, work_item, "current_owner")
    if properties.get("creator_only"):
        return _matches_actor_type(actor, work_item, "creator")

    allowed_actor_types = properties.get("allowed_actor_types") or []
    if allowed_actor_types:
        if not any(_matches_actor_type(actor, work_item, actor_type) for actor_type in allowed_actor_types):
            return False
    else:
        if not (
            _matches_actor_type(actor, work_item, "creator")
            or _matches_actor_type(actor, work_item, "current_owner")
        ):
            return False

    allowed_role_ids = properties.get("allowed_role_ids") or []
    if allowed_role_ids and not _has_any_role(actor, allowed_role_ids):
        return False

    return True


def can_reassign(actor: Any, work_item: Any) -> bool:
    return is_admin_actor(actor) or _matches_actor_type(actor, work_item, "current_owner")


def can_delete_work_item(actor: Any, work_item: Any) -> bool:
    return is_admin_actor(actor) or _matches_actor_type(actor, work_item, "creator")
