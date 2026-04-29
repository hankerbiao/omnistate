"""执行任务 case 解析与快照能力。

保留为兼容桥接，实际实现已迁移到 `ExecutionTaskCaseCoordinator`。
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.execution.application.case_resolver import AutoCaseDispatchBinding, ExecutionCaseResolver
from app.modules.execution.application.task_case_coordinator import ExecutionTaskCaseCoordinator
from app.modules.execution.repository.models import ExecutionTaskDoc


class ExecutionTaskCaseMixin:
    """处理 case 解析、快照与当前态重建。"""

    @staticmethod
    async def _load_case_docs(case_ids: List[str]) -> Dict[str, Any]:
        return await ExecutionTaskCaseCoordinator.load_case_docs(case_ids)

    @staticmethod
    async def resolve_case_dispatch_bindings_by_auto_case_ids(
        auto_case_ids: List[str],
    ) -> List[AutoCaseDispatchBinding]:
        return await ExecutionCaseResolver().resolve_case_dispatch_bindings_by_auto_case_ids(auto_case_ids)

    @staticmethod
    async def resolve_auto_case_ids_by_case_ids(case_ids: List[str]) -> List[str]:
        return await ExecutionCaseResolver().resolve_auto_case_ids_by_case_ids(case_ids)

    @staticmethod
    def _extract_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        return ExecutionTaskCaseCoordinator.extract_case_ids_from_payload(payload)

    @staticmethod
    def _extract_auto_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        return ExecutionTaskCaseCoordinator.extract_auto_case_ids_from_payload(payload)

    @staticmethod
    def _extract_script_entity_ids_from_payload(payload: Dict[str, Any]) -> List[str | None]:
        return ExecutionTaskCaseCoordinator.extract_script_entity_ids_from_payload(payload)

    @staticmethod
    def _extract_case_configs_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        return ExecutionTaskCaseCoordinator.extract_case_configs_from_payload(payload)

    @staticmethod
    def _extract_case_payloads_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        return ExecutionTaskCaseCoordinator.extract_case_payloads_from_payload(payload)

    async def _resolve_task_case_pairs(
        self,
        task_doc: ExecutionTaskDoc,
    ) -> tuple[List[str], List[str], List[str | None], List[Dict[str, Any]], List[Dict[str, Any]]]:
        return await ExecutionTaskCaseCoordinator().resolve_task_case_pairs(task_doc)

    @staticmethod
    def _build_case_snapshot(
        case_doc: Any,
        auto_case_id: str | None,
        script_entity_id: str | None = None,
        case_config: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return ExecutionTaskCaseCoordinator.build_case_snapshot(
            case_doc,
            auto_case_id=auto_case_id,
            script_entity_id=script_entity_id,
            case_config=case_config,
        )

    @classmethod
    async def _replace_task_case_docs(
        cls,
        task_id: str,
        case_ids: List[str],
        auto_case_ids: List[str],
        case_configs: List[Dict[str, Any]],
        doc_map: Dict[str, Any],
    ) -> None:
        await ExecutionTaskCaseCoordinator().replace_task_case_docs(
            task_id,
            case_ids,
            auto_case_ids,
            case_configs,
            doc_map,
        )
