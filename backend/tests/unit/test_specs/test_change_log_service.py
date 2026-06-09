"""change_log_service 单元测试 — 变更记录追加与查询"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.service.change_log_service import TestCaseChangeLogService  # noqa: E402


# ══════════════════════════════════════════════
#  Fake Documents
# ══════════════════════════════════════════════

class _FakeField:
    def __init__(self, name):
        self._name = name
    def __eq__(self, other):
        return _FakeExpr(self._name, other)
    def __neg__(self):
        return _FakeExpr(self._name, -1)


class _FakeExpr:
    def __init__(self, field, value):
        self._field = field
        self._value = value


class _FakeChangeLogDoc:
    store: dict[str, "_FakeChangeLogDoc"] = {}
    _id_counter = 0

    case_id = _FakeField("case_id")
    revision_no = _FakeField("revision_no")
    created_at = _FakeField("created_at")

    def __init__(self, **payload):
        type(self)._id_counter += 1
        self.id = f"log-{type(self)._id_counter:04d}"
        for k, v in payload.items():
            setattr(self, k, v)

    async def insert(self) -> None:
        self.__class__.store[self.id] = self

    @classmethod
    def reset(cls):
        cls.store = {}
        cls._id_counter = 0

    @classmethod
    def find(cls, expr=None):
        docs = list(cls.store.values())
        if isinstance(expr, _FakeExpr):
            docs = [d for d in docs if getattr(d, expr._field, None) == expr._value]

        class _Query:
            def __init__(self, docs):
                self._docs = docs
                self._skip = 0
                self._limit = 20

            def sort(self, *args, **kwargs):
                return self

            def skip(self, n):
                self._skip = n
                return self

            def limit(self, n):
                self._limit = n
                return self

            async def count(self):
                return len(self._docs)

            async def to_list(self):
                return self._docs[self._skip:self._skip + self._limit]

        return _Query(docs)


class _FakeUserDoc:
    store: dict[str, "_FakeUserDoc"] = {}

    def __init__(self, **payload):
        for k, v in payload.items():
            setattr(self, k, v)

    @classmethod
    def find(cls, query=None):
        class _Query:
            async def to_list(self):
                if isinstance(query, dict) and "$in" in query.get("user_id", {}):
                    ids = query["user_id"]["$in"]
                    return [u for u in cls.store.values() if u.user_id in ids]
                return list(cls.store.values())
        return _Query()

    @classmethod
    def reset(cls):
        cls.store = {}


@pytest.fixture(autouse=True)
def reset_stores():
    _FakeChangeLogDoc.reset()
    _FakeUserDoc.reset()
    yield
    _FakeChangeLogDoc.reset()
    _FakeUserDoc.reset()


SERVICE_MODULE = "app.modules.test_specs.service.change_log_service"


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


# ══════════════════════════════════════════════
#  Tests: get_snapshot
# ══════════════════════════════════════════════

def test_get_snapshot_extracts_tracked_fields():
    service = TestCaseChangeLogService()
    case_dict = {
        "title": "Test Case",
        "priority": "P1",
        "status": "DRAFT",
        "steps": [{"step_id": "s1"}],
        "custom_field": "ignored",
    }
    snapshot = asyncio_run(service.get_snapshot(case_dict))
    assert snapshot.get("title") == "Test Case"
    assert snapshot.get("priority") == "P1"
    assert "custom_field" not in snapshot


# ══════════════════════════════════════════════
#  Tests: append
# ══════════════════════════════════════════════

def test_append_creates_log_entry():
    service = TestCaseChangeLogService()
    old = {"title": "Old"}
    new = {"title": "New"}
    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        asyncio_run(service.append("TC-001", "u-1", "UPDATE", old, new))
    assert len(_FakeChangeLogDoc.store) == 1


def test_append_no_changes_skips():
    """无变更且无 remark 时应跳过"""
    service = TestCaseChangeLogService()
    old = {"title": "Same"}
    new = {"title": "Same"}
    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        asyncio_run(service.append("TC-001", "u-1", "UPDATE", old, new))
    assert len(_FakeChangeLogDoc.store) == 0


def test_append_no_changes_but_has_remark():
    """无变更但有 remark 时应仍写入"""
    service = TestCaseChangeLogService()
    old = {"title": "Same"}
    new = {"title": "Same"}
    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        asyncio_run(service.append("TC-001", "u-1", "UPDATE", old, new, remark="手工修正"))
    assert len(_FakeChangeLogDoc.store) == 1


def test_append_delete_action_always_writes():
    """DELETE 操作即使没有变更也应写入"""
    service = TestCaseChangeLogService()
    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        asyncio_run(service.append("TC-001", "u-1", "DELETE", None, {}))
    assert len(_FakeChangeLogDoc.store) == 1


def test_append_extra_changes_appended():
    service = TestCaseChangeLogService()
    old = {"title": "Old"}
    new = {"title": "New"}
    extra = [{"field": "custom", "old_value": "a", "new_value": "b"}]
    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        asyncio_run(service.append("TC-001", "u-1", "UPDATE", old, new, extra_changes=extra))
    assert len(_FakeChangeLogDoc.store) == 1


def test_append_next_revision_no():
    """验证 revision_no 递增"""
    service = TestCaseChangeLogService()
    old = {"title": "v1"}
    new = {"title": "v2"}
    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        asyncio_run(service.append("TC-001", "u-1", "UPDATE", old, new))
    log = list(_FakeChangeLogDoc.store.values())[0]
    assert log.revision_no == 1


# ══════════════════════════════════════════════
#  Tests: list_logs
# ══════════════════════════════════════════════

def test_list_logs_empty():
    service = TestCaseChangeLogService()
    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        result = asyncio_run(service.list_logs("TC-001"))
    assert result["total"] == 0
    assert result["items"] == []


def test_list_logs_with_entries():
    service = TestCaseChangeLogService()
    _FakeChangeLogDoc.store["l1"] = _FakeChangeLogDoc(
        case_id="TC-001", revision_no=1, action="UPDATE",
        operator_id="u-1", changes=[], remark=None,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    _FakeUserDoc.store["u-1"] = _FakeUserDoc(user_id="u-1", username="张三")

    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        result = asyncio_run(service.list_logs("TC-001"))
    assert result["total"] == 1
    assert result["items"][0]["operator_name"] == "张三"
    assert result["items"][0]["action"] == "UPDATE"


def test_list_logs_filters_by_case_id():
    service = TestCaseChangeLogService()
    _FakeChangeLogDoc.store["l1"] = _FakeChangeLogDoc(
        case_id="TC-001", revision_no=1, action="CREATE",
        operator_id="u-1", changes=[], remark=None,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    _FakeChangeLogDoc.store["l2"] = _FakeChangeLogDoc(
        case_id="TC-002", revision_no=1, action="CREATE",
        operator_id="u-2", changes=[], remark=None,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    with patch(f"{SERVICE_MODULE}.TestCaseChangeLogDoc", _FakeChangeLogDoc), \
         patch(f"{SERVICE_MODULE}.UserDoc", _FakeUserDoc):
        result = asyncio_run(service.list_logs("TC-001"))
    assert result["total"] == 1
