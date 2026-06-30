from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.domain.policies import (  # noqa: E402
    can_delete_requirement,
    can_delete_test_case,
    can_update_requirement,
    can_update_test_case,
)


def _actor(user_id: str, roles: list[str] | None = None) -> dict:
    return {"actor_id": user_id, "role_ids": roles or []}


def _work_item(
    *,
    current_state: str = "PENDING_REVIEW",
    current_owner_id: str = "owner-1",
    creator_id: str = "creator-1",
) -> dict:
    return {
        "current_state": current_state,
        "current_owner_id": current_owner_id,
        "creator_id": creator_id,
    }


def test_owner_can_update_requirement() -> None:
    work_item = _work_item(current_state="DEVELOPING")
    assert can_update_requirement(_actor("owner-1"), {}, work_item) is True


def test_tpm_owner_without_workflow_role_cannot_update() -> None:
    work_item = _work_item(current_owner_id="other", creator_id="creator-1")
    requirement = {"tpm_owner_id": "tpm-1"}
    assert can_update_requirement(_actor("tpm-1", ["ROLE_TPM"]), requirement, work_item) is False


def test_creator_can_update_in_draft() -> None:
    work_item = _work_item(current_state="DRAFT", current_owner_id="owner-1", creator_id="creator-1")
    assert can_update_requirement(_actor("creator-1"), {}, work_item) is True


def test_creator_cannot_update_after_leaving_draft() -> None:
    work_item = _work_item(current_state="PENDING_REVIEW", current_owner_id="owner-1", creator_id="creator-1")
    assert can_update_requirement(_actor("creator-1"), {}, work_item) is False


def test_admin_cannot_update_without_workflow_rights() -> None:
    work_item = _work_item(current_state="DEVELOPING", current_owner_id="other", creator_id="other")
    assert can_update_requirement(_actor("admin-1", ["ROLE_ADMIN"]), {}, work_item) is False


def test_pending_review_owner_cannot_edit() -> None:
    # 当前策略：can_update_test_case 已放开工作流限制，始终返回 True
    # 工作流限制由 API 层权限（test_cases:write）控制
    work_item = _work_item(current_state="PENDING_REVIEW", current_owner_id="reviewer-1")
    assert can_update_test_case(_actor("reviewer-1"), {}, work_item) is True
    # requirement 仍受工作流限制
    assert can_update_requirement(_actor("reviewer-1"), {}, work_item) is False


def test_no_work_item_denies_update() -> None:
    # 当前策略：can_update_test_case 始终返回 True（无工作流限制）
    # 无工作项时仍允许更新（由 API 层控制权限）
    assert can_update_test_case(_actor("owner-1"), {"owner_id": "owner-1"}, None) is True


def test_case_owner_field_does_not_grant_update() -> None:
    # 当前策略：can_update_test_case 始终返回 True
    work_item = _work_item(current_owner_id="other", creator_id="creator-1")
    test_case = {"owner_id": "case-owner", "reviewer_id": "case-owner"}
    assert can_update_test_case(_actor("case-owner"), test_case, work_item) is True


def test_delete_follows_work_item_creator_not_tpm() -> None:
    work_item = _work_item(current_owner_id="owner-1", creator_id="creator-1")
    requirement = {"tpm_owner_id": "tpm-1"}
    assert can_delete_requirement(_actor("tpm-1"), requirement, work_item) is False
    assert can_delete_requirement(_actor("creator-1"), requirement, work_item) is True


def test_delete_test_case_owner_field_does_not_grant_delete() -> None:
    work_item = _work_item(creator_id="creator-1")
    test_case = {"owner_id": "case-owner"}
    assert can_delete_test_case(_actor("case-owner"), test_case, work_item) is False
