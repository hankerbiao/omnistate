"""catalog_service 单元测试 — 目录路径、lab 验证、面包屑、树构建"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.domain.exceptions import LabNotFoundError  # noqa: E402
from app.modules.test_specs.service.catalog_service import CatalogService  # noqa: E402


# ══════════════════════════════════════════════
#  Fake Documents
# ══════════════════════════════════════════════

class _FakeLabDoc:
    store: dict[str, "_FakeLabDoc"] = {}
    _id_counter = 0

    def __init__(self, **payload):
        type(self)._id_counter += 1
        self.id = f"lab-{type(self)._id_counter:04d}"
        for k, v in payload.items():
            setattr(self, k, v)

    @classmethod
    def find_one(cls, query=None, *args, **kwargs):
        async def _coro():
            if isinstance(query, dict) and "lab_id" in query:
                return cls.store.get(query["lab_id"])
            return None
        return _coro()

    @classmethod
    def reset(cls):
        cls.store = {}
        cls._id_counter = 0


class _FakeCatalogSegmentDoc:
    store: dict[str, "_FakeCatalogSegmentDoc"] = {}
    _id_counter = 0

    def __init__(self, **payload):
        type(self)._id_counter += 1
        self.id = f"seg-{type(self)._id_counter:04d}"
        for k, v in payload.items():
            setattr(self, k, v)

    async def insert(self) -> None:
        key = f"{self.lab_id}|{self.parent_path}|{self.segment_name}"
        self.__class__.store[key] = self

    async def save(self) -> None:
        pass

    async def delete(self) -> None:
        key = f"{self.lab_id}|{self.parent_path}|{self.segment_name}"
        self.__class__.store.pop(key, None)

    @classmethod
    def find_one(cls, query=None, *args, **kwargs):
        async def _coro():
            if isinstance(query, dict):
                key = f"{query.get('lab_id')}|{query.get('parent_path')}|{query.get('segment_name')}"
                return cls.store.get(key)
            return None
        return _coro()

    @classmethod
    def find(cls, query=None):
        class _Query:
            def sort(self, *args, **kwargs):
                return self
            async def to_list(self):
                if isinstance(query, dict):
                    lab_id = query.get("lab_id")
                    parent = query.get("parent_path")
                    return [
                        doc for doc in cls.store.values()
                        if doc.lab_id == lab_id and doc.parent_path == parent and doc.usage_count > 0
                    ]
                return list(cls.store.values())
        return _Query()

    @classmethod
    def reset(cls):
        cls.store = {}
        cls._id_counter = 0


class _FakeTestCaseDoc:
    store: dict[str, "_FakeTestCaseDoc"] = {}

    def __init__(self, **payload):
        self.id = f"case-{payload.get('case_id', 'unknown')}"
        for k, v in payload.items():
            setattr(self, k, v)

    @classmethod
    def find(cls, query=None):
        class _Query:
            async def to_list(self):
                if isinstance(query, dict):
                    lab_id = query.get("lab_id")
                    return [
                        doc for doc in cls.store.values()
                        if getattr(doc, "lab_id", None) == lab_id and not getattr(doc, "is_deleted", True)
                    ]
                return list(cls.store.values())
        return _Query()

    @classmethod
    def reset(cls):
        cls.store = {}


@pytest.fixture(autouse=True)
def reset_stores():
    _FakeLabDoc.reset()
    _FakeCatalogSegmentDoc.reset()
    _FakeTestCaseDoc.reset()
    yield
    _FakeLabDoc.reset()
    _FakeCatalogSegmentDoc.reset()
    _FakeTestCaseDoc.reset()


def _add_lab(lab_id: str, name: str, is_active: bool = True) -> _FakeLabDoc:
    doc = _FakeLabDoc(lab_id=lab_id, name=name, is_active=is_active)
    _FakeLabDoc.store[lab_id] = doc
    return doc


SERVICE = "app.modules.test_specs.service.catalog_service"


# ══════════════════════════════════════════════
#  Tests: static methods
# ══════════════════════════════════════════════

def test_normalize_path_segments():
    result = CatalogService.normalize_path_segments([" BIOS ", "Release_Check"])
    assert result == ["bios", "release_check"]


def test_build_path_key():
    result = CatalogService.build_path_key(["bios", "release_check"])
    assert result == "bios/release_check"


def test_match_catalog_prefix_filter_no_prefix():
    result = CatalogService.match_catalog_prefix_filter("LAB-BIOS", [])
    assert result == {"lab_id": "LAB-BIOS"}


def test_match_catalog_prefix_filter_with_prefix():
    result = CatalogService.match_catalog_prefix_filter("LAB-BIOS", ["bios", "memory"])
    assert "lab_id" in result
    assert "catalog_path_key" in result


# ══════════════════════════════════════════════
#  Tests: ensure_active_lab
# ══════════════════════════════════════════════

def test_ensure_active_lab_found_and_active():
    _add_lab("LAB-BIOS", "BIOS Lab", is_active=True)
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        lab = asyncio_run(service.ensure_active_lab("LAB-BIOS"))
    assert lab.lab_id == "LAB-BIOS"


def test_ensure_active_lab_not_found():
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        with pytest.raises(LabNotFoundError):
            asyncio_run(service.ensure_active_lab("LAB-MISSING"))


def test_ensure_active_lab_inactive():
    _add_lab("LAB-BIOS", "BIOS Lab", is_active=False)
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        with pytest.raises(ValueError, match="未启用"):
            asyncio_run(service.ensure_active_lab("LAB-BIOS"))


# ══════════════════════════════════════════════
#  Tests: prepare_catalog_fields
# ══════════════════════════════════════════════

def test_prepare_catalog_fields():
    _add_lab("LAB-BIOS", "BIOS Lab")
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        result = asyncio_run(service.prepare_catalog_fields("LAB-BIOS", [" BIOS ", "Memory"]))
    assert result["lab_id"] == "LAB-BIOS"
    assert result["catalog_path"] == ["bios", "memory"]
    assert result["catalog_path_key"] == "bios/memory"


# ══════════════════════════════════════════════
#  Tests: register_path & adjust_path_on_update
# ══════════════════════════════════════════════

def test_register_path_creates_segments():
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc), \
         patch(f"{SERVICE}.TestCatalogSegmentDoc", _FakeCatalogSegmentDoc):
        asyncio_run(service.register_path("LAB-BIOS", ["bios", "memory"], delta=1))
    assert len(_FakeCatalogSegmentDoc.store) == 2


def test_register_path_noop_when_delta_zero():
    service = CatalogService()
    with patch(f"{SERVICE}.TestCatalogSegmentDoc", _FakeCatalogSegmentDoc):
        asyncio_run(service.register_path("LAB-BIOS", ["bios"], delta=0))
    assert len(_FakeCatalogSegmentDoc.store) == 0


def test_adjust_path_on_update_no_change():
    service = CatalogService()
    with patch(f"{SERVICE}.TestCatalogSegmentDoc", _FakeCatalogSegmentDoc):
        # Same lab + path = no-op
        asyncio_run(service.adjust_path_on_update("LAB-BIOS", ["bios"], "LAB-BIOS", ["bios"]))
    assert len(_FakeCatalogSegmentDoc.store) == 0


def test_adjust_path_on_update_decrements_old():
    service = CatalogService()
    with patch(f"{SERVICE}.TestCatalogSegmentDoc", _FakeCatalogSegmentDoc):
        asyncio_run(service.register_path("LAB-BIOS", ["bios"], delta=1))
        # adjust_path_on_update calls register_path(old, delta=-1) then register_path(new, delta=1)
        asyncio_run(service.adjust_path_on_update("LAB-BIOS", ["bios"], "LAB-BMC", ["bmc"]))
    # Old path segment may be deleted (usage_count goes to 0)
    # New path should exist
    bmc_key = "LAB-BMC|[]|bmc"
    assert bmc_key in _FakeCatalogSegmentDoc.store


# ══════════════════════════════════════════════
#  Tests: build_breadcrumb
# ══════════════════════════════════════════════

def test_build_breadcrumb():
    _add_lab("LAB-BIOS", "BIOS Lab")
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        result = asyncio_run(service.build_breadcrumb("LAB-BIOS", ["bios", "memory"]))
    assert result == "BIOS Lab / bios / memory"


def test_build_breadcrumb_with_case_title():
    _add_lab("LAB-BIOS", "BIOS Lab")
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        result = asyncio_run(service.build_breadcrumb("LAB-BIOS", ["bios"], case_title="Test"))
    assert result == "BIOS Lab / bios / Test"


def test_build_breadcrumb_lab_not_found():
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        result = asyncio_run(service.build_breadcrumb("LAB-MISSING", ["p1"]))
    assert "LAB-MISSING" in result


# ══════════════════════════════════════════════
#  Tests: enrich_case_dict
# ══════════════════════════════════════════════

def test_enrich_case_dict_adds_lab_name():
    _add_lab("LAB-BIOS", "BIOS Lab")
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        result = asyncio_run(service.enrich_case_dict({"lab_id": "LAB-BIOS", "catalog_path": ["bios"]}))
    assert result["lab_name"] == "BIOS Lab"
    assert result["catalog_breadcrumb"] is not None


def test_enrich_case_dict_no_lab():
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        result = asyncio_run(service.enrich_case_dict({}))
    assert result["lab_name"] is None
    assert result["catalog_breadcrumb"] is None


# ══════════════════════════════════════════════
#  Tests: get_suggestions
# ══════════════════════════════════════════════

def test_get_suggestions_returns_segment_names():
    _add_lab("LAB-BIOS", "BIOS Lab")
    _FakeCatalogSegmentDoc.store["k1"] = _FakeCatalogSegmentDoc(
        lab_id="LAB-BIOS", parent_path=[], segment_name="bios", usage_count=3
    )
    _FakeCatalogSegmentDoc.store["k2"] = _FakeCatalogSegmentDoc(
        lab_id="LAB-BIOS", parent_path=[], segment_name="memory", usage_count=1
    )
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc), \
         patch(f"{SERVICE}.TestCatalogSegmentDoc", _FakeCatalogSegmentDoc):
        suggestions = asyncio_run(service.get_suggestions("LAB-BIOS"))
    assert "bios" in suggestions
    assert "memory" in suggestions


# ══════════════════════════════════════════════
#  Tests: build_tree
# ══════════════════════════════════════════════

def test_build_tree_returns_tree_structure():
    _add_lab("LAB-BIOS", "BIOS Lab")
    _FakeCatalogSegmentDoc.store["k1"] = _FakeCatalogSegmentDoc(
        lab_id="LAB-BIOS", parent_path=[], segment_name="bios", usage_count=1
    )
    _FakeTestCaseDoc.store["c1"] = _FakeTestCaseDoc(
        case_id="TC-001", lab_id="LAB-BIOS", catalog_path=["bios"], is_deleted=False
    )
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc), \
         patch(f"{SERVICE}.TestCatalogSegmentDoc", _FakeCatalogSegmentDoc), \
         patch(f"{SERVICE}.TestCaseDoc", _FakeTestCaseDoc):
        result = asyncio_run(service.build_tree("LAB-BIOS"))
    assert result["lab_id"] == "LAB-BIOS"
    assert len(result["tree"]["children"]) > 0
    assert result["tree"]["children"][0]["name"] == "bios"
    assert result["tree"]["children"][0]["case_count"] == 1


def test_build_tree_lab_not_found():
    service = CatalogService()
    with patch(f"{SERVICE}.TestLabDoc", _FakeLabDoc):
        with pytest.raises(LabNotFoundError):
            asyncio_run(service.build_tree("LAB-MISSING"))


def test_serialize_tree_node_sorts_children():
    """验证树节点序列化按名称排序"""
    from app.modules.test_specs.service.catalog_service import _serialize_tree_node
    node = {
        "name": "",
        "path": [],
        "case_count": 0,
        "children": {
            "zzz": {"name": "zzz", "path": ["zzz"], "case_count": 0, "children": {}},
            "aaa": {"name": "aaa", "path": ["aaa"], "case_count": 0, "children": {}},
        },
    }
    result = _serialize_tree_node(node)
    assert result["children"][0]["name"] == "aaa"
    assert result["children"][1]["name"] == "zzz"


# ══════════════════════════════════════════════
#  Helper
# ══════════════════════════════════════════════

def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)
