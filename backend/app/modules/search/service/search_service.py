"""全局搜索服务。"""
import re
from typing import List, Optional

from beanie.odm.documents import Document

from app.modules.execution.repository.models.execution import ExecutionTaskDoc
from app.modules.test_specs.repository.models.automation_test_case import (
    AutomationTestCaseDoc,
)
from app.modules.test_specs.repository.models.test_case import TestCaseDoc
from app.modules.test_specs.repository.models.test_case_comment import (
    TestCaseCommentDoc,
)
from app.modules.test_specs.repository.models.requirement import (
    TestRequirementDoc,
)
from app.modules.search.schemas import SearchGroup, SearchItem, SearchResponse


def _highlight(text: str, query: str) -> str:
    """在文本中用 <em> 标签包裹匹配的关键词。"""
    return re.sub(
        f"({re.escape(query)})",
        "<em>\\1</em>",
        text,
        flags=re.IGNORECASE,
    )


def _safe_subtitle(obj) -> str:
    """安全地获取副标题。"""
    if hasattr(obj, "status") and obj.status:
        return f"状态: {obj.status}"
    return ""


class SearchService:
    """全局搜索服务，跨模块搜索。"""

    async def search(
        self,
        query: str,
        types: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """执行全局搜索。

        Args:
            query: 搜索关键词
            types: 限定搜索的类型列表（None 表示搜索全部）
            limit: 每页条数
            offset: 分页偏移

        Returns:
            分组的搜索结果
        """
        q = query.strip()
        if not q:
            return SearchResponse(query=q, total=0, results=[])

        # 构建 $regex 模式
        pattern = re.escape(q)
        options = "i"

        groups: List[SearchGroup] = []
        total = 0

        # 并行搜索各个集合
        searches = []

        if types is None or "requirement" in types:
            searches.append(self._search_requirements(q, pattern, options, limit, offset))
        if types is None or "test_case" in types:
            searches.append(self._search_test_cases(q, pattern, options, limit, offset))
        if types is None or "automation_case" in types:
            searches.append(self._search_auto_cases(q, pattern, options, limit, offset))
        if types is None or "execution_task" in types:
            searches.append(self._search_tasks(q, pattern, options, limit, offset))
        if types is None or "comment" in types:
            searches.append(self._search_comments(q, pattern, options, limit, offset))

        # TODO: 后续可扩展搜索 Lab / 执行计划 / 用户等

        from asyncio import gather

        results = await gather(*searches, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                continue
            if isinstance(r, tuple):
                group, count = r
                if group and group.items:
                    groups.append(group)
                    total += count

        groups.sort(key=lambda g: len(g.items), reverse=True)

        return SearchResponse(query=q, total=total, results=groups)

    async def _search_requirements(
        self, q: str, pattern: str, options: str, limit: int, offset: int
    ):
        """搜索测试需求。"""
        docs = await TestRequirementDoc.find(
            {
                "$or": [
                    {"title": {"$regex": pattern, "$options": options}},
                    {"req_id": {"$regex": pattern, "$options": options}},
                    {"description": {"$regex": pattern, "$options": options}},
                    {"tags": {"$regex": pattern, "$options": options}},
                ],
            },
            fetch_links=False,
        ).sort(-TestRequirementDoc.updated_at).skip(offset).limit(limit).to_list()

        total = await TestRequirementDoc.find(
            {
                "$or": [
                    {"title": {"$regex": pattern, "$options": options}},
                    {"req_id": {"$regex": pattern, "$options": options}},
                    {"description": {"$regex": pattern, "$options": options}},
                    {"tags": {"$regex": pattern, "$options": options}},
                ],
            }
        ).count()

        items = [
            SearchItem(
                id=d.req_id,
                title=_highlight(d.title, q),
                subtitle=_safe_subtitle(d),
                type="requirement",
                type_label="测试需求",
                highlight=_highlight(d.description[:200], q) if d.description else None,
                url=f"?page=requirements&highlight={d.req_id}",
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs
        ]
        return SearchGroup(type="requirement", type_label="测试需求", items=items, total=total), total

    async def _search_test_cases(
        self, q: str, pattern: str, options: str, limit: int, offset: int
    ):
        """搜索手工测试用例。"""
        docs = await TestCaseDoc.find(
            {
                "$or": [
                    {"title": {"$regex": pattern, "$options": options}},
                    {"case_id": {"$regex": pattern, "$options": options}},
                    {"pre_condition": {"$regex": pattern, "$options": options}},
                    {"tags": {"$regex": pattern, "$options": options}},
                ],
            },
            fetch_links=False,
        ).sort(-TestCaseDoc.updated_at).skip(offset).limit(limit).to_list()

        total = await TestCaseDoc.find(
            {
                "$or": [
                    {"title": {"$regex": pattern, "$options": options}},
                    {"case_id": {"$regex": pattern, "$options": options}},
                    {"pre_condition": {"$regex": pattern, "$options": options}},
                    {"tags": {"$regex": pattern, "$options": options}},
                ],
            }
        ).count()

        items = [
            SearchItem(
                id=d.case_id,
                title=_highlight(d.title, q),
                subtitle=_safe_subtitle(d),
                type="test_case",
                type_label="测试用例",
                highlight=(
                    _highlight(d.pre_condition[:200], q) if d.pre_condition else None
                ),
                url=f"?page=testCases&highlight={d.case_id}",
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs
        ]
        return SearchGroup(type="test_case", type_label="测试用例", items=items, total=total), total

    async def _search_auto_cases(
        self, q: str, pattern: str, options: str, limit: int, offset: int
    ):
        """搜索自动化用例。"""
        docs = await AutomationTestCaseDoc.find(
            {
                "$or": [
                    {"name": {"$regex": pattern, "$options": options}},
                    {"auto_case_id": {"$regex": pattern, "$options": options}},
                    {"tags": {"$regex": pattern, "$options": options}},
                ],
            },
            fetch_links=False,
        ).sort(-AutomationTestCaseDoc.updated_at).skip(offset).limit(limit).to_list()

        total = await AutomationTestCaseDoc.find(
            {
                "$or": [
                    {"name": {"$regex": pattern, "$options": options}},
                    {"auto_case_id": {"$regex": pattern, "$options": options}},
                    {"tags": {"$regex": pattern, "$options": options}},
                ],
            }
        ).count()

        items = [
            SearchItem(
                id=d.auto_case_id,
                title=_highlight(d.name, q),
                subtitle=f"框架: {d.framework or '-'}",
                type="automation_case",
                type_label="自动化用例",
                url=f"?page=testCases",
            )
            for d in docs
        ]
        return SearchGroup(type="automation_case", type_label="自动化用例", items=items, total=total), total

    async def _search_tasks(
        self, q: str, pattern: str, options: str, limit: int, offset: int
    ):
        """搜索执行任务。"""
        docs = await ExecutionTaskDoc.find(
            {
                "$or": [
                    {"task_id": {"$regex": pattern, "$options": options}},
                ],
            },
            fetch_links=False,
        ).sort(-ExecutionTaskDoc.updated_at).skip(offset).limit(limit).to_list()

        total = await ExecutionTaskDoc.find(
            {
                "$or": [
                    {"task_id": {"$regex": pattern, "$options": options}},
                ],
            }
        ).count()

        items = [
            SearchItem(
                id=d.task_id,
                title=f"任务 {d.task_id}",
                subtitle=f"状态: {d.overall_status} | {d.case_count} 用例",
                type="execution_task",
                type_label="执行任务",
                url=f"?page=tasks&highlight={d.task_id}",
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs
        ]
        return SearchGroup(type="execution_task", type_label="执行任务", items=items, total=total), total

    async def _search_comments(
        self, q: str, pattern: str, options: str, limit: int, offset: int
    ):
        """搜索评论内容。"""
        docs = await TestCaseCommentDoc.find(
            {"content": {"$regex": pattern, "$options": options}},
            fetch_links=False,
        ).sort(-TestCaseCommentDoc.created_at).skip(offset).limit(limit).to_list()

        total = await TestCaseCommentDoc.find(
            {"content": {"$regex": pattern, "$options": options}},
        ).count()

        items = [
            SearchItem(
                id=d.comment_id,
                title=f"评论 ({d.author_id})",
                subtitle=f"用例: {d.case_id}",
                type="comment",
                type_label="评论",
                highlight=_highlight(d.content[:200], q),
                url=f"?page=testCases&highlight={d.case_id}",
                created_at=d.created_at,
            )
            for d in docs
        ]
        return SearchGroup(type="comment", type_label="评论", items=items, total=total), total
