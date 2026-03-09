"""测试规格策略测试"""
import pytest

from app.modules.test_specs.domain.policies import (
    can_update_requirement,
    can_delete_requirement,
    can_update_test_case,
    can_delete_test_case,
    can_dispatch_execution,
    is_admin_actor,
)


class TestRequirementPolicies:
    """需求策略测试套件"""

    def test_admin_can_update_any_requirement(self):
        """测试管理员可以更新任何需求"""
        admin_actor = {"actor_id": "admin-1", "role_ids": ["ROLE_ADMIN"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert can_update_requirement(admin_actor, requirement, work_item)

    def test_requirement_owner_can_update(self):
        """测试需求拥有者可以更新"""
        owner = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert can_update_requirement(owner, requirement, work_item)

    def test_work_item_owner_or_creator_can_update_requirement(self):
        """测试工作项拥有者或创建者可以更新需求"""
        work_item_owner = {"actor_id": "user-2", "role_ids": ["ROLE_USER"]}
        work_item_creator = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert can_update_requirement(work_item_owner, requirement, work_item)
        assert can_update_requirement(work_item_creator, requirement, work_item)

    def test_unauthorized_user_cannot_update_requirement(self):
        """测试未授权用户不能更新需求"""
        unauthorized = {"actor_id": "user-4", "role_ids": ["ROLE_USER"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert not can_update_requirement(unauthorized, requirement, work_item)

    def test_admin_can_delete_requirement(self):
        """测试管理员可以删除需求"""
        admin_actor = {"actor_id": "admin-1", "role_ids": ["ROLE_ADMIN"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert can_delete_requirement(admin_actor, requirement, work_item)

    def test_work_item_creator_can_delete_requirement(self):
        """测试工作项创建者可以删除需求"""
        creator = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert can_delete_requirement(creator, requirement, work_item)

    def test_requirement_owner_can_delete_when_no_work_item(self):
        """测试没有工作项时，需求拥有者可以删除"""
        owner = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = None

        assert can_delete_requirement(owner, requirement, work_item)

    def test_unauthorized_user_cannot_delete_requirement(self):
        """测试未授权用户不能删除需求"""
        unauthorized = {"actor_id": "user-4", "role_ids": ["ROLE_USER"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert not can_delete_requirement(unauthorized, requirement, work_item)


class TestTestCasePolicies:
    """测试用例策略测试套件"""

    def test_admin_can_update_any_test_case(self):
        """测试管理员可以更新任何测试用例"""
        admin_actor = {"actor_id": "admin-1", "role_ids": ["ROLE_ADMIN"]}
        test_case = {"owner_id": "user-1", "reviewer_id": "user-2", "auto_dev_id": "user-3"}
        work_item = {"current_owner_id": "user-4", "creator_id": "user-5"}

        assert can_update_test_case(admin_actor, test_case, work_item)

    def test_test_case_owner_can_update(self):
        """测试测试用例拥有者可以更新"""
        owner = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        test_case = {"owner_id": "user-1", "reviewer_id": "user-2", "auto_dev_id": "user-3"}
        work_item = {"current_owner_id": "user-4", "creator_id": "user-5"}

        assert can_update_test_case(owner, test_case, work_item)

    def test_test_case_reviewer_can_update(self):
        """测试测试用例审核者可以更新"""
        reviewer = {"actor_id": "user-2", "role_ids": ["ROLE_USER"]}
        test_case = {"owner_id": "user-1", "reviewer_id": "user-2", "auto_dev_id": "user-3"}
        work_item = {"current_owner_id": "user-4", "creator_id": "user-5"}

        assert can_update_test_case(reviewer, test_case, work_item)

    def test_auto_dev_can_update(self):
        """测试自动化开发者可以更新"""
        auto_dev = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        test_case = {"owner_id": "user-1", "reviewer_id": "user-2", "auto_dev_id": "user-3"}
        work_item = {"current_owner_id": "user-4", "creator_id": "user-5"}

        assert can_update_test_case(auto_dev, test_case, work_item)

    def test_work_item_owner_or_creator_can_update_test_case(self):
        """测试工作项拥有者或创建者可以更新测试用例"""
        work_item_owner = {"actor_id": "user-4", "role_ids": ["ROLE_USER"]}
        work_item_creator = {"actor_id": "user-5", "role_ids": ["ROLE_USER"]}
        test_case = {"owner_id": "user-1", "reviewer_id": "user-2", "auto_dev_id": "user-3"}
        work_item = {"current_owner_id": "user-4", "creator_id": "user-5"}

        assert can_update_test_case(work_item_owner, test_case, work_item)
        assert can_update_test_case(work_item_creator, test_case, work_item)

    def test_unauthorized_user_cannot_update_test_case(self):
        """测试未授权用户不能更新测试用例"""
        unauthorized = {"actor_id": "user-6", "role_ids": ["ROLE_USER"]}
        test_case = {"owner_id": "user-1", "reviewer_id": "user-2", "auto_dev_id": "user-3"}
        work_item = {"current_owner_id": "user-4", "creator_id": "user-5"}

        assert not can_update_test_case(unauthorized, test_case, work_item)

    def test_admin_can_delete_test_case(self):
        """测试管理员可以删除测试用例"""
        admin_actor = {"actor_id": "admin-1", "role_ids": ["ROLE_ADMIN"]}
        test_case = {"owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert can_delete_test_case(admin_actor, test_case, work_item)

    def test_work_item_creator_can_delete_test_case(self):
        """测试工作项创建者可以删除测试用例"""
        creator = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        test_case = {"owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert can_delete_test_case(creator, test_case, work_item)

    def test_test_case_owner_can_delete_when_no_work_item(self):
        """测试没有工作项时，测试用例拥有者可以删除"""
        owner = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        test_case = {"owner_id": "user-1"}
        work_item = None

        assert can_delete_test_case(owner, test_case, work_item)

    def test_unauthorized_user_cannot_delete_test_case(self):
        """测试未授权用户不能删除测试用例"""
        unauthorized = {"actor_id": "user-4", "role_ids": ["ROLE_USER"]}
        test_case = {"owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-3"}

        assert not can_delete_test_case(unauthorized, test_case, work_item)


class TestDispatchExecutionPolicies:
    """执行调度策略测试套件"""

    def test_admin_can_dispatch_any_execution(self):
        """测试管理员可以调度任何执行"""
        admin_actor = {"actor_id": "admin-1", "role_ids": ["ROLE_ADMIN"]}
        test_cases = [
            {"owner_id": "user-1"},
            {"owner_id": "user-2"},
        ]

        assert can_dispatch_execution(admin_actor, test_cases)

    def test_user_can_dispatch_owned_test_cases(self):
        """测试用户可以调度拥有的测试用例"""
        actor = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        test_cases = [
            {"owner_id": "user-1"},
            {"owner_id": "user-1"},
        ]

        assert can_dispatch_execution(actor, test_cases)

    def test_user_cannot_dispatch_unowned_test_cases(self):
        """测试用户不能调度非拥有的测试用例"""
        actor = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        test_cases = [
            {"owner_id": "user-1"},
            {"owner_id": "user-2"},
        ]

        assert not can_dispatch_execution(actor, test_cases)

    def test_cannot_dispatch_empty_test_cases(self):
        """测试不能调度空测试用例列表"""
        actor = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}

        assert not can_dispatch_execution(actor, [])

    def test_endpoint_permission_passes_but_resource_policy_fails(self):
        """测试端点权限通过但资源策略失败的情况"""
        unauthorized = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        requirement = {"tpm_owner_id": "user-1"}
        work_item = {"current_owner_id": "user-2", "creator_id": "user-4"}
        test_case = {"owner_id": "user-1"}

        # 模拟用户有端点权限但不是需求拥有者、工作项拥有者或创建者
        assert not can_update_requirement(unauthorized, requirement, work_item)
        assert not can_update_test_case(unauthorized, test_case, work_item)
        assert not can_delete_requirement(unauthorized, requirement, work_item)
        assert not can_delete_test_case(unauthorized, test_case, work_item)