"""执行任务 case 解析与快照能力。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.execution.repository.models import ExecutionTaskCaseDoc, ExecutionTaskDoc
from app.modules.test_specs.repository.models import AutomationTestCaseDoc, TestCaseDoc


class ExecutionTaskCaseMixin:
    """处理 case 解析、快照与当前态重建。"""

    @staticmethod
    async def _load_case_docs(case_ids: List[str]) -> Dict[str, Any]:
        """加载并校验任务关联的测试用例。"""
        docs = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False,
        }).to_list()
        doc_map = {doc.case_id: doc for doc in docs}
        missing = [cid for cid in case_ids if cid not in doc_map]
        if missing:
            raise KeyError(f"Test cases not found: {missing}")
        return doc_map

    @staticmethod
    async def resolve_case_ids_by_auto_case_ids(auto_case_ids: List[str]) -> List[str]:
        """将 auto_case_id 列表解析为平台测试用例 case_id，保留原始顺序。"""
        auto_docs = await AutomationTestCaseDoc.find({
            "auto_case_id": {"$in": auto_case_ids},
            "is_deleted": False,
        }).to_list()
        source_mapping = {doc.auto_case_id: doc.source_case_id for doc in auto_docs}

        missing_auto_case_ids = [auto_case_id for auto_case_id in auto_case_ids if auto_case_id not in source_mapping]
        if missing_auto_case_ids:
            raise KeyError(f"Automation test cases not found: {missing_auto_case_ids}")

        source_case_ids = [source_mapping[auto_case_id] for auto_case_id in auto_case_ids]
        docs = await TestCaseDoc.find({
            "case_id": {"$in": source_case_ids},
            "is_deleted": False,
        }).to_list()

        mapping: Dict[str, List[str]] = {}
        for doc in docs:
            source_case_id = getattr(doc, "case_id", None)
            if not source_case_id:
                continue
            mapping.setdefault(source_case_id, []).append(doc.case_id)

        missing_source_case_ids = [source_case_id for source_case_id in source_case_ids if source_case_id not in mapping]
        if missing_source_case_ids:
            missing_auto_case_ids = [
                auto_case_id for auto_case_id in auto_case_ids
                if source_mapping.get(auto_case_id) in missing_source_case_ids
            ]
            raise KeyError(
                "Automation test cases source_case_id not matched to test cases: "
                f"auto_case_ids={missing_auto_case_ids}, source_case_ids={missing_source_case_ids}"
            )

        ambiguous = {
            source_case_id: case_ids
            for source_case_id, case_ids in mapping.items()
            if len(case_ids) > 1
        }
        if ambiguous:
            raise ValueError(f"Automation test cases linked to multiple test cases: {ambiguous}")

        return [mapping[source_mapping[auto_case_id]][0] for auto_case_id in auto_case_ids]

    @staticmethod
    async def resolve_auto_case_ids_by_case_ids(case_ids: List[str]) -> List[str]:
        """根据平台 case_id 反查 auto_case_id，保留原始顺序。"""
        docs = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False,
        }).to_list()
        source_mapping: Dict[str, str] = {}
        missing: List[str] = []
        for doc in docs:
            source_case_id = getattr(doc, "case_id", None)
            if source_case_id:
                source_mapping[doc.case_id] = source_case_id
        for case_id in case_ids:
            if case_id not in source_mapping:
                missing.append(case_id)
        if missing:
            raise KeyError(f"Test cases not linked to automation test cases: {missing}")

        auto_docs = await AutomationTestCaseDoc.find({
            "source_case_id": {"$in": list(source_mapping.values())},
            "is_deleted": False,
        }).to_list()
        auto_mapping = {doc.source_case_id: doc.auto_case_id for doc in auto_docs}
        missing_sources = [source_case_id for source_case_id in source_mapping.values() if source_case_id not in auto_mapping]
        if missing_sources:
            missing_case_ids = [case_id for case_id, source_case_id in source_mapping.items() if source_case_id in missing_sources]
            raise KeyError(f"Test cases not linked to automation test cases: {missing_case_ids}")
        return [auto_mapping[source_mapping[case_id]] for case_id in case_ids]

    @staticmethod
    def _extract_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        """从任务快照中恢复 case 顺序。"""
        return [case["case_id"] for case in payload.get("cases", [])]

    @staticmethod
    def _extract_auto_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        """从任务快照中恢复 auto_case_id 顺序。"""
        return [case["auto_case_id"] for case in payload.get("cases", []) if "auto_case_id" in case]

    async def _resolve_task_case_pairs(self, task_doc: ExecutionTaskDoc) -> tuple[List[str], List[str]]:
        case_ids = self._extract_case_ids_from_payload(task_doc.request_payload)
        auto_case_ids = self._extract_auto_case_ids_from_payload(task_doc.request_payload)
        if not auto_case_ids:
            auto_case_ids = await self.resolve_auto_case_ids_by_case_ids(case_ids)
        return case_ids, auto_case_ids

    @staticmethod
    def _build_case_snapshot(case_doc: TestCaseDoc, auto_case_id: str | None) -> Dict[str, Any]:
        """构建任务侧静态 case 快照。"""
        return {
            "case_id": case_doc.case_id,
            "auto_case_id": auto_case_id,
            "ref_req_id": case_doc.ref_req_id,
            "workflow_item_id": case_doc.workflow_item_id,
            "title": case_doc.title,
            "version": case_doc.version,
            "status": getattr(case_doc, "status", "draft"),
            "priority": case_doc.priority,
            "tags": list(case_doc.tags or []),
            "test_category": case_doc.test_category,
            "estimated_duration_sec": case_doc.estimated_duration_sec,
            "target_components": list(case_doc.target_components or []),
            "required_env": dict(case_doc.required_env or {}),
            "tooling_req": list(case_doc.tooling_req or []),
            "is_destructive": case_doc.is_destructive,
            "pre_condition": case_doc.pre_condition,
            "post_condition": case_doc.post_condition,
            "steps": [step.model_dump() for step in case_doc.steps],
            "cleanup_steps": [step.model_dump() for step in case_doc.cleanup_steps],
            "custom_fields": dict(case_doc.custom_fields or {}),
        }

    @classmethod
    async def _replace_task_case_docs(
        cls,
        task_id: str,
        case_ids: List[str],
        auto_case_ids: List[str],
        doc_map: Dict[str, Any],
    ) -> None:
        """重建尚未触发任务的 case 明细快照。"""
        existing_docs = await ExecutionTaskCaseDoc.find({"task_id": task_id}).to_list()
        for existing_doc in existing_docs:
            await existing_doc.delete()

        auto_case_id_map = {
            case_id: auto_case_id
            for case_id, auto_case_id in zip(case_ids, auto_case_ids)
        }

        for order_no, case_id in enumerate(case_ids):
            case_doc = doc_map[case_id]
            snapshot = cls._build_case_snapshot(case_doc, auto_case_id=auto_case_id_map.get(case_id))
            await ExecutionTaskCaseDoc(
                task_id=task_id,
                case_id=case_id,
                case_snapshot=snapshot,
                order_no=order_no,
                dispatch_status="PENDING",
                status="QUEUED",
                step_total=0,
                step_passed=0,
                step_failed=0,
                step_skipped=0,
                last_seq=0,
                result_data={},
            ).insert()
