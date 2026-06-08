"""测试用例评论服务"""
from datetime import datetime, timezone
from typing import Optional

from app.modules.test_specs.repository.models.test_case_comment import TestCaseCommentDoc


class TestCaseCommentService:
    """测试用例评论领域服务"""

    async def create_comment(
        self,
        case_id: str,
        content: str,
        author_id: str,
        author_name: Optional[str] = None,
    ) -> TestCaseCommentDoc:
        doc = TestCaseCommentDoc(
            case_id=case_id,
            content=content,
            author_id=author_id,
            author_name=author_name,
        )
        return await doc.insert()

    async def list_comments(
        self,
        case_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TestCaseCommentDoc], int]:
        query = TestCaseCommentDoc.find(TestCaseCommentDoc.case_id == case_id)
        total = await query.count()
        docs = (
            await query
            .sort(-TestCaseCommentDoc.created_at)
            .skip(offset)
            .limit(limit)
            .to_list()
        )
        return docs, total

    async def get_comment(self, comment_id: str) -> Optional[TestCaseCommentDoc]:
        return await TestCaseCommentDoc.get(comment_id)

    async def update_comment(
        self,
        comment_id: str,
        content: str,
        actor_id: str,
    ) -> Optional[TestCaseCommentDoc]:
        doc = await TestCaseCommentDoc.get(comment_id)
        if doc is None or doc.author_id != actor_id:
            return None
        doc.content = content
        doc.updated_at = datetime.now(timezone.utc)
        return await doc.replace()

    async def delete_comment(
        self,
        comment_id: str,
        actor_id: str,
    ) -> bool:
        doc = await TestCaseCommentDoc.get(comment_id)
        if doc is None or doc.author_id != actor_id:
            return False
        await doc.delete()
        return True
