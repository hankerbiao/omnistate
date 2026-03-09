"""工作流策略测试"""
import pytest

from app.modules.workflow.domain.policies import (
    can_transition,
    can_reassign,
    can_delete_work_item,
    is_admin_actor,
)


class TestWorkflowPolicies:
    """工作流策略测试套件"""

    def test_admin_actor_has_all_permissions(self):
        """测试管理员拥有所有权限"""
        admin_actor = {"actor_id": "admin-1", "role_ids": ["ROLE_ADMIN"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {}

        assert is_admin_actor(admin_actor)
        assert can_transition(admin_actor, work_item, workflow_config)
        assert can_reassign(admin_actor, work_item)
        assert can_delete_work_item(admin_actor, work_item)

    def test_creator_can_transition_when_allowed(self):
        """测试创建者可以在允许时进行状态转换"""
        creator = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {}

        assert can_transition(creator, work_item, workflow_config)

    def test_owner_can_transition_when_allowed(self):
        """测试当前拥有者可以进行状态转换"""
        owner = {"actor_id": "user-2", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {}

        assert can_transition(owner, work_item, workflow_config)

    def test_non_owner_non_creator_cannot_transition(self):
        """测试非拥有者非创建者不能进行状态转换"""
        other_user = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {}

        assert not can_transition(other_user, work_item, workflow_config)

    def test_creator_can_delete_work_item(self):
        """测试创建者可以删除工作项"""
        creator = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}

        assert can_delete_work_item(creator, work_item)

    def test_non_creator_cannot_delete_work_item(self):
        """测试非创建者不能删除工作项"""
        other_user = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}

        assert not can_delete_work_item(other_user, work_item)

    def test_owner_can_reassign(self):
        """测试当前拥有者可以重新分配"""
        owner = {"actor_id": "user-2", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}

        assert can_reassign(owner, work_item)

    def test_non_owner_cannot_reassign(self):
        """测试非拥有者不能重新分配"""
        other_user = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}

        assert not can_reassign(other_user, work_item)

    def test_workflow_config_owner_only_restriction(self):
        """测试工作流配置的所有者唯一限制"""
        owner = {"actor_id": "user-2", "role_ids": ["ROLE_USER"]}
        non_owner = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {"properties": {"owner_only": True}}

        assert can_transition(owner, work_item, workflow_config)
        assert not can_transition(non_owner, work_item, workflow_config)

    def test_workflow_config_creator_only_restriction(self):
        """测试工作流配置的创建者唯一限制"""
        creator = {"actor_id": "user-1", "role_ids": ["ROLE_USER"]}
        non_creator = {"actor_id": "user-2", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {"properties": {"creator_only": True}}

        assert can_transition(creator, work_item, workflow_config)
        assert not can_transition(non_creator, work_item, workflow_config)

    def test_workflow_config_allowed_actor_types(self):
        """测试工作流配置的允许执行者类型"""
        reviewer = {"actor_id": "user-3", "role_ids": ["ROLE_REVIEWER"]}
        other_user = {"actor_id": "user-4", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {"properties": {"allowed_actor_types": ["reviewer"]}}

        assert can_transition(reviewer, work_item, workflow_config)
        assert not can_transition(other_user, work_item, workflow_config)

    def test_workflow_config_allowed_role_ids(self):
        """测试工作流配置的允许角色ID"""
        reviewer = {"actor_id": "user-3", "role_ids": ["ROLE_REVIEWER"]}
        regular_user = {"actor_id": "user-4", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {"properties": {"allowed_role_ids": ["ROLE_REVIEWER"]}}

        assert can_transition(reviewer, work_item, workflow_config)
        assert not can_transition(regular_user, work_item, workflow_config)

    def test_system_actor_has_special_semantics(self):
        """测试系统执行者具有特殊语义"""
        system = {"actor_id": "system", "role_ids": ["ROLE_SYSTEM"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {"properties": {"allowed_actor_types": ["system"]}}

        assert can_transition(system, work_item, workflow_config)

    def test_endpoint_permission_passes_but_resource_policy_fails(self):
        """测试端点权限通过但资源策略失败的情况"""
        other_user = {"actor_id": "user-3", "role_ids": ["ROLE_USER"]}
        work_item = {"creator_id": "user-1", "current_owner_id": "user-2"}
        workflow_config = {}

        # 模拟用户有端点权限但不是创建者或拥有者
        assert not can_transition(other_user, work_item, workflow_config)
        assert not can_reassign(other_user, work_item)
        assert not can_delete_work_item(other_user, work_item)