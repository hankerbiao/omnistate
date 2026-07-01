"""TestCaseRepository 仓储层单元测试。

测试策略：
- 单元测试隔离模式：使用 unittest.mock.patch 替换 TestCaseDoc 的 Beanie 操作，
  不依赖真实 MongoDB/Beanie 运行环境。
- 验证每个方法的查询语义正确（参数透传、返回值映射）。
- 验证 get_mongo_client 在服务可用/不可用时行为正确。

与 service 层测试的分工：
- service 层测试 (_FakeTestCaseDoc) 验证业务逻辑组合
- 本文件验证 repository 层数据访问语义
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.repository.test_case_repository import (  # noqa: E402
    TestCaseRepository,
)


# ═══════════════════════════════════════════════════════════════════════
#  Helper: 快速构造 mock TestCaseDoc 对象
# ═══════════════════════════════════════════════════════════════════════

def _mock_doc(case_id: str = "TC-001", **overrides) -> MagicMock:
    doc = MagicMock()
    doc.case_id = case_id
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


# ═══════════════════════════════════════════════════════════════════════
#  find_active_by_case_id
# ═══════════════════════════════════════════════════════════════════════

async def test_find_active_returns_doc_when_exists():
    """未删除的用例存在时返回文档。"""
    repo = TestCaseRepository()
    mock_doc = _mock_doc("TC-001")

    with patch(
        "app.modules.test_specs.repository.test_case_repository.TestCaseDoc",
    ) as MockTC:
        MockTC.find_one = AsyncMock(return_value=mock_doc)

        result = await repo.find_active_by_case_id("TC-001")

    assert result is mock_doc
    # 验证 find_one 被调用时传了 case_id 表达式和 is_deleted 过滤条件
    MockTC.find_one.assert_awaited_once()
    args, kwargs = MockTC.find_one.call_args
    assert len(args) == 2
    # args[0] 是 Beanie 表达式 TestCaseDoc.case_id == "TC-001"
    # args[1] 是 dict {"is_deleted": False}


async def test_find_active_returns_none_when_not_found():
    """用例不存在时返回 None。"""
    repo = TestCaseRepository()
    with patch(
        "app.modules.test_specs.repository.test_case_repository.TestCaseDoc",
    ) as MockTC:
        MockTC.find_one = AsyncMock(return_value=None)

        result = await repo.find_active_by_case_id("TC-MISSING")
    assert result is None


async def test_find_active_returns_none_when_deleted():
    """已删除的用例返回 None（is_deleted 过滤生效）。"""
    repo = TestCaseRepository()
    with patch(
        "app.modules.test_specs.repository.test_case_repository.TestCaseDoc",
    ) as MockTC:
        MockTC.find_one = AsyncMock(return_value=None)

        result = await repo.find_active_by_case_id("TC-DELETED")
    assert result is None
    # 验证 find_one 包含 is_deleted 条件
    _, kwargs = MockTC.find_one.call_args
    # 第二个位置参数是 {"is_deleted": False}，不是传 kwargs
    args = MockTC.find_one.call_args[0]
    assert len(args) >= 2
    assert isinstance(args[1], dict)
    assert args[1].get("is_deleted") is False


# ═══════════════════════════════════════════════════════════════════════
#  find_by_case_id
# ═══════════════════════════════════════════════════════════════════════

async def test_find_by_case_id_returns_doc_regardless_of_deleted():
    """含已删除：find_by_case_id 无条件返回匹配文档。"""
    repo = TestCaseRepository()
    mock_doc = _mock_doc("TC-DELETED", is_deleted=True)

    with patch(
        "app.modules.test_specs.repository.test_case_repository.TestCaseDoc",
    ) as MockTC:
        MockTC.find_one = AsyncMock(return_value=mock_doc)

        result = await repo.find_by_case_id("TC-DELETED")
    assert result is mock_doc
    # 验证只传了 case_id 表达式，没有 is_deleted 条件
    MockTC.find_one.assert_awaited_once()
    args = MockTC.find_one.call_args[0]
    assert len(args) == 1  # 只有 Beanie 表达式，无 dict 过滤


async def test_find_by_case_id_returns_none_when_missing():
    """含已删除：用例 ID 不存在时返回 None。"""
    repo = TestCaseRepository()
    with patch(
        "app.modules.test_specs.repository.test_case_repository.TestCaseDoc",
    ) as MockTC:
        MockTC.find_one = AsyncMock(return_value=None)

        result = await repo.find_by_case_id("TC-NEVER-EXISTED")
    assert result is None


# ═══════════════════════════════════════════════════════════════════════
#  insert
# ═══════════════════════════════════════════════════════════════════════

async def test_insert_calls_doc_insert():
    """insert 委托给 doc.insert(session=None)。"""
    repo = TestCaseRepository()
    doc = _mock_doc("TC-NEW")
    doc.insert = AsyncMock()

    result = await repo.insert(doc)

    assert result is doc
    doc.insert.assert_awaited_once_with(session=None)


async def test_insert_passes_session():
    """insert 透传 session 参数。"""
    repo = TestCaseRepository()
    doc = _mock_doc("TC-NEW")
    doc.insert = AsyncMock()
    fake_session = MagicMock()

    await repo.insert(doc, session=fake_session)

    doc.insert.assert_awaited_once_with(session=fake_session)


# ═══════════════════════════════════════════════════════════════════════
#  save
# ═══════════════════════════════════════════════════════════════════════

async def test_save_calls_doc_save():
    """save 委托给 doc.save(session=None)。"""
    repo = TestCaseRepository()
    doc = _mock_doc("TC-EXISTING")
    doc.save = AsyncMock()

    result = await repo.save(doc)

    assert result is doc
    doc.save.assert_awaited_once_with(session=None)


async def test_save_passes_session():
    """save 透传 session 参数。"""
    repo = TestCaseRepository()
    doc = _mock_doc("TC-EXISTING")
    doc.save = AsyncMock()
    fake_session = MagicMock()

    await repo.save(doc, session=fake_session)

    doc.save.assert_awaited_once_with(session=fake_session)


# ═══════════════════════════════════════════════════════════════════════
#  count
# ═══════════════════════════════════════════════════════════════════════

async def test_count_delegates_to_find():
    """count 委托给 TestCaseDoc.find(filter).count()。"""
    repo = TestCaseRepository()
    fake_query = MagicMock()
    fake_query.count = AsyncMock(return_value=42)

    with patch(
        "app.modules.test_specs.repository.test_case_repository.TestCaseDoc",
    ) as MockTC:
        MockTC.find.return_value = fake_query

        result = await repo.count({"is_deleted": False})

    assert result == 42
    MockTC.find.assert_called_once_with({"is_deleted": False})
    fake_query.count.assert_awaited_once()


async def test_count_empty_filter():
    """空过滤条件时 count 语义正确。"""
    repo = TestCaseRepository()
    fake_query = MagicMock()
    fake_query.count = AsyncMock(return_value=0)

    with patch(
        "app.modules.test_specs.repository.test_case_repository.TestCaseDoc",
    ) as MockTC:
        MockTC.find.return_value = fake_query

        result = await repo.count({})
    assert result == 0


# ═══════════════════════════════════════════════════════════════════════
#  build_find_query
# ═══════════════════════════════════════════════════════════════════════

async def test_build_find_query_returns_beanie_query():
    """build_find_query 委托给 TestCaseDoc.find。"""
    repo = TestCaseRepository()
    fake_query = MagicMock()

    with patch(
        "app.modules.test_specs.repository.test_case_repository.TestCaseDoc",
    ) as MockTC:
        MockTC.find.return_value = fake_query

        result = repo.build_find_query({"status": "active"})

    assert result is fake_query
    MockTC.find.assert_called_once_with({"status": "active"})


# ═══════════════════════════════════════════════════════════════════════
#  get_mongo_client
# ═══════════════════════════════════════════════════════════════════════

async def test_get_mongo_client_returns_client_when_available():
    """MongoDB 客户端可用时返回客户端实例。"""
    repo = TestCaseRepository()
    fake_client = MagicMock()

    with patch(
        "app.modules.test_specs.repository.test_case_repository.get_mongo_client",
        return_value=fake_client,
    ):
        result = await repo.get_mongo_client()
    assert result is fake_client


async def test_get_mongo_client_returns_none_when_not_available():
    """MongoDB 客户端未初始化时返回 None（RuntimeError 吞掉）。"""
    repo = TestCaseRepository()
    with patch(
        "app.modules.test_specs.repository.test_case_repository.get_mongo_client",
        side_effect=RuntimeError("MongoDB not initialized"),
    ):
        result = await repo.get_mongo_client()
    assert result is None
