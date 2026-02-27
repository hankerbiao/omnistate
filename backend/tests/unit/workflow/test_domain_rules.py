import pytest

from app.modules.workflow.domain.exceptions import MissingRequiredFieldError
from app.modules.workflow.domain.rules import (
    ensure_required_fields,
    build_process_payload,
    resolve_owner,
    normalize_sort,
)


def test_ensure_required_fields_missing():
    with pytest.raises(MissingRequiredFieldError):
        ensure_required_fields(["comment", "reason"], {"comment": "ok"})


def test_build_process_payload_includes_required_and_optional_remark():
    payload = build_process_payload(["comment"], {"comment": "ok", "remark": "r"})
    assert payload == {"comment": "ok", "remark": "r"}


def test_resolve_owner_keep():
    owner_id = resolve_owner("KEEP", {"current_owner_id": 7, "creator_id": 1}, {})
    assert owner_id == 7


def test_resolve_owner_creator():
    owner_id = resolve_owner("TO_CREATOR", {"current_owner_id": 7, "creator_id": 1}, {})
    assert owner_id == 1


def test_resolve_owner_specific_user_missing():
    with pytest.raises(MissingRequiredFieldError):
        resolve_owner("TO_SPECIFIC_USER", {"current_owner_id": 7, "creator_id": 1}, {})


def test_normalize_sort():
    assert normalize_sort("created_at", "desc") == "-created_at"
    assert normalize_sort("updated_at", "asc") == "updated_at"
    assert normalize_sort("invalid", "desc") == "-created_at"
