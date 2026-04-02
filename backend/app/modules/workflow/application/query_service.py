from __future__ import annotations

import re
from typing import Any

from beanie import PydanticObjectId
from pymongo.errors import OperationFailure

from app.modules.workflow.application.common import (
    base_item_query,
    docs_to_dicts,
    serialize_work_item,
    validate_object_id,
)
from app.modules.workflow.domain.exceptions import WorkItemNotFoundError
from app.modules.workflow.domain.rules import normalize_sort
from app.modules.workflow.repository.models import (
    BusFlowLogDoc,
    BusWorkItemDoc,
    SysWorkflowConfigDoc,
    SysWorkflowStateDoc,
    SysWorkTypeDoc,
)
from app.shared.core.logger import log as logger


class WorkflowQueryService:
    async def get_work_types(self) -> list[dict[str, Any]]:
        docs = await SysWorkTypeDoc.find_all().to_list()
        return [doc.model_dump() for doc in docs]

    async def get_workflow_states(self) -> list[dict[str, Any]]:
        docs = await SysWorkflowStateDoc.find_all().to_list()
        return [doc.model_dump() for doc in docs]

    async def get_workflow_configs(self, type_code: str) -> list[dict[str, Any]]:
        docs = await SysWorkflowConfigDoc.find(SysWorkflowConfigDoc.type_code == type_code).to_list()
        results: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.model_dump()
            data["id"] = str(doc.id)
            results.append(data)
        return results

    async def list_items(
        self,
        type_code: str | None = None,
        state: str | None = None,
        owner_id: str | None = None,
        creator_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = base_item_query(type_code, state, owner_id, creator_id)
        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return docs_to_dicts(docs)

    async def list_items_sorted(
        self,
        type_code: str | None = None,
        state: str | None = None,
        owner_id: str | None = None,
        creator_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "created_at",
        direction: str = "desc",
    ) -> list[dict[str, Any]]:
        query = base_item_query(type_code, state, owner_id, creator_id)
        docs = await query.sort(normalize_sort(order_by, direction)).skip(offset).limit(limit).to_list()
        return docs_to_dicts(docs)

    async def search_items(
        self,
        keyword: str,
        type_code: str | None = None,
        state: str | None = None,
        owner_id: str | None = None,
        creator_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        normalized_keyword = keyword.strip()
        if len(normalized_keyword) < 2:
            raise ValueError("keyword length must be at least 2")

        query = base_item_query(type_code, state, owner_id, creator_id).find(
            {"$text": {"$search": normalized_keyword}}
        )
        try:
            docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        except OperationFailure as exc:
            if "text index required" not in str(exc).lower():
                raise
            escaped_keyword = re.escape(normalized_keyword)
            fallback_query = base_item_query(type_code, state, owner_id, creator_id).find(
                {
                    "$or": [
                        {"title": {"$regex": escaped_keyword, "$options": "i"}},
                        {"content": {"$regex": escaped_keyword, "$options": "i"}},
                    ]
                }
            )
            docs = await fallback_query.sort("-created_at").skip(offset).limit(limit).to_list()
        return docs_to_dicts(docs)

    async def get_item_by_id(self, item_id: str) -> dict[str, Any] | None:
        try:
            if validate_object_id(item_id) is None:
                return None
            doc = await BusWorkItemDoc.get(item_id)
            if doc and not doc.is_deleted:
                return serialize_work_item(doc)
        except Exception as exc:
            logger.warning(f"获取事项 {item_id} 时发生错误: {exc}")
        return None

    async def get_logs(self, item_id: str, limit: int = 50) -> list[dict[str, Any]]:
        item = await self.get_item_by_id(item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        docs = await BusFlowLogDoc.find(
            BusFlowLogDoc.work_item_id == PydanticObjectId(item_id)
        ).sort("-created_at").limit(limit).to_list()
        results: list[dict[str, Any]] = []
        for doc in docs:
            data = doc.model_dump()
            data["id"] = str(doc.id)
            data["work_item_id"] = str(doc.work_item_id)
            results.append(data)
        return results

    async def batch_get_logs(self, item_ids: list[str], limit: int = 20) -> dict[str, list[dict[str, Any]]]:
        if not item_ids:
            return {}

        invalid_item_ids: list[str] = []
        object_ids: list[PydanticObjectId] = []
        for item_id in item_ids:
            object_id = validate_object_id(item_id)
            if object_id is None:
                invalid_item_ids.append(item_id)
                continue
            object_ids.append(object_id)

        if invalid_item_ids:
            raise ValueError(f"invalid item_ids: {invalid_item_ids}")
        if not object_ids:
            return {item_id: [] for item_id in item_ids}

        all_logs = await BusFlowLogDoc.find({"work_item_id": {"$in": object_ids}}).sort("-created_at").to_list()
        result: dict[str, list[dict[str, Any]]] = {item_id: [] for item_id in item_ids}
        for log_doc in all_logs:
            work_item_id = str(log_doc.work_item_id)
            if work_item_id in result and len(result[work_item_id]) < limit:
                data = log_doc.model_dump()
                data["id"] = str(log_doc.id)
                data["work_item_id"] = str(log_doc.work_item_id)
                result[work_item_id].append(data)
        return result

    async def get_item_with_transitions(self, item_id: str) -> dict[str, Any]:
        item = await self.get_item_by_id(item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        configs = await SysWorkflowConfigDoc.find(
            SysWorkflowConfigDoc.type_code == item["type_code"],
            SysWorkflowConfigDoc.from_state == item["current_state"],
        ).to_list()
        return {
            "item": item,
            "available_transitions": [
                {
                    "action": config.action,
                    "to_state": config.to_state,
                    "target_owner_strategy": config.target_owner_strategy,
                    "required_fields": config.required_fields,
                }
                for config in configs
            ],
        }

    async def list_test_cases_for_requirement(self, requirement_id: str) -> list[dict[str, Any]]:
        requirement = await self.get_item_by_id(requirement_id)
        if not requirement or requirement.get("type_code") != "REQUIREMENT":
            raise WorkItemNotFoundError(requirement_id)

        docs = await BusWorkItemDoc.find(
            {"is_deleted": False},
            BusWorkItemDoc.type_code == "TEST_CASE",
            BusWorkItemDoc.parent_item_id == PydanticObjectId(requirement_id),
        ).sort("-created_at").to_list()
        return docs_to_dicts(docs)

    async def get_requirement_for_test_case(self, test_case_id: str) -> dict[str, Any] | None:
        doc = await BusWorkItemDoc.get(test_case_id)
        if not doc or doc.is_deleted or doc.type_code != "TEST_CASE":
            return None
        if not doc.parent_item_id:
            return None
        return await self.get_item_by_id(str(doc.parent_item_id))
