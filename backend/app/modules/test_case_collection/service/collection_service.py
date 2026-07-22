"""用例集合核心服务。"""
import csv
from io import BytesIO, StringIO
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from openpyxl import Workbook

from app.modules.test_case_collection.repository.models import TestCaseCollectionChangeLogDoc, TestCaseCollectionDoc
from app.modules.test_case_collection.schemas import (
    AddCasesRequest,
    CollectionChangeLogListResponse,
    CollectionChangeLogResponse,
    CollectionListItem,
    CollectionResponse,
    CollectionValiditySummary,
    CopyCollectionRequest,
    CreateCollectionRequest,
    RemoveCasesRequest,
    UpdateCollectionRequest,
)
from app.modules.test_case_collection.service.exceptions import (
    CollectionNotFoundError,
)
from app.modules.test_specs.repository.models import AutomationTestCaseDoc, TestCaseDoc
from app.shared.auth.jwt_auth import is_admin_role
from app.shared.core.logger import log
from app.shared.service import SequenceIdService


class TestCaseCollectionService:
    """用例集合服务。"""

    def __init__(self):
        self._sequence_service = SequenceIdService()

    @staticmethod
    def _actor_id(current_user: Optional[Dict[str, Any]], fallback: str = "system") -> str:
        return (current_user or {}).get("user_id") or fallback

    @staticmethod
    def _actor_name(current_user: Optional[Dict[str, Any]]) -> Optional[str]:
        if not current_user:
            return None
        return current_user.get("username") or current_user.get("name") or current_user.get("user_id")

    async def _save_log(
        self,
        collection_id: str,
        action: str,
        current_user: Optional[Dict[str, Any]] = None,
        *,
        case_changes: Optional[List[Dict[str, Any]]] = None,
        field_changes: Optional[List[Dict[str, Any]]] = None,
        export_format: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> None:
        try:
            await TestCaseCollectionChangeLogDoc(
                collection_id=collection_id,
                action=action,
                operator_id=self._actor_id(current_user),
                operator_name=self._actor_name(current_user),
                case_changes=case_changes or [],
                field_changes=field_changes or [],
                export_format=export_format,
                remark=remark,
            ).insert()
        except Exception as exc:
            log.warning(
                "Failed to write collection change log | collection_id={} | action={} | error={}",
                collection_id,
                action,
                exc,
            )

    async def create(
        self,
        request: CreateCollectionRequest,
        creator_id: str,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> CollectionResponse:
        """创建用例集合。"""
        seq = await self._sequence_service.next("test_case_collection")
        collection_id = f"CC-{str(seq).zfill(4)}"

        doc = TestCaseCollectionDoc(
            collection_id=collection_id,
            name=request.name,
            description=request.description,
            tags=request.tags,
            case_ids=list(set(request.case_ids)),
            auto_case_ids=list(set(request.auto_case_ids)),
            created_by=creator_id,
        )
        await doc.insert()
        await self._save_log(
            collection_id,
            "CREATE",
            current_user or {"user_id": creator_id},
            case_changes=self._case_changes("ADD", request.case_ids, request.auto_case_ids),
            remark="创建集合",
        )
        return CollectionResponse.from_doc(doc)

    async def get(self, collection_id: str) -> CollectionResponse:
        """获取集合详情。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")
        return CollectionResponse.from_doc(doc)

    async def update(
        self,
        collection_id: str,
        request: UpdateCollectionRequest,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> CollectionResponse:
        """更新集合基本信息。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        updates = {}
        field_changes = []
        if request.name is not None:
            updates["name"] = request.name
            if doc.name != request.name:
                field_changes.append({"field": "name", "old_value": doc.name, "new_value": request.name})
        if request.description is not None:
            updates["description"] = request.description
            if doc.description != request.description:
                field_changes.append({
                    "field": "description",
                    "old_value": doc.description,
                    "new_value": request.description,
                })
        if request.tags is not None:
            updates["tags"] = request.tags
            if doc.tags != request.tags:
                field_changes.append({"field": "tags", "old_value": doc.tags, "new_value": request.tags})
        updates["updated_at"] = datetime.utcnow()

        await doc.update({"$set": updates})
        if field_changes:
            await self._save_log(collection_id, "UPDATE", current_user, field_changes=field_changes, remark="更新集合信息")
        doc = await TestCaseCollectionDoc.find_one({"collection_id": collection_id})
        return CollectionResponse.from_doc(doc) if doc else await self.get(collection_id)

    async def delete(self, collection_id: str, current_user: Dict[str, Any]) -> None:
        """逻辑删除集合。仅 Admin 或创建者可删除。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        user_id = current_user.get("user_id", "")
        role_ids = current_user.get("role_ids", [])
        if not is_admin_role(role_ids) and doc.created_by != user_id:
            raise HTTPException(
                status_code=403,
                detail="仅 Admin 或创建者可删除此集合",
            )

        await doc.update({"$set": {"is_active": False, "updated_at": datetime.utcnow()}})
        await self._save_log(collection_id, "DELETE", current_user, remark="删除集合")

    @staticmethod
    def _case_changes(action: str, case_ids: List[str], auto_case_ids: List[str]) -> List[Dict[str, Any]]:
        return (
            [{"type": "manual", "case_id": case_id, "action": action} for case_id in case_ids]
            + [{"type": "auto", "case_id": case_id, "action": action} for case_id in auto_case_ids]
        )

    async def add_cases(
        self,
        collection_id: str,
        request: AddCasesRequest,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> CollectionResponse:
        """向集合添加用例（去重）。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        old_case_set = set(doc.case_ids)
        old_auto_set = set(doc.auto_case_ids)
        new_case_ids = list(set(doc.case_ids + request.case_ids))
        new_auto_ids = list(set(doc.auto_case_ids + request.auto_case_ids))
        added_case_ids = [case_id for case_id in new_case_ids if case_id not in old_case_set]
        added_auto_ids = [case_id for case_id in new_auto_ids if case_id not in old_auto_set]
        await doc.update({
            "$set": {
                "case_ids": new_case_ids,
                "auto_case_ids": new_auto_ids,
                "updated_at": datetime.utcnow(),
            }
        })
        doc.case_ids = new_case_ids
        doc.auto_case_ids = new_auto_ids
        if added_case_ids or added_auto_ids:
            await self._save_log(
                collection_id,
                "ADD_CASES",
                current_user,
                case_changes=self._case_changes("ADD", added_case_ids, added_auto_ids),
                remark=f"添加 {len(added_case_ids) + len(added_auto_ids)} 个用例",
            )
        return CollectionResponse.from_doc(doc)

    async def remove_cases(
        self,
        collection_id: str,
        request: RemoveCasesRequest,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> CollectionResponse:
        """从集合移除用例。"""
        doc = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        remove_set = set(request.case_ids)
        remove_auto_set = set(request.auto_case_ids)
        removed_case_ids = [c for c in doc.case_ids if c in remove_set]
        removed_auto_ids = [c for c in doc.auto_case_ids if c in remove_auto_set]
        new_case_ids = [c for c in doc.case_ids if c not in remove_set]
        new_auto_ids = [c for c in doc.auto_case_ids if c not in remove_auto_set]
        await doc.update({
            "$set": {
                "case_ids": new_case_ids,
                "auto_case_ids": new_auto_ids,
                "updated_at": datetime.utcnow(),
            }
        })
        doc.case_ids = new_case_ids
        doc.auto_case_ids = new_auto_ids
        if removed_case_ids or removed_auto_ids:
            await self._save_log(
                collection_id,
                "REMOVE_CASES",
                current_user,
                case_changes=self._case_changes("REMOVE", removed_case_ids, removed_auto_ids),
                remark=f"移除 {len(removed_case_ids) + len(removed_auto_ids)} 个用例",
            )
        return CollectionResponse.from_doc(doc)

    async def copy(
        self,
        collection_id: str,
        request: CopyCollectionRequest,
        current_user: Dict[str, Any],
    ) -> CollectionResponse:
        """另存为集合。"""
        source = await TestCaseCollectionDoc.find_one(
            {"collection_id": collection_id, "is_active": True}
        )
        if not source:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        new_doc = await self.create(
            CreateCollectionRequest(
                name=request.name,
                description=request.description,
                tags=request.tags,
                case_ids=source.case_ids if request.include_cases else [],
                auto_case_ids=source.auto_case_ids if request.include_cases else [],
            ),
            creator_id=self._actor_id(current_user),
            current_user=current_user,
        )
        await self._save_log(
            collection_id,
            "COPY_FROM",
            current_user,
            remark=f"另存为集合 {new_doc.collection_id}",
        )
        await self._save_log(
            new_doc.collection_id,
            "COPY_TO",
            current_user,
            remark=f"从集合 {collection_id} 另存为",
        )
        return new_doc

    async def history(self, collection_id: str, limit: int = 50, offset: int = 0) -> CollectionChangeLogListResponse:
        """获取集合变更历史。"""
        exists = await TestCaseCollectionDoc.find_one({"collection_id": collection_id})
        if not exists:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")
        query = TestCaseCollectionChangeLogDoc.find(TestCaseCollectionChangeLogDoc.collection_id == collection_id)
        total = await query.count()
        docs = await query.sort(-TestCaseCollectionChangeLogDoc.created_at).skip(offset).limit(limit).to_list()
        return CollectionChangeLogListResponse(
            items=[CollectionChangeLogResponse.from_doc(doc) for doc in docs],
            total=total,
        )

    @staticmethod
    def _risk_label(code: str) -> str:
        return {
            "DELETED_OR_MISSING": "已删除/缺失",
            "INACTIVE": "已停用",
            "DEPRECATED": "已废弃",
            "AUTOMATION_INVALID": "自动化失效",
        }.get(code, code)

    async def _load_case_context(
        self,
        collection_id: str,
        *,
        active_only: bool = True,
    ) -> tuple[TestCaseCollectionDoc, Dict[str, Any], Dict[str, Any]]:
        query: Dict[str, Any] = {"collection_id": collection_id}
        if active_only:
            query["is_active"] = True

        doc = await TestCaseCollectionDoc.find_one(query)
        if not doc:
            raise CollectionNotFoundError(f"集合 {collection_id} 不存在")

        manual_docs = await TestCaseDoc.find({"case_id": {"$in": doc.case_ids}, "is_deleted": False}).to_list()
        auto_docs = await AutomationTestCaseDoc.find({
            "auto_case_id": {"$in": doc.auto_case_ids},
            "is_deleted": False,
        }).to_list()
        manual_map = {case.case_id: case for case in manual_docs}
        auto_map = {case.auto_case_id: case for case in auto_docs}
        return doc, manual_map, auto_map

    async def validity(self, collection_id: str) -> CollectionValiditySummary:
        """计算集合内用例有效性。"""
        doc, manual_map, auto_map = await self._load_case_context(collection_id)
        return self._build_validity_summary(doc, manual_map, auto_map)

    def _build_validity_summary(
        self,
        doc: TestCaseCollectionDoc,
        manual_map: Dict[str, Any],
        auto_map: Dict[str, Any],
    ) -> CollectionValiditySummary:
        cases = []
        counters = {
            "inactive_count": 0,
            "missing_count": 0,
            "deprecated_count": 0,
            "automation_invalid_count": 0,
        }

        for case_id in doc.case_ids:
            case = manual_map.get(case_id)
            risk_code = None
            if not case:
                risk_code = "DELETED_OR_MISSING"
                counters["missing_count"] += 1
            elif not case.is_active:
                risk_code = "INACTIVE"
                counters["inactive_count"] += 1
            elif str(getattr(case, "status", "")).upper() in {"DEPRECATED", "INACTIVE", "DISABLED", "废弃", "停用"}:
                risk_code = "DEPRECATED"
                counters["deprecated_count"] += 1
            cases.append({
                "type": "manual",
                "case_id": case_id,
                "valid": risk_code is None,
                "risk_code": risk_code,
                "risk_label": self._risk_label(risk_code) if risk_code else None,
            })

        for case_id in doc.auto_case_ids:
            case = auto_map.get(case_id)
            risk_code = None
            if not case:
                risk_code = "DELETED_OR_MISSING"
                counters["missing_count"] += 1
            elif str(getattr(case, "status", "")).upper() != "ACTIVE":
                risk_code = "AUTOMATION_INVALID"
                counters["automation_invalid_count"] += 1
            cases.append({
                "type": "auto",
                "case_id": case_id,
                "valid": risk_code is None,
                "risk_code": risk_code,
                "risk_label": self._risk_label(risk_code) if risk_code else None,
            })

        risk_count = sum(1 for item in cases if not item["valid"])
        return CollectionValiditySummary(
            total=len(cases),
            valid_count=len(cases) - risk_count,
            risk_count=risk_count,
            **counters,
            cases=cases,
        )

    async def _export_rows(
        self,
        doc: TestCaseCollectionDoc,
        manual_map: Dict[str, Any],
        auto_map: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        validity = self._build_validity_summary(doc, manual_map, auto_map)
        risk_map = {(item.type, item.case_id): item for item in validity.cases}
        rows = []
        for case_id in doc.case_ids:
            case = manual_map.get(case_id)
            risk = risk_map.get(("manual", case_id))
            rows.append({
                "集合ID": doc.collection_id,
                "集合名称": doc.name,
                "用例类型": "手工",
                "用例ID": case_id,
                "标题": getattr(case, "title", "") if case else "",
                "目录": "/".join(getattr(case, "catalog_path", []) or []) if case else "",
                "状态": getattr(case, "status", "") if case else "",
                "有效性风险": risk.risk_label if risk and risk.risk_label else "全部有效",
                "版本/脚本信息": getattr(case, "version", "") if case else "",
                "更新时间": getattr(case, "updated_at", "") if case else "",
            })
        for case_id in doc.auto_case_ids:
            case = auto_map.get(case_id)
            risk = risk_map.get(("auto", case_id))
            rows.append({
                "集合ID": doc.collection_id,
                "集合名称": doc.name,
                "用例类型": "自动化",
                "用例ID": case_id,
                "标题": getattr(case, "name", "") if case else "",
                "目录": "",
                "状态": getattr(case, "status", "") if case else "",
                "有效性风险": risk.risk_label if risk and risk.risk_label else "全部有效",
                "版本/脚本信息": getattr(getattr(case, "code_snapshot", None), "version", "") if case else "",
                "更新时间": getattr(case, "updated_at", "") if case else "",
            })
        return rows

    async def export_cases(
        self,
        collection_id: str,
        export_format: str,
        current_user: Dict[str, Any],
    ) -> tuple[bytes, str, str]:
        """生成集合导出文件。"""
        normalized = export_format.lower()
        if normalized not in {"csv", "xlsx"}:
            raise ValueError("format 仅支持 csv 或 xlsx")

        doc, manual_map, auto_map = await self._load_case_context(collection_id)
        rows = await self._export_rows(doc, manual_map, auto_map)
        headers = ["集合ID", "集合名称", "用例类型", "用例ID", "标题", "目录", "状态", "有效性风险", "版本/脚本信息", "更新时间"]
        if normalized == "csv":
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
            content = output.getvalue().encode("utf-8-sig")
            media_type = "text/csv; charset=utf-8"
        else:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "集合用例清单"
            sheet.append(headers)
            for row in rows:
                sheet.append([row.get(header, "") for header in headers])
            output = BytesIO()
            workbook.save(output)
            content = output.getvalue()
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        await self._save_log(
            collection_id,
            "EXPORT",
            current_user,
            export_format=normalized,
            remark=f"导出 {normalized.upper()} 清单",
        )
        filename = f"{collection_id}_cases.{normalized}"
        return content, media_type, filename

    async def list_all(self, query: Optional[str] = None) -> List[CollectionListItem]:
        """查询集合列表，支持模糊搜索。"""
        filter_expr: dict = {"is_active": True}

        if query:
            pattern = re.escape(query.strip())
            filter_expr["$or"] = [
                {"name": {"$regex": pattern, "$options": "i"}},
                {"description": {"$regex": pattern, "$options": "i"}},
                {"tags": {"$regex": pattern, "$options": "i"}},
            ]

        docs = await TestCaseCollectionDoc.find(filter_expr).sort(
            -TestCaseCollectionDoc.updated_at
        ).to_list()
        return [CollectionListItem.from_doc(d) for d in docs]

    async def search(self, q: str, limit: int = 10) -> List[CollectionListItem]:
        """快速搜索集合（用于任务创建时的下拉选择）。"""
        pattern = re.escape(q.strip())
        docs = await TestCaseCollectionDoc.find(
            {
                "is_active": True,
                "$or": [
                    {"name": {"$regex": pattern, "$options": "i"}},
                    {"tags": {"$regex": pattern, "$options": "i"}},
                ],
            }
        ).limit(limit).to_list()
        return [CollectionListItem.from_doc(d) for d in docs]
