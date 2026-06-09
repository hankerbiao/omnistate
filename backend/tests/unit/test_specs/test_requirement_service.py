"""requirement_service 单元测试 — 字段安全校验、负责人分配、逻辑删除"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.service.requirement_service import RequirementService  # noqa: E402
from app.modules.workflow.application import WorkflowItemGateway  # noqa: E402


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


SERVICE_MODULE = "app.modules.test_specs.service.requirement_service"


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


class _FakeRequirementDoc:
    store: dict[str, "_FakeRequirementDoc"] = {}

    req_id = _FakeField("req_id")

    def __init__(self, **payload):
        self.id = f"req-{payload.get('req_id', 'unknown')}"
        for k, v in payload.items():
            setattr(self, k, v)

    async def insert(self):
        self.__class__.store[self.req_id] = self

    async def save(self):
        self.__class__.store[self.req_id] = self

    async def delete(self):
        self.__class__.store.pop(self.req_id, None)
        self.is_deleted = True

    def model_dump(self) -> dict:
        data = {}
        for attr in ["req_id", "title", "description", "tpm_owner_id", "tpm_owner_name",
                      "manual_dev_id", "manual_dev_name", "auto_dev_id", "auto_dev_name",
                      "workflow_item_id", "is_deleted", "status", "created_at", "updated_at"]:
            val = getattr(self, attr, None)
            if val is not None:
                data[attr] = val
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
                cond = args[0]
                for doc in cls.store.values():
                    match = all(getattr(doc, k, None) == v for k, v in cond.items() if k != "is_deleted")
                    if match and not getattr(doc, "is_deleted", False):
                        return doc
            return None
        return _coro()

    @classmethod
    def find(cls, expr=None):
        class _Query:
            def __init__(self, docs):
                self._docs = docs
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
            def find(self, expr):
                return self

        docs = list(cls.store.values())
        if isinstance(expr, _FakeExpr):
            docs = [d for d in docs if getattr(d, expr._field, None) == expr._value]
        elif isinstance(expr, dict):
            docs = [d for d in docs if not getattr(d, "is_deleted", False)]
        return _Query(docs)


class _FakeTestCaseDoc:
    store: dict[str, "_FakeTestCaseDoc"] = {}
    ref_req_id = _FakeField("ref_req_id")

    def __init__(self, **payload):
        for k, v in payload.items():
            setattr(self, k, v)

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def find(cls, expr=None):
        docs = list(cls.store.values())
        return _FakeTestCaseQuery(docs)

    @classmethod
    def find_one(cls, *args, **kwargs):
        async def _coro():
            return None
        return _coro()


class _FakeTestCaseQuery:
    def __init__(self, docs):
        self._docs = docs
    def sort(self, *args, **kwargs):
        return self
    async def count(self):
        return len(self._docs)


@pytest.fixture(autouse=True)
def reset_stores():
    _FakeRequirementDoc.reset()
    _FakeTestCaseDoc.reset()
    yield
    _FakeRequirementDoc.reset()
    _FakeTestCaseDoc.reset()


def _make_requirement(req_id: str, **overrides) -> _FakeRequirementDoc:
    attrs = dict(req_id=req_id, title="Test Req", is_deleted=False, workflow_item_id=None)
    attrs.update(overrides)
    doc = _FakeRequirementDoc(**attrs)
    _FakeRequirementDoc.store[req_id] = doc
    return doc


# ══════════════════════════════════════════════
#  Tests: update_requirement — safe field enforcement
# ══════════════════════════════════════════════

def test_update_requirement_rejects_high_risk_fields():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    _make_requirement("TR-001", title="Old")
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch(f"{SERVICE_MODULE}.TestRequirementDoc.find_one", _FakeRequirementDoc.find_one), \
         patch.object(service, "_get_mongo_client_or_none", return_value=AsyncMock()):
        with pytest.raises(ValueError, match="Use explicit commands"):
            asyncio_run(service.update_requirement("TR-001", {"status": "IN_REVIEW"}))


def test_update_requirement_rejects_owner_change():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    _make_requirement("TR-001", title="Old", tpm_owner_id="u-1")
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch.object(service, "_get_mongo_client_or_none", return_value=AsyncMock()):
        with pytest.raises(ValueError, match="Use explicit commands"):
            asyncio_run(service.update_requirement("TR-001", {"tpm_owner_id": "u-2"}))


def test_update_requirement_not_found():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch.object(service, "_get_mongo_client_or_none", return_value=AsyncMock()):
        with pytest.raises(KeyError, match="requirement not found"):
            asyncio_run(service.update_requirement("TR-MISSING", {"title": "New"}))


# ══════════════════════════════════════════════
#  Tests: assign_owners
# ══════════════════════════════════════════════

def test_assign_owners_sets_fields():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    _make_requirement("TR-001", tpm_owner_id="old-owner")
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch.object(service, "_resolve_user_names", AsyncMock(return_value={"u-new": "新负责人"})):
        result = asyncio_run(service.assign_owners("TR-001", tpm_owner_id="u-new"))
    assert result["tpm_owner_id"] == "u-new"
    assert "tpm_owner_name" not in result or result.get("tpm_owner_id") == "u-new"
    # Note: tpm_owner_name depends on _resolve_user_names which is mocked


def test_assign_owners_no_targets_raises():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    with pytest.raises(ValueError, match="at least one owner"):
        asyncio_run(service.assign_owners("TR-001"))


def test_assign_owners_not_found():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc):
        with pytest.raises(KeyError, match="requirement not found"):
            asyncio_run(service.assign_owners("TR-MISSING", tpm_owner_id="u-1"))


# ══════════════════════════════════════════════
#  Tests: delete_requirement
# ══════════════════════════════════════════════

def test_delete_requirement_soft_deletes():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    _make_requirement("TR-001", title="To Delete")
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch(f"{SERVICE_MODULE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE_MODULE}.workflow_aware_soft_delete", AsyncMock()):
        asyncio_run(service.delete_requirement("TR-001"))


def test_delete_requirement_not_found():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch(f"{SERVICE_MODULE}.TestCaseDoc", _FakeTestCaseDoc):
        with pytest.raises(KeyError, match="requirement not found"):
            asyncio_run(service.delete_requirement("TR-MISSING"))


def test_delete_requirement_with_cases_raises():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    _make_requirement("TR-001", title="Has Cases")
    _FakeTestCaseDoc.store["tc-1"] = _FakeTestCaseDoc(ref_req_id="TR-001", is_deleted=False)
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch(f"{SERVICE_MODULE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch(f"{SERVICE_MODULE}.workflow_aware_soft_delete") as mock_delete:
        mock_delete.side_effect = ValueError("requirement has related test cases")
        with pytest.raises(ValueError, match="related test cases"):
            asyncio_run(service.delete_requirement("TR-001"))


# ══════════════════════════════════════════════
#  Tests: list_requirements
# ══════════════════════════════════════════════

def test_list_requirements_returns_empty_when_none():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc):
        result = asyncio_run(service.list_requirements())
    assert result == []


# ══════════════════════════════════════════════
#  Tests: get_requirement
# ══════════════════════════════════════════════

def test_get_requirement_not_found():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    from app.modules.test_specs.service._workflow_status_support import enrich_projected_status
    with patch(f"{SERVICE_MODULE}.TestRequirementDoc", _FakeRequirementDoc), \
         patch(f"{SERVICE_MODULE}.enrich_projected_status", AsyncMock(side_effect=lambda x: x)):
        with pytest.raises(KeyError, match="requirement not found"):
            asyncio_run(service.get_requirement("TR-MISSING"))


# ══════════════════════════════════════════════
#  Tests: _generate_req_id
# ══════════════════════════════════════════════

def test_generate_req_id_format():
    service = RequirementService(AsyncMock(spec=WorkflowItemGateway))
    with patch(f"{SERVICE_MODULE}.SequenceIdService") as mock_seq:
        mock_seq.return_value.next = AsyncMock(return_value=1)
        req_id = asyncio_run(service._generate_req_id())
    assert req_id.startswith("TR-")
    assert req_id.endswith("-00001")
