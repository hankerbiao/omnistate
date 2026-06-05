"""测试用例变更记录服务"""
from __future__ import annotations

from typing import Any

from app.modules.auth.repository.models import UserDoc
from app.modules.test_specs.domain.field_diff import TRACKED_FIELDS, compute_field_changes
from app.modules.test_specs.repository.models.test_case_change_log import TestCaseChangeLogDoc


class TestCaseChangeLogService:
    """写入与查询测试用例变更记录。"""

    async def get_snapshot(self, case_dict: dict[str, Any]) -> dict[str, Any]:
        """从用例 dict 提取可 diff 的快照。"""
        return {field: case_dict.get(field) for field in TRACKED_FIELDS}

    async def append(
        self,
        case_id: str,
        operator_id: str,
        action: str,
        old_snapshot: dict[str, Any] | None,
        new_snapshot: dict[str, Any],
        remark: str | None = None,
        extra_changes: list[dict[str, Any]] | None = None,
    ) -> None:
        changes = compute_field_changes(old_snapshot, new_snapshot)
        if extra_changes:
            changes.extend(extra_changes)
        if not changes and action != "DELETE":
            if not remark:
                return

        revision_no = await self._next_revision_no(case_id)
        doc = TestCaseChangeLogDoc(
            case_id=case_id,
            revision_no=revision_no,
            action=action,
            operator_id=operator_id,
            changes=changes,
            remark=remark,
        )
        await doc.insert()

    async def list_logs(
        self,
        case_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        query = TestCaseChangeLogDoc.find(TestCaseChangeLogDoc.case_id == case_id)
        total = await query.count()
        docs = (
            await query.sort("-created_at")
            .skip(offset)
            .limit(limit)
            .to_list()
        )
        operator_ids = {doc.operator_id for doc in docs}
        name_map = await self._load_operator_names(operator_ids)
        items = [self._to_dict(doc, name_map.get(doc.operator_id)) for doc in docs]
        return {"items": items, "total": total}

    async def _next_revision_no(self, case_id: str) -> int:
        latest = (
            await TestCaseChangeLogDoc.find(TestCaseChangeLogDoc.case_id == case_id)
            .sort("-revision_no")
            .limit(1)
            .to_list()
        )
        if not latest:
            return 1
        return latest[0].revision_no + 1

    @staticmethod
    async def _load_operator_names(operator_ids: set[str]) -> dict[str, str]:
        if not operator_ids:
            return {}
        users = await UserDoc.find({"user_id": {"$in": list(operator_ids)}}).to_list()
        return {user.user_id: user.username for user in users}

    @staticmethod
    def _to_dict(doc: TestCaseChangeLogDoc, operator_name: str | None) -> dict[str, Any]:
        return {
            "id": str(doc.id),
            "case_id": doc.case_id,
            "revision_no": doc.revision_no,
            "action": doc.action,
            "operator_id": doc.operator_id,
            "operator_name": operator_name,
            "changes": doc.changes,
            "remark": doc.remark,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
