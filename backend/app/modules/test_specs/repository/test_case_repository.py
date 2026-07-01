"""测试用例仓储实现。

实现 domain.repositories.TestCaseRepositoryProtocol，
封装所有对 TestCaseDoc 的 Beanie 数据访问操作。

service 层依赖协议而非本实现，测试时可注入 Mock 替换。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pymongo import AsyncMongoClient

from app.modules.test_specs.domain.repositories import TestCaseRepositoryProtocol
from app.modules.test_specs.repository.models import TestCaseDoc
from app.shared.core.mongo_client import get_mongo_client


class TestCaseRepository(TestCaseRepositoryProtocol):
    """TestCaseDoc 的 Beanie 仓储实现。"""

    async def find_active_by_case_id(self, case_id: str) -> Optional[TestCaseDoc]:
        """按 case_id 查询未删除的测试用例文档。"""
        return await TestCaseDoc.find_one(
            TestCaseDoc.case_id == case_id,
            {"is_deleted": False},
        )

    async def find_by_case_id(self, case_id: str) -> Optional[TestCaseDoc]:
        """按 case_id 查询测试用例文档（含已删除）。"""
        return await TestCaseDoc.find_one(TestCaseDoc.case_id == case_id)

    async def insert(self, doc: TestCaseDoc, session: Any = None) -> TestCaseDoc:
        """插入一条测试用例文档。"""
        await doc.insert(session=session)
        return doc

    async def save(self, doc: TestCaseDoc, session: Any = None) -> TestCaseDoc:
        """保存测试用例文档的变更。"""
        await doc.save(session=session)
        return doc

    async def count(self, filter_doc: Dict[str, Any]) -> int:
        """按条件统计测试用例数量。"""
        return await TestCaseDoc.find(filter_doc).count()

    def build_find_query(self, mongo_query: Dict[str, Any]):
        """构建 Beanie find 查询对象，支持链式追加条件。"""
        return TestCaseDoc.find(mongo_query)

    async def get_mongo_client(self) -> Optional[AsyncMongoClient]:
        """获取底层 MongoDB 客户端，未初始化返回 None。"""
        try:
            return get_mongo_client()
        except RuntimeError:
            return None
