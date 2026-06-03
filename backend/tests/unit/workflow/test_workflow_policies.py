"""工作流 domain 权限策略单元测试。"""

from app.modules.workflow.domain.policies import can_delete_work_item, can_reassign, can_transition


def _actor(actor_id: str, role_ids: list[str] | None = None) -> dict:
    return {"actor_id": actor_id, "role_ids": role_ids or []}


def _work_item(
    *,
    creator_id: str = "creator",
    current_owner_id: str = "owner",
    current_state: str = "PENDING_REVIEW",
) -> dict:
    return {
        "creator_id": creator_id,
        "current_owner_id": current_owner_id,
        "current_state": current_state,
    }


def _config(**properties) -> dict:
    return {"properties": properties}


class TestCanTransition:
    def test_admin_cannot_bypass_when_not_owner(self):
        actor = _actor("admin", ["ADMIN"])
        item = _work_item(creator_id="admin", current_owner_id="reviewer")
        config = _config(owner_only=True)

        assert can_transition(actor, item, config) is False

    def test_admin_can_transition_when_owner(self):
        actor = _actor("admin", ["ADMIN"])
        item = _work_item(creator_id="other", current_owner_id="admin")
        config = _config(owner_only=True)

        assert can_transition(actor, item, config) is True

    def test_reviewer_owner_can_approve(self):
        actor = _actor("reviewer", ["REVIEWER"])
        item = _work_item(current_owner_id="reviewer")
        config = _config(owner_only=True)

        assert can_transition(actor, item, config) is True

    def test_reviewer_without_ownership_cannot_approve(self):
        actor = _actor("reviewer", ["REVIEWER"])
        item = _work_item(current_owner_id="other_reviewer")
        config = _config(owner_only=True)

        assert can_transition(actor, item, config) is False

    def test_creator_only_submit(self):
        actor = _actor("creator", ["ADMIN"])
        item = _work_item(creator_id="creator", current_owner_id="creator", current_state="DRAFT")
        config = _config(creator_only=True)

        assert can_transition(actor, item, config) is True

    def test_non_creator_cannot_submit(self):
        actor = _actor("admin", ["ADMIN"])
        item = _work_item(creator_id="tpm", current_owner_id="tpm", current_state="DRAFT")
        config = _config(creator_only=True)

        assert can_transition(actor, item, config) is False

    def test_default_allows_creator_or_owner(self):
        actor = _actor("owner")
        item = _work_item(creator_id="creator", current_owner_id="owner")
        config = _config()

        assert can_transition(actor, item, config) is True

    def test_default_denies_unrelated_user(self):
        actor = _actor("stranger", ["REVIEWER"])
        item = _work_item(creator_id="creator", current_owner_id="owner")
        config = _config()

        assert can_transition(actor, item, config) is False

    def test_allowed_role_ids_without_owner_still_role_based(self):
        actor = _actor("reviewer", ["REVIEWER"])
        item = _work_item(current_owner_id="someone_else")
        config = _config(allowed_role_ids=["REVIEWER"])

        assert can_transition(actor, item, config) is True


class TestAdminOtherOperations:
    def test_admin_can_reassign_without_ownership(self):
        actor = _actor("admin", ["ADMIN"])
        item = _work_item(current_owner_id="reviewer")

        assert can_reassign(actor, item) is True

    def test_admin_can_delete_without_being_creator(self):
        actor = _actor("admin", ["ADMIN"])
        item = _work_item(creator_id="other")

        assert can_delete_work_item(actor, item) is True
