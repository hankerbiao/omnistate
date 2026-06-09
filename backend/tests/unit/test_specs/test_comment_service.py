"""测试用例评论模块单元测试 — schema + service"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.schemas.comment import (  # noqa: E402
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    UpdateCommentRequest,
)
from app.modules.test_specs.service.comment_service import TestCaseCommentService  # noqa: E402


# ══════════════════════════════════════════════
#  Fake Beanie Document
# ══════════════════════════════════════════════

class _FakeField:
    """模拟 Beanie Field 描述符，支持 == 和 - 运算生成查询表达式"""
    def __init__(self, name: str):
        self._name = name

    def __eq__(self, other):
        return _FakeExpr(self._name, other)

    def __neg__(self):
        """支持 -TestCaseCommentDoc.created_at 降序排序"""
        return _FakeExpr(self._name, -1)


class _FakeExpr:
    """模拟 Beanie 查询表达式"""
    def __init__(self, field: str, value):
        self._field = field
        self._value = value

    def __neg__(self):
        return _FakeExpr(self._field, -self._value)


class _FakeCommentDoc:
    """模拟 TestCaseCommentDoc，替代 Beanie Document"""
    _id_counter = 0
    store: dict[str, "_FakeCommentDoc"] = {}

    # Beanie 风格字段描述符
    case_id = _FakeField("case_id")
    created_at = _FakeField("created_at")

    def __init__(self, **payload):
        type(self)._id_counter += 1
        self.id = f"comment-{type(self)._id_counter:04d}"
        self.is_deleted = False
        for key, value in payload.items():
            setattr(self, key, value)

    async def insert(self) -> _FakeCommentDoc:
        self.__class__.store[self.id] = self
        return self

    async def replace(self) -> _FakeCommentDoc:
        self.__class__.store[self.id] = self
        return self

    async def delete(self) -> None:
        self.__class__.store.pop(self.id, None)
        self.is_deleted = True

    def model_dump(self, **kwargs) -> dict:
        exclude = kwargs.get("exclude", set())
        data = {}
        if "id" not in exclude:
            data["id"] = self.id
        for attr in ["case_id", "content", "author_id", "author_name", "created_at", "updated_at"]:
            if attr not in exclude:
                val = getattr(self, attr, None)
                if val is not None:
                    data[attr] = val
        return data

    @classmethod
    def reset(cls) -> None:
        cls._id_counter = 0
        cls.store = {}

    @classmethod
    def find_one(cls, query=None, *args, **kwargs):
        """支持 TestCaseCommentDoc.get(comment_id) 查找"""
        async def _coro():
            # Beanie's get() passes the id as the first positional argument
            if isinstance(query, str) and query in cls.store:
                return cls.store[query]
            # Handle dict-style query: find_one({"_id": ...})
            if isinstance(query, dict) and "_id" in query:
                oid = str(query["_id"])
                return cls.store.get(oid)
            return None
        return _coro()

    # Beanie's `get` classmethod is aliased to find_one
    get = find_one

    @classmethod
    def find(cls, expr=None):
        """支持 Beanie 风格查询表达式"""

        # Pre-filter docs based on expression
        docs = list(cls.store.values())
        filter_field = None
        filter_value = None
        if expr is not None and isinstance(expr, _FakeExpr):
            filter_field = expr._field
            filter_value = expr._value
            docs = [d for d in docs if getattr(d, filter_field, None) == filter_value]

        class _Query:
            def __init__(self, pre_filtered_docs):
                self._docs = pre_filtered_docs
                self._skip_val = 0
                self._limit_val = 50
                self._sort_steps: list[tuple[str, int]] = []

            def sort(self, field, direction=None):
                if isinstance(field, _FakeExpr):
                    field_name = field._field
                    if isinstance(field._value, int) and field._value < 0:
                        self._sort_steps.append((field_name, -1))
                    else:
                        self._sort_steps.append((field_name, 1))
                return self

            def skip(self, n):
                self._skip_val = n
                return self

            def limit(self, n):
                self._limit_val = n
                return self

            async def count(self):
                return len(self._docs)

            async def to_list(self):
                docs = list(self._docs)
                for field_name, direction in self._sort_steps:
                    docs.sort(key=lambda d, f=field_name: getattr(d, f, 0) or 0, reverse=(direction < 0))
                skip = self._skip_val
                limit = self._limit_val
                return docs[skip:skip + limit]

        return _Query(docs)


# ══════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════

NOW = datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def reset_store():
    _FakeCommentDoc.reset()
    yield
    _FakeCommentDoc.reset()


def _make_doc(**overrides) -> _FakeCommentDoc:
    defaults = dict(
        case_id="TC-BMC-001",
        content="这是一条测试评论",
        author_id="user-001",
        author_name="张三",
        created_at=NOW,
        updated_at=None,
    )
    defaults.update(overrides)
    doc = _FakeCommentDoc(**defaults)
    _FakeCommentDoc.store[doc.id] = doc
    return doc


# ══════════════════════════════════════════════
#  Schema Tests
# ══════════════════════════════════════════════

class TestCommentSchemas:
    """测试用例评论 Schema 验证"""

    def test_create_request_valid(self):
        req = CreateCommentRequest(content="这是一条评论")
        assert req.content == "这是一条评论"

    def test_create_request_empty_rejected(self):
        with pytest.raises(Exception):
            CreateCommentRequest(content="")

    def test_create_request_too_long_rejected(self):
        with pytest.raises(Exception):
            CreateCommentRequest(content="x" * 2001)

    def test_update_request_valid(self):
        req = UpdateCommentRequest(content="更新后的评论")
        assert req.content == "更新后的评论"

    def test_comment_response_with_alias(self):
        """验证 comment_id 通过 _id 别名正确反序列化"""
        resp = CommentResponse(
            _id="comment-001",
            case_id="TC-BMC-001",
            content="test",
            author_id="u-1",
            created_at=NOW,
        )
        assert resp.comment_id == "comment-001"
        assert resp.case_id == "TC-BMC-001"

    def test_comment_response_by_field_name(self):
        """populate_by_name=True 允许用字段名 comment_id 传入"""
        resp = CommentResponse(
            comment_id="comment-002",
            case_id="TC-BMC-002",
            content="by name",
            author_id="u-2",
            created_at=NOW,
        )
        assert resp.comment_id == "comment-002"

    def test_comment_response_model_dump_uses_alias(self):
        """序列化时应以 _id 为 key 输出"""
        resp = CommentResponse(
            comment_id="c-001",
            case_id="TC-BMC-001",
            content="test",
            author_id="u-1",
            created_at=NOW,
        )
        dumped = resp.model_dump(by_alias=True)
        assert dumped["_id"] == "c-001"
        assert "comment_id" not in dumped

    def test_comment_list_response(self):
        items = [
            CommentResponse(comment_id="c-1", case_id="TC-001", content="a", author_id="u-1", created_at=NOW),
            CommentResponse(comment_id="c-2", case_id="TC-001", content="b", author_id="u-2", created_at=NOW),
        ]
        resp = CommentListResponse(items=items, total=2)
        assert len(resp.items) == 2
        assert resp.total == 2


# ══════════════════════════════════════════════
#  Service Tests
# ══════════════════════════════════════════════

SERVICE_MODULE = "app.modules.test_specs.service.comment_service"


class TestCommentService:
    """TestCaseCommentService 单元测试"""

    def test_create_comment(self):
        service = TestCaseCommentService()
        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            doc = asyncio.run(
                service.create_comment(
                    case_id="TC-BMC-001",
                    content="新评论",
                    author_id="user-001",
                    author_name="张三",
                )
            )
        assert doc.case_id == "TC-BMC-001"
        assert doc.content == "新评论"
        assert doc.author_id == "user-001"
        assert doc.author_name == "张三"
        assert doc.created_at is not None

    def test_create_comment_sets_created_at(self):
        service = TestCaseCommentService()
        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            doc = asyncio.run(
                service.create_comment(case_id="TC-001", content="test", author_id="u-1")
            )
        assert doc.created_at is not None

    def test_list_comments_empty(self):
        service = TestCaseCommentService()
        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            docs, total = asyncio.run(
                service.list_comments(case_id="TC-BMC-001")
            )
        assert docs == []
        assert total == 0

    def test_list_comments_returns_correct_case_only(self):
        service = TestCaseCommentService()
        _make_doc(case_id="TC-A", content="评论A")
        _make_doc(case_id="TC-B", content="评论B")
        _make_doc(case_id="TC-A", content="评论A2")

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            docs, total = asyncio.run(
                service.list_comments(case_id="TC-A")
            )

        assert total == 2
        contents = [d.content for d in docs]
        assert "评论A" in contents
        assert "评论A2" in contents
        assert "评论B" not in contents

    def test_list_comments_ordered_by_created_at_desc(self):
        """评论应按创建时间倒序排列（最新的在前）"""
        service = TestCaseCommentService()
        earlier = _make_doc(case_id="TC-001", content="较早", created_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
        later = _make_doc(case_id="TC-001", content="较新", created_at=datetime(2025, 6, 1, tzinfo=timezone.utc))

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            docs, _ = asyncio.run(
                service.list_comments(case_id="TC-001")
            )

        # 最新的在前
        ids = [d.id for d in docs]
        assert ids == [later.id, earlier.id]

    def test_list_comments_pagination(self):
        service = TestCaseCommentService()
        for i in range(10):
            _make_doc(case_id="TC-001", content=f"评论{i}", created_at=datetime(2025, 6, i + 1, tzinfo=timezone.utc))

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            docs, total = asyncio.run(
                service.list_comments(case_id="TC-001", limit=3, offset=2)
            )

        assert total == 10
        assert len(docs) == 3

    def test_get_comment_found(self):
        service = TestCaseCommentService()
        doc = _make_doc(case_id="TC-001", content="查找我")

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            found = asyncio.run(
                service.get_comment(comment_id=doc.id)
            )

        assert found is not None
        assert found.content == "查找我"

    def test_get_comment_not_found(self):
        service = TestCaseCommentService()

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            found = asyncio.run(
                service.get_comment(comment_id="nonexistent-id")
            )

        assert found is None

    def test_update_comment_updates_content(self):
        service = TestCaseCommentService()
        doc = _make_doc(case_id="TC-001", content="原始内容", author_id="user-001")

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            updated = asyncio.run(
                service.update_comment(
                    comment_id=doc.id,
                    content="更新后的内容",
                    actor_id="user-001",
                )
            )

        assert updated is not None
        assert updated.content == "更新后的内容"
        assert updated.updated_at is not None

    def test_update_comment_wrong_author_returns_none(self):
        service = TestCaseCommentService()
        doc = _make_doc(case_id="TC-001", content="原始内容", author_id="user-001")

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            updated = asyncio.run(
                service.update_comment(
                    comment_id=doc.id,
                    content="想篡改",
                    actor_id="user-002",  # 不是作者
                )
            )

        assert updated is None

    def test_update_comment_not_found_returns_none(self):
        service = TestCaseCommentService()

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            updated = asyncio.run(
                service.update_comment(
                    comment_id="nonexistent",
                    content="test",
                    actor_id="u-1",
                )
            )

        assert updated is None

    def test_delete_comment_success(self):
        service = TestCaseCommentService()
        doc = _make_doc(case_id="TC-001", content="待删除", author_id="user-001")

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            result = asyncio.run(
                service.delete_comment(
                    comment_id=doc.id,
                    actor_id="user-001",
                )
            )

        assert result is True

    def test_delete_comment_wrong_author_returns_false(self):
        service = TestCaseCommentService()
        doc = _make_doc(case_id="TC-001", content="待删除", author_id="user-001")

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            result = asyncio.run(
                service.delete_comment(
                    comment_id=doc.id,
                    actor_id="user-002",
                )
            )

        assert result is False

    def test_delete_comment_not_found_returns_false(self):
        service = TestCaseCommentService()

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            result = asyncio.run(
                service.delete_comment(
                    comment_id="nonexistent",
                    actor_id="u-1",
                )
            )

        assert result is False

    def test_create_comment_without_author_name(self):
        """author_name 为 None 时应正常工作"""
        service = TestCaseCommentService()
        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            doc = asyncio.run(
                service.create_comment(
                    case_id="TC-001",
                    content="无名称测试",
                    author_id="user-001",
                )
            )
        assert doc.author_name is None

    def test_full_lifecycle(self):
        """完整的评论生命周测试：创建 → 列表 → 获取 → 更新 → 删除"""
        service = TestCaseCommentService()

        with patch(f"{SERVICE_MODULE}.TestCaseCommentDoc", _FakeCommentDoc):
            # 创建
            doc = asyncio.run(
                service.create_comment(case_id="TC-LIFE", content="生命周期", author_id="u-1", author_name="用户1")
            )
            assert doc.id is not None

            # 列表
            docs, total = asyncio.run(service.list_comments(case_id="TC-LIFE"))
            assert total == 1
            assert docs[0].content == "生命周期"

            # 获取
            found = asyncio.run(service.get_comment(doc.id))
            assert found is not None
            assert found.author_name == "用户1"

            # 更新
            updated = asyncio.run(service.update_comment(doc.id, "已更新", "u-1"))
            assert updated is not None
            assert updated.content == "已更新"

            # 删除
            deleted = asyncio.run(service.delete_comment(doc.id, "u-1"))
            assert deleted is True

            # 验证已删除
            found_after = asyncio.run(service.get_comment(doc.id))
            assert found_after is None
