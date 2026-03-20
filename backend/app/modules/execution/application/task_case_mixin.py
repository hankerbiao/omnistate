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
        case_ids, _ = await ExecutionTaskCaseMixin.resolve_case_bindings_by_auto_case_ids(auto_case_ids)
        return case_ids

    @staticmethod
    async def resolve_case_bindings_by_auto_case_ids(
        auto_case_ids: List[str],
    ) -> tuple[List[str], List[str | None]]:
        """将 auto_case_id 列表解析为平台 case_id 和脚本实体 ID，保留原始顺序。"""
        auto_docs = await AutomationTestCaseDoc.find({
            "auto_case_id": {"$in": auto_case_ids},
            "is_deleted": False,
        }).to_list()
        source_mapping = {doc.auto_case_id: doc.dml_manual_case_id for doc in auto_docs}
        script_mapping = {
            doc.auto_case_id: getattr(getattr(doc, "script_ref", None), "entity_id", None)
            for doc in auto_docs
        }

        missing_auto_case_ids = [auto_case_id for auto_case_id in auto_case_ids if auto_case_id not in source_mapping]
        if missing_auto_case_ids:
            raise KeyError(f"Automation test cases not found: {missing_auto_case_ids}")

        source_case_ids = [source_mapping[auto_case_id] for auto_case_id in auto_case_ids]
        docs = await TestCaseDoc.find({
            "case_id": {"$in": source_case_ids},
            "is_deleted": False,
        }).to_list()

        missing_source_case_ids = [source_case_id for source_case_id in source_case_ids if source_case_id not in {
            getattr(doc, "case_id", None) for doc in docs
        }]
        if missing_source_case_ids:
            missing_bindings = [
                {
                    "auto_case_id": auto_case_id,
                    "dml_manual_case_id": source_mapping.get(auto_case_id),
                }
                for auto_case_id in auto_case_ids
                if source_mapping.get(auto_case_id) in missing_source_case_ids
            ]
            raise KeyError(
                "Automation test cases linked manual cases not found: "
                f"{missing_bindings}"
            )

        mapping: Dict[str, List[str]] = {}
        for doc in docs:
            source_case_id = getattr(doc, "case_id", None)
            if not source_case_id:
                continue
            mapping.setdefault(source_case_id, []).append(doc.case_id)

        ambiguous = {
            source_case_id: case_ids
            for source_case_id, case_ids in mapping.items()
            if len(case_ids) > 1
        }
        if ambiguous:
            raise ValueError(f"Automation test cases linked to multiple test cases: {ambiguous}")

        case_ids = [mapping[source_mapping[auto_case_id]][0] for auto_case_id in auto_case_ids]
        script_entity_ids = [script_mapping.get(auto_case_id) for auto_case_id in auto_case_ids]
        return case_ids, script_entity_ids

    @staticmethod
    async def resolve_auto_case_ids_by_case_ids(case_ids: List[str]) -> List[str]:
        """根据平台 case_id 反查 auto_case_id，保留原始顺序。"""
        auto_docs = await AutomationTestCaseDoc.find({
            "dml_manual_case_id": {"$in": case_ids},
            "is_deleted": False,
        }).to_list()
        auto_mapping = {doc.dml_manual_case_id: doc.auto_case_id for doc in auto_docs}
        missing_case_ids = [case_id for case_id in case_ids if case_id not in auto_mapping]
        if missing_case_ids:
            raise KeyError(f"Test cases not linked to automation test cases: {missing_case_ids}")
        return [auto_mapping[case_id] for case_id in case_ids]

    @staticmethod
    def _extract_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        """从任务快照中恢复 case 顺序。"""
        return [case["case_id"] for case in payload.get("cases", [])]

    @staticmethod
    def _extract_auto_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        """从任务快照中恢复 auto_case_id 顺序。"""
        return [case["auto_case_id"] for case in payload.get("cases", []) if "auto_case_id" in case]

    @staticmethod
    def _extract_script_entity_ids_from_payload(payload: Dict[str, Any]) -> List[str | None]:
        """从任务快照中恢复 script_entity_id 顺序。"""
        return [case.get("script_entity_id") for case in payload.get("cases", [])]

    @staticmethod
    def _extract_case_configs_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从任务快照中恢复 case config 顺序。"""
        return [dict(case.get("config") or {}) for case in payload.get("cases", [])]

    @staticmethod
    def _extract_case_payloads_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从任务快照中恢复执行端 case 载荷顺序。"""
        return [
            {
                "case_id": case.get("payload_case_id"),
                "case_path": case.get("case_path"),
                "case_name": case.get("case_name"),
                "parameters": dict(case.get("parameters") or {}),
            }
            for case in payload.get("cases", [])
        ]

    async def _resolve_task_case_pairs(
        self,
        task_doc: ExecutionTaskDoc,
    ) -> tuple[List[str], List[str], List[str | None], List[Dict[str, Any]], List[Dict[str, Any]]]:
        case_ids = self._extract_case_ids_from_payload(task_doc.request_payload)
        auto_case_ids = self._extract_auto_case_ids_from_payload(task_doc.request_payload)
        script_entity_ids = self._extract_script_entity_ids_from_payload(task_doc.request_payload)
        case_configs = self._extract_case_configs_from_payload(task_doc.request_payload)
        case_payloads = self._extract_case_payloads_from_payload(task_doc.request_payload)
        if not auto_case_ids or len(auto_case_ids) != len(case_ids):
            auto_case_ids = await self.resolve_auto_case_ids_by_case_ids(case_ids)
        if not script_entity_ids or len(script_entity_ids) != len(case_ids):
            script_entity_ids = [None] * len(case_ids)
        if not case_configs or len(case_configs) != len(case_ids):
            case_configs = [{} for _ in case_ids]
        if not case_payloads or len(case_payloads) != len(case_ids):
            case_payloads = [{} for _ in case_ids]
        if any(script_entity_id is None for script_entity_id in script_entity_ids):
            auto_docs = await AutomationTestCaseDoc.find({
                "dml_manual_case_id": {"$in": case_ids},
                "is_deleted": False,
            }).to_list()
            script_mapping = {
                doc.dml_manual_case_id: getattr(getattr(doc, "script_ref", None), "entity_id", None)
                for doc in auto_docs
            }
            script_entity_ids = [script_entity_id or script_mapping.get(case_id) for case_id, script_entity_id in zip(case_ids, script_entity_ids)]
        return case_ids, auto_case_ids, script_entity_ids, case_configs, case_payloads

    @staticmethod
    def _build_case_snapshot(
        case_doc: TestCaseDoc,
        auto_case_id: str | None,
        script_entity_id: str | None = None,
        case_config: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """构建任务侧静态 case 快照。"""
        return {
            "case_id": case_doc.case_id,
            "auto_case_id": auto_case_id,
            "script_entity_id": script_entity_id,
            "config": dict(case_config or {}),
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
        case_configs: List[Dict[str, Any]],
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
        _, script_entity_ids = await cls.resolve_case_bindings_by_auto_case_ids(auto_case_ids)
        script_entity_id_map = {
            case_id: script_entity_id
            for case_id, script_entity_id in zip(case_ids, script_entity_ids)
        }

        for order_no, case_id in enumerate(case_ids):
            case_doc = doc_map[case_id]
            snapshot = cls._build_case_snapshot(
                case_doc,
                auto_case_id=auto_case_id_map.get(case_id),
                script_entity_id=script_entity_id_map.get(case_id),
                case_config=case_configs[order_no] if order_no < len(case_configs) else {},
            )
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
