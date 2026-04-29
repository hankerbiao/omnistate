"""执行任务 case 协调器。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.execution.application.case_resolver import AutoCaseDispatchBinding, ExecutionCaseResolver
from app.modules.execution.repository.models import ExecutionTaskCaseDoc, ExecutionTaskDoc
from app.modules.test_specs.repository.models import TestCaseDoc


class ExecutionTaskCaseCoordinator:
    """处理 case 载入、解析与快照重建。"""

    def __init__(self, case_resolver: ExecutionCaseResolver | None = None) -> None:
        self._case_resolver = case_resolver or ExecutionCaseResolver()

    @staticmethod
    async def load_case_docs(case_ids: List[str]) -> Dict[str, Any]:
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

    async def resolve_case_dispatch_bindings_by_auto_case_ids(
        self,
        auto_case_ids: List[str],
    ) -> List[AutoCaseDispatchBinding]:
        return await self._case_resolver.resolve_case_dispatch_bindings_by_auto_case_ids(auto_case_ids)

    async def resolve_auto_case_ids_by_case_ids(self, case_ids: List[str]) -> List[str]:
        return await self._case_resolver.resolve_auto_case_ids_by_case_ids(case_ids)

    @staticmethod
    def extract_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        """从任务快照中恢复 case 顺序。"""
        return [case["case_id"] for case in payload["cases"]]

    @staticmethod
    def extract_auto_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        """从任务快照中恢复 auto_case_id 顺序。"""
        return [case["auto_case_id"] for case in payload["cases"]]

    @staticmethod
    def extract_script_entity_ids_from_payload(payload: Dict[str, Any]) -> List[str | None]:
        """从任务快照中恢复 script_entity_id 顺序。"""
        return [case["script_entity_id"] for case in payload["cases"]]

    @staticmethod
    def extract_case_configs_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从任务快照中恢复 case config 顺序。"""
        return [dict(case["config"]) for case in payload["cases"]]

    @staticmethod
    def extract_case_payloads_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从任务快照中恢复执行端 case 载荷顺序。"""
        return [
            {
                "case_id": case["payload_case_id"],
                "script_path": case["script_path"],
                "script_name": case["script_name"],
                "parameters": dict(case["parameters"]),
                "attachments": list(case.get("attachments", [])),
            }
            for case in payload["cases"]
        ]

    async def resolve_task_case_pairs(
        self,
        task_doc: ExecutionTaskDoc,
    ) -> tuple[List[str], List[str], List[str | None], List[Dict[str, Any]], List[Dict[str, Any]]]:
        case_ids = self.extract_case_ids_from_payload(task_doc.request_payload)
        auto_case_ids = self.extract_auto_case_ids_from_payload(task_doc.request_payload)
        script_entity_ids = self.extract_script_entity_ids_from_payload(task_doc.request_payload)
        case_configs = self.extract_case_configs_from_payload(task_doc.request_payload)
        case_payloads = self.extract_case_payloads_from_payload(task_doc.request_payload)
        if len(auto_case_ids) != len(case_ids):
            raise ValueError("request_payload cases auto_case_id length mismatch")
        if len(script_entity_ids) != len(case_ids):
            raise ValueError("request_payload cases script_entity_id length mismatch")
        if len(case_configs) != len(case_ids):
            raise ValueError("request_payload cases config length mismatch")
        if len(case_payloads) != len(case_ids):
            raise ValueError("request_payload cases payload length mismatch")
        return case_ids, auto_case_ids, script_entity_ids, case_configs, case_payloads

    @staticmethod
    def build_case_snapshot(
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
            "config": dict(case_config),
            "ref_req_id": case_doc.ref_req_id,
            "title": case_doc.title,
            "version": case_doc.version,
            "status": getattr(case_doc, "status", "draft"),
            "priority": case_doc.priority,
            "tags": list(case_doc.tags),
            "test_category": case_doc.test_category,
            "estimated_duration_sec": case_doc.estimated_duration_sec,
            "required_env": dict(case_doc.required_env),
            "is_destructive": case_doc.is_destructive,
            "pre_condition": case_doc.pre_condition,
            "post_condition": case_doc.post_condition,
            "custom_fields": dict(case_doc.custom_fields),
            "attachments": list(case_doc.attachments),
        }

    async def replace_task_case_docs(
        self,
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
        dispatch_bindings = await self.resolve_case_dispatch_bindings_by_auto_case_ids(auto_case_ids)
        script_entity_id_map = {
            binding.case_id: binding.script_entity_id
            for binding in dispatch_bindings
        }

        for order_no, case_id in enumerate(case_ids):
            case_doc = doc_map[case_id]
            snapshot = self.build_case_snapshot(
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
