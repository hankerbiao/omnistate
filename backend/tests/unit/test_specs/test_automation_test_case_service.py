"""automation_test_case_service 单元测试 — CRUD、元数据上报、载荷校验"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.service.automation_test_case_service import (  # noqa: E402
    AutomationTestCaseService,
)


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


SERVICE = "app.modules.test_specs.service.automation_test_case_service"


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


class _FakeAutoDoc:
    store: dict[str, "_FakeAutoDoc"] = {}
    auto_case_id = _FakeField("auto_case_id")
    framework = _FakeField("framework")
    automation_type = _FakeField("automation_type")
    status = _FakeField("status")
    _id_counter = 0

    def __init__(self, **payload):
        type(self)._id_counter += 1
        self.id = f"auto-{type(self)._id_counter:04d}"
        for k, v in payload.items():
            setattr(self, k, v)

    async def insert(self) -> None:
        self.__class__.store[self.auto_case_id] = self

    async def save(self) -> None:
        self.__class__.store[self.auto_case_id] = self

    def model_dump(self) -> dict:
        data = {}
        for attr in ["auto_case_id", "name", "linked_manual_case_id", "framework",
                      "automation_type", "status", "description", "is_deleted",
                      "script_ref", "config_path", "script_name", "script_path",
                      "code_snapshot", "param_spec", "tags", "report_meta",
                      "created_at", "updated_at"]:
            val = getattr(self, attr, None)
            if val is not None:
                data[attr] = val
        data["id"] = self.id
        return data

    @classmethod
    def reset(cls):
        cls.store = {}
        cls._id_counter = 0

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
            def find(self, _e):
                if isinstance(_e, _FakeExpr):
                    self._docs = [d for d in self._docs if getattr(d, _e._field, None) == _e._value]
                return self
            def sort(self, *args, **kwargs):
                return self
            def skip(self, n):
                return self
            def limit(self, n):
                return self
            async def to_list(self):
                return self._docs
        docs = [d for d in cls.store.values() if not getattr(d, "is_deleted", False)]
        if isinstance(expr, _FakeExpr):
            docs = [d for d in docs if getattr(d, expr._field, None) == expr._value]
        return _Query(docs)


class _FakeTestCaseDoc:
    store: dict[str, "_FakeTestCaseDoc"] = {}

    def __init__(self, **payload):
        for k, v in payload.items():
            setattr(self, k, v)

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def find_one(cls, *args, **kwargs):
        async def _coro():
            if args and isinstance(args[0], dict):
                case_id = args[0].get("case_id")
                for doc in cls.store.values():
                    if getattr(doc, "case_id", None) == case_id and not getattr(doc, "is_deleted", False):
                        return doc
            return None
        return _coro()


@pytest.fixture(autouse=True)
def reset_stores():
    _FakeAutoDoc.reset()
    _FakeTestCaseDoc.reset()
    yield
    _FakeAutoDoc.reset()
    _FakeTestCaseDoc.reset()


def _make_auto(auto_case_id: str, **overrides) -> _FakeAutoDoc:
    attrs = dict(auto_case_id=auto_case_id, name=auto_case_id, is_deleted=False, status="ACTIVE")
    attrs.update(overrides)
    doc = _FakeAutoDoc(**attrs)
    _FakeAutoDoc.store[auto_case_id] = doc
    return doc


# ══════════════════════════════════════════════
#  Tests: create / upsert
# ══════════════════════════════════════════════

def test_create_new_auto_case():
    service = AutomationTestCaseService()
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc), \
         patch(f"{SERVICE}.SequenceIdService") as mock_seq:
        mock_seq.return_value.next = AsyncMock(return_value=1)
        result = asyncio_run(service.create_automation_test_case({
            "name": "New Auto Case",
            "framework": "pytest",
        }))
    assert result["name"] == "New Auto Case"
    assert result["auto_case_id"].startswith("ATC-")


def test_create_existing_updates():
    """已存在的 auto_case_id 应更新而非新建"""
    _make_auto("ATC-001", name="Old Name")
    service = AutomationTestCaseService()
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc):
        result = asyncio_run(service.create_automation_test_case({
            "auto_case_id": "ATC-001",
            "name": "Updated Name",
            "framework": "pytest",
        }))
    assert result["name"] == "Updated Name"


# ══════════════════════════════════════════════
#  Tests: get
# ══════════════════════════════════════════════

def test_get_auto_case_found():
    _make_auto("ATC-001", name="My Case")
    service = AutomationTestCaseService()
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc):
        result = asyncio_run(service.get_automation_test_case("ATC-001"))
    assert result["name"] == "My Case"


def test_get_auto_case_not_found():
    service = AutomationTestCaseService()
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc):
        with pytest.raises(KeyError, match="automation test case not found"):
            asyncio_run(service.get_automation_test_case("ATC-MISSING"))


def test_get_by_manual_case_id_found():
    _make_auto("ATC-001", linked_manual_case_id="TC-001")
    service = AutomationTestCaseService()
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc):
        result = asyncio_run(service.get_automation_test_case_by_manual_case_id("TC-001"))
    assert result["auto_case_id"] == "ATC-001"


def test_get_by_manual_case_id_not_found():
    service = AutomationTestCaseService()
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc):
        with pytest.raises(KeyError, match="automation test case not found"):
            asyncio_run(service.get_automation_test_case_by_manual_case_id("TC-MISSING"))


# ══════════════════════════════════════════════
#  Tests: list
# ══════════════════════════════════════════════

def test_list_auto_cases():
    _make_auto("ATC-001", framework="pytest")
    _make_auto("ATC-002", framework="playwright")
    service = AutomationTestCaseService()
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc):
        result = asyncio_run(service.list_automation_test_cases())
    assert len(result) == 2


def test_list_auto_cases_filters_by_framework():
    _make_auto("ATC-001", framework="pytest")
    _make_auto("ATC-002", framework="playwright")
    service = AutomationTestCaseService()
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc):
        result = asyncio_run(service.list_automation_test_cases(framework="pytest"))
    assert len(result) == 1
    assert result[0]["framework"] == "pytest"


# ══════════════════════════════════════════════
#  Tests: static methods — payload extraction
# ══════════════════════════════════════════════

def test_extract_report_payload_valid():
    cases, summary = AutomationTestCaseService._extract_report_payload({
        "cases": [{"linked_manual_case_id": "TC-001"}],
        "summary": {"total_cases": 1},
    })
    assert len(cases) == 1
    assert summary["total_cases"] == 1


def test_extract_report_payload_empty_raises():
    with pytest.raises(ValueError, match="cannot be empty"):
        AutomationTestCaseService._extract_report_payload({})


def test_extract_report_payload_empty_cases_raises():
    with pytest.raises(ValueError, match="must be a non-empty list"):
        AutomationTestCaseService._extract_report_payload({"cases": [], "summary": {}})


def test_extract_report_payload_mismatched_total_raises():
    with pytest.raises(ValueError, match="must match cases length"):
        AutomationTestCaseService._extract_report_payload({
            "cases": [{"linked_manual_case_id": "TC-001"}],
            "summary": {"total_cases": 999},
        })




# ══════════════════════════════════════════════
#  Tests: _build_report_doc_data
# ══════════════════════════════════════════════

def test_build_report_doc_data():
    result = AutomationTestCaseService._build_report_doc_data(
        "TC-001",
        {"framework": "pytest", "description": "Test"},
    )
    assert result["linked_manual_case_id"] == "TC-001"
    assert result["framework"] == "pytest"
    assert result["status"] == "ACTIVE"


def test_build_report_doc_data_framework_fallback():
    result = AutomationTestCaseService._build_report_doc_data("TC-001", {})
    assert result["framework"] == "reported"


# ══════════════════════════════════════════════
#  Tests: metadata report (report_automation_test_case_metadata)
# ══════════════════════════════════════════════

def test_report_metadata_new_case():
    service = AutomationTestCaseService()
    payload = {
        "cases": [{"linked_manual_case_id": "TC-001", "framework": "pytest"}],
        "summary": {"total_cases": 1},
    }
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc), \
         patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc), \
         patch.object(service, "_generate_auto_case_id", AsyncMock(return_value="ATC-NEW")):
        result = asyncio_run(service.report_automation_test_case_metadata(payload))
    assert result["total_cases"] == 1
    assert result["saved_count"] == 1
    assert "ATC-NEW" in _FakeAutoDoc.store


def test_report_metadata_updates_existing():
    _make_auto("ATC-001", linked_manual_case_id="TC-001", framework="old-fw")
    service = AutomationTestCaseService()
    payload = {
        "cases": [{"linked_manual_case_id": "TC-001", "framework": "new-fw"}],
        "summary": {"total_cases": 1},
    }
    with patch(f"{SERVICE}.AutomationTestCaseDoc", _FakeAutoDoc), \
         patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc):
        result = asyncio_run(service.report_automation_test_case_metadata(payload))
    assert result["total_cases"] == 1
    assert _FakeAutoDoc.store["ATC-001"].framework == "new-fw"


# ══════════════════════════════════════════════
#  Tests: _try_link_test_case
# ══════════════════════════════════════════════

def test_try_link_test_case_no_manual_id():
    service = AutomationTestCaseService()
    doc = _FakeAutoDoc(auto_case_id="ATC-001", linked_manual_case_id=None)
    result = asyncio_run(service._try_link_test_case(doc, {}))
    assert result["linked"] is False


def test_try_link_test_case_found():
    _FakeTestCaseDoc.store["TC-001"] = _FakeTestCaseDoc(case_id="TC-001", is_deleted=False)
    service = AutomationTestCaseService()
    doc = _FakeAutoDoc(auto_case_id="ATC-001", linked_manual_case_id="TC-001")
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc):
        result = asyncio_run(service._try_link_test_case(doc, {}))
    assert result["linked"] is True
    assert result["linked_case_id"] == "TC-001"


def test_try_link_test_case_not_found():
    service = AutomationTestCaseService()
    doc = _FakeAutoDoc(auto_case_id="ATC-001", linked_manual_case_id="TC-MISSING")
    with patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc):
        result = asyncio_run(service._try_link_test_case(doc, {}))
    assert result["linked"] is False
