from typing import Any, Iterable

from app.modules.workflow.domain.policies import can_delete_work_item, is_admin_actor


def _read_value(source: Any, field: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(field, default)
    return getattr(source, field, default)


def _actor_id(actor: Any) -> str:
    if isinstance(actor, dict):
        return str(actor.get("actor_id") or actor.get("user_id") or "").strip()
    return str(getattr(actor, "actor_id", "")).strip()


def _matches_any(actor_id: str, candidates: Iterable[Any]) -> bool:
    normalized = actor_id.strip()
    return any(normalized and normalized == str(candidate).strip() for candidate in candidates if candidate is not None)


def can_update_requirement(actor: Any, requirement: Any, work_item: Any = None) -> bool:
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
    if is_admin_actor(actor):
        return True
    if work_item is not None and can_delete_work_item(actor, work_item):
        return True
    return _matches_any(_actor_id(actor), [_read_value(requirement, "tpm_owner_id")])


def can_update_test_case(actor: Any, test_case: Any, work_item: Any = None) -> bool:
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


def can_dispatch_execution(actor: Any, cases: Iterable[Any]) -> bool:
    if is_admin_actor(actor):
        return True
    case_list = list(cases)
    if not case_list:
        return False
    return all(can_update_test_case(actor, test_case=case) for case in case_list)


def can_delete_test_case(actor: Any, test_case: Any, work_item: Any = None) -> bool:
    if is_admin_actor(actor):
        return True
    if work_item is not None and can_delete_work_item(actor, work_item):
        return True
    return _matches_any(_actor_id(actor), [_read_value(test_case, "owner_id")])
