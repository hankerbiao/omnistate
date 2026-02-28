import asyncio
from types import SimpleNamespace

import pytest
from pymongo.errors import DuplicateKeyError

from app.modules.workflow.service.workflow_service import AsyncWorkflowService
from app.modules.workflow.domain.exceptions import (
    MissingRequiredFieldError,
    InvalidTransitionError,
    WorkItemNotFoundError,
)
from tests.fakes.workflow import (
    FakeQuery,
    FakeWorkItemDoc,
    FakeConfigDoc,
    FakeFlowLog,
)


@pytest.fixture()
def service(monkeypatch):
    # 提供一个干净的服务实例，便于单元测试复用
    service = AsyncWorkflowService()

    class _FakeTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def start_transaction(self):
            return _FakeTransaction()

    class _FakeClient:
        def start_session(self):
            return _FakeSession()

    monkeypatch.setattr(service, "_get_mongo_client_or_none", lambda: _FakeClient())
    return service


def test_list_items_sorted_uses_domain_sort(monkeypatch, service):
    # 验证排序字段被 normalize_sort 处理，并正确传递给查询对象
    docs = [SimpleNamespace(id="1")]
    query = FakeQuery(docs)

    def fake_base_query(*args, **kwargs):
        return query

    def fake_docs_to_dicts(docs_in):
        return [{"id": str(docs_in[0].id)}]

    monkeypatch.setattr(service, "_base_item_query", fake_base_query)
    monkeypatch.setattr(service, "_docs_to_dicts", fake_docs_to_dicts)
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.normalize_sort",
        lambda order_by, direction: "-created_at",
    )

    # 执行并断言排序表达式与分页参数
    result = asyncio.run(
        service.list_items_sorted(order_by="created_at", direction="desc", limit=10, offset=5)
    )

    assert query.sort_expr == "-created_at"
    assert query.skipped == 5
    assert query.limited == 10
    assert result == [{"id": "1"}]


def test_handle_transition_success(monkeypatch, service):
    # 验证正常流转：状态、处理人、日志写入均符合预期
    work_item_id = "507f1f77bcf86cd799439011"
    item_doc = FakeWorkItemDoc(
        id=work_item_id,
        type_code="REQUIREMENT",
        title="t",
        content="c",
        parent_item_id=None,
        current_state="DRAFT",
        current_owner_id=10,
        creator_id=10,
        is_deleted=False,
    )
    config_doc = FakeConfigDoc(
        type_code="REQUIREMENT",
        from_state="DRAFT",
        action="SUBMIT",
        to_state="PENDING_REVIEW",
        required_fields=["comment"],
        target_owner_strategy="TO_CREATOR",
    )

    async def fake_get(item_id):
        assert item_id == work_item_id
        return item_doc

    async def fake_find_one(*args, **kwargs):
        return config_doc

    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.BusWorkItemDoc.get", fake_get
    )
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.SysWorkflowConfigDoc.find_one", fake_find_one
    )
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.BusFlowLogDoc", FakeFlowLog
    )
    async def fake_find_requirement_none(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.TestRequirementDoc.find_one",
        fake_find_requirement_none,
    )

    # 调用流转并断言结果
    result = asyncio.run(
        service.handle_transition(
            work_item_id=work_item_id,
            action="SUBMIT",
            operator_id=99,
            form_data={"comment": "ok"},
        )
    )

    assert item_doc.current_state == "PENDING_REVIEW"
    assert item_doc.current_owner_id == 10
    assert item_doc.saved is True
    assert FakeFlowLog.inserted is True
    assert FakeFlowLog.payload == {"comment": "ok"}
    assert result["work_item_id"] == work_item_id
    assert result["from_state"] == "DRAFT"
    assert result["to_state"] == "PENDING_REVIEW"
    assert result["action"] == "SUBMIT"
    assert result["new_owner_id"] == 10


def test_handle_transition_sync_business_status_failure_raises(monkeypatch, service):
    # 验证业务实体状态同步失败时不再吞错，直接抛异常以触发回滚
    work_item_id = "507f1f77bcf86cd799439011"
    item_doc = FakeWorkItemDoc(
        id=work_item_id,
        type_code="REQUIREMENT",
        title="t",
        content="c",
        parent_item_id=None,
        current_state="DRAFT",
        current_owner_id=10,
        creator_id=10,
        is_deleted=False,
    )
    config_doc = FakeConfigDoc(
        type_code="REQUIREMENT",
        from_state="DRAFT",
        action="SUBMIT",
        to_state="PENDING_REVIEW",
        required_fields=["comment"],
        target_owner_strategy="TO_CREATOR",
    )

    class BrokenRequirement:
        def __init__(self):
            self.status = "DRAFT"

        async def save(self):
            raise RuntimeError("sync failed")

    async def fake_get(item_id):
        return item_doc

    async def fake_find_one(*args, **kwargs):
        return config_doc

    async def fake_find_requirement(*args, **kwargs):
        return BrokenRequirement()

    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.BusWorkItemDoc.get", fake_get
    )
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.SysWorkflowConfigDoc.find_one", fake_find_one
    )
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.TestRequirementDoc.find_one",
        fake_find_requirement,
    )
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.BusFlowLogDoc", FakeFlowLog
    )

    with pytest.raises(RuntimeError, match="sync failed"):
        asyncio.run(
            service.handle_transition(
                work_item_id=work_item_id,
                action="SUBMIT",
                operator_id=99,
                form_data={"comment": "ok"},
            )
        )


def test_handle_transition_missing_required_field(monkeypatch, service):
    # 验证缺少必填字段时抛出 MissingRequiredFieldError
    work_item_id = "507f1f77bcf86cd799439011"
    item_doc = FakeWorkItemDoc(
        id=work_item_id,
        type_code="REQUIREMENT",
        title="t",
        content="c",
        parent_item_id=None,
        current_state="DRAFT",
        current_owner_id=10,
        creator_id=10,
        is_deleted=False,
    )
    config_doc = FakeConfigDoc(
        type_code="REQUIREMENT",
        from_state="DRAFT",
        action="SUBMIT",
        to_state="PENDING_REVIEW",
        required_fields=["comment"],
        target_owner_strategy="TO_CREATOR",
    )

    async def fake_get(item_id):
        return item_doc

    async def fake_find_one(*args, **kwargs):
        return config_doc

    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.BusWorkItemDoc.get", fake_get
    )
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.SysWorkflowConfigDoc.find_one", fake_find_one
    )

    # 缺少 comment 字段，应该报错
    with pytest.raises(MissingRequiredFieldError):
        asyncio.run(
            service.handle_transition(
                work_item_id=work_item_id,
                action="SUBMIT",
                operator_id=99,
                form_data={},
            )
        )


def test_handle_transition_invalid_config(monkeypatch, service):
    # 验证当找不到匹配流转配置时抛出 InvalidTransitionError
    work_item_id = "507f1f77bcf86cd799439011"
    item_doc = FakeWorkItemDoc(
        id=work_item_id,
        type_code="REQUIREMENT",
        title="t",
        content="c",
        parent_item_id=None,
        current_state="DRAFT",
        current_owner_id=10,
        creator_id=10,
        is_deleted=False,
    )

    async def fake_get(item_id):
        return item_doc

    async def fake_find_one(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.BusWorkItemDoc.get", fake_get
    )
    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.SysWorkflowConfigDoc.find_one", fake_find_one
    )

    # 没有对应配置时应抛错
    with pytest.raises(InvalidTransitionError):
        asyncio.run(
            service.handle_transition(
                work_item_id=work_item_id,
                action="SUBMIT",
                operator_id=99,
                form_data={"comment": "ok"},
            )
        )


def test_handle_transition_item_not_found(monkeypatch, service):
    # 验证事项不存在时抛出 WorkItemNotFoundError
    async def fake_get(item_id):
        return None

    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.BusWorkItemDoc.get", fake_get
    )

    # 事项不存在时应抛错
    with pytest.raises(WorkItemNotFoundError):
        asyncio.run(
            service.handle_transition(
                work_item_id="507f1f77bcf86cd799439011",
                action="SUBMIT",
                operator_id=99,
                form_data={"comment": "ok"},
            )
        )


def test_create_item_duplicate_key_raises_value_error(monkeypatch, service):
    # 验证并发冲突触发 DuplicateKeyError 时转换为业务冲突异常
    class FakeBusWorkItemDoc:
        def __init__(self, **kwargs):
            self.id = "507f1f77bcf86cd799439011"
            self.parent_item_id = kwargs.get("parent_item_id")
            self.current_state = "DRAFT"

        @staticmethod
        async def find_one(*args, **kwargs):
            return None

        async def insert(self, session=None):
            raise DuplicateKeyError("dup")

        def model_dump(self):
            return {
                "id": self.id,
                "parent_item_id": self.parent_item_id,
                "current_state": self.current_state,
            }

    monkeypatch.setattr(
        "app.modules.workflow.service.workflow_service.BusWorkItemDoc", FakeBusWorkItemDoc
    )

    with pytest.raises(ValueError, match="已存在相同标题的REQUIREMENT"):
        asyncio.run(
            service.create_item(
                type_code="REQUIREMENT",
                title="same-title",
                content="c",
                creator_id="u1",
            )
        )


def test_batch_get_logs_invalid_object_id_raises_value_error(service):
    # 批量查询日志时，任意非法 ObjectId 都应被识别并返回 400 级错误
    with pytest.raises(ValueError, match="invalid item_ids"):
        asyncio.run(
            service.batch_get_logs(
                ["invalid-id", "507f1f77bcf86cd799439011"],
                limit=10,
            )
        )


def test_search_items_keyword_too_short_raises_value_error(service):
    # 关键词长度过短时应提前失败，避免无意义的扫描查询
    with pytest.raises(ValueError, match="keyword length must be at least 2"):
        asyncio.run(service.search_items(keyword="a"))
