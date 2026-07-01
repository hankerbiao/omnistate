"""测试用例仓储协议（Repository Protocol）。

将 TestCaseService 对 Beanie Document 的直接依赖收玫为协议依赖，
使核心业务逻辑可在单测中 Mock 数据访问层。

设计原则：
- 协议定义在 domain 层（纯抽象，不 import beanie/pymongo）
- 实现在 repository 层（TestCaseRepository 直接操作 Document）
- service 依赖协议，通过构造器注入，便于测试替换

当前为渐进式引入：协议覆盖 TestCaseService 高频使用的查询/写入方法，
未覆盖的方法暂保持直接 Document 调用，后续逐步迁移。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class TestCaseRepositoryProtocol(ABC):
    """测试用例仓储协议。

    抽象 TestCaseService 对 TestCaseDoc 的数据访问操作，
    使 service 依赖协议而非具体 Beanie Document。

    domain 层协议不 import 任何框架依赖（pymongo/beanie），
    返回值为 Any 以避免对 Document 类型的编译期耦合。
    """

    @abstractmethod
    async def find_active_by_case_id(self, case_id: str) -> Any:
        """按 case_id 查询未删除的测试用例文档，不存在返回 None。"""
        ...

    @abstractmethod
    async def find_by_case_id(self, case_id: str) -> Any:
        """按 case_id 查询测试用例文档（含已删除），不存在返回 None。"""
        ...

    @abstractmethod
    async def insert(self, doc: Any, session: Any = None) -> Any:
        """插入一条测试用例文档。"""
        ...

    @abstractmethod
    async def save(self, doc: Any, session: Any = None) -> Any:
        """保存测试用例文档的变更。"""
        ...

    @abstractmethod
    async def count(self, filter_doc: Dict[str, Any]) -> int:
        """按条件统计测试用例数量。"""
        ...

    @abstractmethod
    def build_find_query(self, mongo_query: Dict[str, Any]) -> Any:
        """构建查询对象，支持链式追加 find/sort/skip/limit/to_list。

        返回值类型为 Any 以避免 domain 层对 Beanie 的编译期依赖，
        实际返回 Beanie FindQuery 对象。
        """
        ...

    @abstractmethod
    async def get_mongo_client(self) -> Optional[Any]:
        """获取底层 MongoDB 客户端（事务用），未初始化返回 None。

        返回值为 pymongo AsyncMongoClient 或 None，协议用 Any 避免框架耦合。
        """
        ...
