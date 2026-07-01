"""test_case_service 单元测试 — 字段安全校验、负责人分配、需求迁移、逻辑删除"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.service.test_case_service import TestCaseService  # noqa: E402
from app.modules.workflow.application import WorkflowItemGateway  # noqa: E402


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


SERVICE = "app.modules.test_specs.service.test_case_service"


# ══════════════════════════════════════════════
#  Fake Documents
# ══════════════════════════════════════════════

class _FakeField:
    def __init__(self, name):
        self._name = name
    def __eq__(self, other):
        return _FakeExpr(self._name, other)


class _FakeExpr:
    def __init__(self, field, value):
        self._field = field
        self._value = value


class _FakeTestCaseDoc:
    store: dict[str, "_FakeTestCaseDoc"] = {}
    case_id = _FakeField("case_id")
    ref_req_id = _FakeField("ref_req_id")
    owner_id = _FakeField("owner_id")
    reviewer_id = _FakeField("reviewer_id")
    lab_id = _FakeField("lab_id")
    is_active = _FakeField("is_active")
    priority = _FakeField("priority")

    def __init__(self, **payload):
        self.id = f"case-{payload.get('case_id', 'unknown')}"
        for k, v in payload.items():
            setattr(self, k, v)
        if not hasattr(self, "catalog_path"):
            self.catalog_path = None
        if not hasattr(self, "lab_id"):
            self.lab_id = None
        if not hasattr(self, "workflow_item_id"):
            self.workflow_item_id = None

    async def save(self):
        self.__class__.store[getattr(self, "case_id", str(id(self)))] = self

    def model_dump(self) -> dict:
        data = {}
        for attr in ["case_id", "title", "ref_req_id", "owner_id", "reviewer_id", "auto_dev_id",
                      "lab_id", "catalog_path", "catalog_path_key", "workflow_item_id",
                      "is_deleted", "steps", "status", "created_at", "updated_at"]:
            val = getattr(self, attr, None)
            if val is not None:
                data[attr] = val
        data["id"] = str(id(self))
        return data

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def find_one(cls, *args, **kwargs):
        async def _coro():
            if args and isinstance(args[0], _FakeExpr):
                expr = args[0]
                for doc in cls.store.values():
                    if getattr(doc, expr._field, None) == expr._value and not getattr(doc, "is_deleted", False):
                        return doc
            elif args and isinstance(args[0], dict):
                cond = {k: v for k, v in args[0].items() if k != "is_deleted"}
                for doc in cls.store.values():
                    match = all(getattr(doc, k, None) == v for k, v in cond.items())
                    if match and not getattr(doc, "is_deleted", False):
                        return doc
            return None
        return _coro()

    @classmethod
    def find(cls, expr=None):
        class _Query:
            def __init__(self, docs):
                self._docs = docs
            def find(self, _expr):
                return self
            def sort(self, *args, **kwargs):
                return self
            def skip(self, n):
                return self
            def limit(self, n):
                return self
            async def to_list(self):
                return self._docs
            async def count(self):
                return len(self._docs)
        docs = [d for d in cls.store.values() if not getattr(d, "is_deleted", False)]
        if isinstance(expr, _FakeExpr):
            docs = [d for d in docs if getattr(d, expr._field, None) == expr._value]
        return _Query(docs)


class _FakeRequirementDoc:
    store: dict[str, "_FakeRequirementDoc"] = {}
    req_id = _FakeField("req_id")

    def __init__(self, **payload):
        for k, v in payload.items():
            setattr(self, k, v)

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def find_one(cls, *args, **kwargs):
        async def _coro():
            if args and isinstance(args[0], _FakeExpr):
                expr = args[0]
                for doc in cls.store.values():
                    if getattr(doc, expr._field, None) == expr._value and not getattr(doc, "is_deleted", False):
                        return doc
            return None
        return _coro()


class _FakeAutomationDoc:
    store: dict[str, "_FakeAutomationDoc"] = {}
    auto_case_id = _FakeField("auto_case_id")

    def __init__(self, **payload):
        for k, v in payload.items():
            setattr(self, k, v)

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def find_one(cls, *args, **kwargs):
        async def _coro():
            return None
        return _coro()


class _FakeTestCaseRepository:
    """基于 _FakeTestCaseDoc 内存存储的测试用仓储。

    实现 TestCaseRepositoryProtocol，供 TestCaseService 构造器注入，
    避免单元测试触碰真实 Beanie Document（未 init_beanie 时类属性访问会报错）。
    所有读写均委托给 _FakeTestCaseDoc 的类方法，与既有内存存储保持一致。
    """

    async def find_active_by_case_id(self, case_id: str):
        return await _FakeTestCaseDoc.find_one(_FakeTestCaseDoc.case_id == case_id)

    async def find_by_case_id(self, case_id: str):
        for doc in _FakeTestCaseDoc.store.values():
            if getattr(doc, "case_id", None) == case_id:
                return doc
        return None

    async def insert(self, doc, session=None):
        key = getattr(doc, "case_id", str(id(doc)))
        _FakeTestCaseDoc.store[key] = doc
        return doc

    async def save(self, doc, session=None):
        key = getattr(doc, "case_id", str(id(doc)))
        _FakeTestCaseDoc.store[key] = doc
        return doc

    async def count(self, filter_doc):
        docs = [d for d in _FakeTestCaseDoc.store.values()
                if not getattr(d, "is_deleted", False)]
        result = 0
        for d in docs:
            match = all(getattr(d, k, None) == v
                        for k, v in filter_doc.items() if k != "is_deleted")
            if match:
                result += 1
        return result

    def build_find_query(self, mongo_query):
        return _FakeTestCaseDoc.find(mongo_query)

    async def get_mongo_client(self):
        return None


@pytest.fixture(autouse=True)
def reset_stores():
    _FakeTestCaseDoc.reset()
    _FakeRequirementDoc.reset()
    _FakeAutomationDoc.reset()
    yield
    _FakeTestCaseDoc.reset()
    _FakeRequirementDoc.reset()
    _FakeAutomationDoc.reset()


def _make_case(case_id: str, **overrides) -> _FakeTestCaseDoc:
    attrs = dict(case_id=case_id, title="Test Case", is_deleted=False)
    attrs.update(overrides)
    doc = _FakeTestCaseDoc(**attrs)
    _FakeTestCaseDoc.store[case_id] = doc
    return doc


def build_service():
    gw = AsyncMock(spec=WorkflowItemGateway)
    catalog = MagicMock()
    catalog.enrich_case_dict = AsyncMock(side_effect=lambda x: x)
    catalog.prepare_catalog_fields = AsyncMock(return_value={
        "lab_id": "LAB-BIOS", "catalog_path": ["bios"], "catalog_path_key": "bios",
    })
    catalog.adjust_path_on_update = AsyncMock()
    catalog.register_path = AsyncMock()
    # 注入基于 _FakeTestCaseDoc 内存存储的仓储，避免触碰真实 Beanie Document
    repo = _FakeTestCaseRepository()
    return TestCaseService(workflow_gateway=gw, catalog_service=catalog, case_repository=repo)


# ══════════════════════════════════════════════
#  Tests: update_test_case — safe field enforcement
# ══════════════════════════════════════════════

def test_update_test_case_allows_owner_id():
    """owner_id 已在 _UPDATABLE_FIELDS 中，更新不再抛异常。"""
    service = build_service()
    _make_case("TC-001", title="Old")
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.enrich_projected_status", AsyncMock(side_effect=lambda x: x)):
        result = asyncio_run(service.update_test_case("TC-001", {"owner_id": "u-2"}))
        assert result["owner_id"] == "u-2"


def test_update_test_case_allows_ref_req_id():
    """ref_req_id 已在 _UPDATABLE_FIELDS 中，更新不再抛异常。"""
    service = build_service()
    _make_case("TC-001", title="Old")
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.enrich_projected_status", AsyncMock(side_effect=lambda x: x)):
        result = asyncio_run(service.update_test_case("TC-001", {"ref_req_id": "TR-NEW"}))
        assert result["ref_req_id"] == "TR-NEW"


def test_update_test_case_not_found():
    service = build_service()
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.enrich_projected_status", AsyncMock(side_effect=lambda x: x)):
        with pytest.raises(KeyError, match="test case not found"):
            asyncio_run(service.update_test_case("TC-MISSING", {"title": "New"}))


# ══════════════════════════════════════════════
#  Tests: assign_owners
# ══════════════════════════════════════════════

def test_assign_owners_sets_fields():
    service = build_service()
    _make_case("TC-001", owner_id="old-owner")
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.enrich_projected_status", AsyncMock(side_effect=lambda x: x)):
        result = asyncio_run(service.assign_owners("TC-001", owner_id="u-new"))
    assert result["owner_id"] == "u-new"


def test_assign_owners_no_targets_raises():
    service = build_service()
    with pytest.raises(ValueError, match="at least one owner"):
        asyncio_run(service.assign_owners("TC-001"))


def test_assign_owners_not_found():
    service = build_service()
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc):
        with pytest.raises(KeyError, match="test case not found"):
            asyncio_run(service.assign_owners("TC-MISSING", owner_id="u-1"))


# ══════════════════════════════════════════════
#  Tests: move_to_requirement
# ══════════════════════════════════════════════

def test_move_to_requirement_changes_ref():
    service = build_service()
    _make_case("TC-001", ref_req_id="TR-OLD")
    _FakeRequirementDoc.store["TR-NEW"] = _FakeRequirementDoc(req_id="TR-NEW", title="New Req", is_deleted=False)
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch(f"{SERVICE}.enrich_projected_status", AsyncMock(side_effect=lambda x: x)):
        result = asyncio_run(service.move_to_requirement("TC-001", "TR-NEW"))
    assert result["ref_req_id"] == "TR-NEW"


def test_move_to_requirement_same_target_raises():
    service = build_service()
    _make_case("TC-001", ref_req_id="TR-SAME")
    _FakeRequirementDoc.store["TR-SAME"] = _FakeRequirementDoc(req_id="TR-SAME", is_deleted=False)
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.TestRequirementDoc", _FakeRequirementDoc):
        with pytest.raises(ValueError, match="already linked"):
            asyncio_run(service.move_to_requirement("TC-001", "TR-SAME"))


def test_move_to_requirement_target_not_found():
    service = build_service()
    _make_case("TC-001", ref_req_id="TR-OLD")
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.TestRequirementDoc", _FakeRequirementDoc):
        with pytest.raises(KeyError, match="target requirement not found"):
            asyncio_run(service.move_to_requirement("TC-001", "TR-MISSING"))


def test_move_to_requirement_case_not_found():
    service = build_service()
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc):
        with pytest.raises(KeyError, match="test case not found"):
            asyncio_run(service.move_to_requirement("TC-MISSING", "TR-001"))


# ══════════════════════════════════════════════
#  Tests: delete_test_case
# ══════════════════════════════════════════════

def test_delete_test_case_soft_deletes():
    service = build_service()
    _make_case("TC-001", title="To Delete")
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.workflow_aware_soft_delete", AsyncMock()):
        asyncio_run(service.delete_test_case("TC-001"))


def test_delete_test_case_not_found():
    service = build_service()
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc):
        with pytest.raises(KeyError, match="test case not found"):
            asyncio_run(service.delete_test_case("TC-MISSING"))


# ══════════════════════════════════════════════
#  Tests: get_test_case
# ══════════════════════════════════════════════

def test_get_test_case_not_found():
    service = build_service()
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.enrich_projected_status", AsyncMock(side_effect=lambda x: x)):
        with pytest.raises(KeyError, match="test case not found"):
            asyncio_run(service.get_test_case("TC-MISSING"))


# ══════════════════════════════════════════════
#  Tests: link_automation_case
# ══════════════════════════════════════════════

def test_link_automation_case_case_not_found():
    service = build_service()
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutomationDoc):
        with pytest.raises(KeyError, match="test case not found"):
            asyncio_run(service.link_automation_case("TC-MISSING", "ATC-001"))


# ══════════════════════════════════════════════
#  Tests: list_test_cases
# ══════════════════════════════════════════════

def test_list_test_cases_returns_empty_when_none():
    service = build_service()
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE}.load_workflow_states_for_entities", AsyncMock(return_value={})):
        result = asyncio_run(service.list_test_cases())
    assert result == []


# ══════════════════════════════════════════════
#  Tests: _generate_case_id
# ══════════════════════════════════════════════

def test_generate_case_id_format():
    service = build_service()
    with patch(f"{SERVICE}.SequenceIdService") as mock_seq:
        mock_seq.return_value.next = AsyncMock(return_value=42)
        case_id = asyncio_run(service._generate_case_id())
    assert case_id.startswith("TC-")
    assert case_id.endswith("-00042")
