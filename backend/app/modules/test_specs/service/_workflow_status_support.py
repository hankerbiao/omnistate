from typing import Any, Dict, Iterable

from app.modules.workflow.repository.models.business import BusWorkItemDoc

DEFAULT_PROJECTED_STATUS = "未开始"


async def enrich_projected_status(data: Dict[str, Any]) -> Dict[str, Any]:
    """用工作流真实状态补齐业务响应中的派生状态字段。"""
    workflow_item_id = str(data.get("workflow_item_id") or "").strip()
    if not workflow_item_id:
        data["status"] = DEFAULT_PROJECTED_STATUS
        return data

    work_item = await BusWorkItemDoc.get(workflow_item_id)
    if work_item and not work_item.is_deleted:
        data["status"] = work_item.current_state
    else:
        data["status"] = DEFAULT_PROJECTED_STATUS
    return data


async def get_workflow_states(docs: Iterable[Any], key_attr: str) -> Dict[str, str]:
    """批量读取工作流状态，返回业务主键到 current_state 的映射。"""
    workflow_id_map = {
        getattr(doc, key_attr): doc.workflow_item_id
        for doc in docs
        if getattr(doc, "workflow_item_id", None)
    }
    if not workflow_id_map:
        return {}

    # 先按 workflow_item_id 批量查出工作项，再反向映射回业务实体主键。
    work_items = await BusWorkItemDoc.find({
        "id": {"$in": list(workflow_id_map.values())},
        "is_deleted": False,
    }).to_list()
    state_by_workflow_id = {
        str(work_item.id): work_item.current_state
        for work_item in work_items
    }
    return {
        entity_id: state_by_workflow_id[workflow_id]
        for entity_id, workflow_id in workflow_id_map.items()
        if workflow_id in state_by_workflow_id
    }
