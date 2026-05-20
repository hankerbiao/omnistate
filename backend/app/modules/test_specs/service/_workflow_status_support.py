from typing import Any, Dict, Iterable, Optional

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
        # 添加工作流创建人和负责人信息
        data["creator"] = work_item.creator_id
        data["current_owner"] = work_item.current_owner_id
    else:
        data["status"] = DEFAULT_PROJECTED_STATUS
    return data


async def enrich_projected_status_with_usernames(
    data: Dict[str, Any],
    user_cache: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """用工作流真实状态补齐业务响应，并尝试获取用户名。

    Args:
        data: 业务实体数据字典
        user_cache: 用户名缓存字典 {user_id: username}，为空时跳过用户名查询
    """
    # 先获取状态和基础信息
    data = await enrich_projected_status(data)

    # 如果有用户缓存，尝试填充用户名
    if user_cache:
        creator = data.get("creator")
        current_owner = data.get("current_owner")
        if creator and creator in user_cache:
            data["creator_name"] = user_cache[creator]
        if current_owner and current_owner in user_cache:
            data["current_owner_name"] = user_cache[current_owner]

    return data


async def get_workflow_states(docs: Iterable[Any], key_attr: str) -> Dict[str, str]:
    """批量读取工作流状态，返回业务主键到 current_state 的映射。"""
    details = await get_workflow_details(docs, key_attr)
    return {k: v["status"] for k, v in details.items()}


async def get_workflow_details(docs: Iterable[Any], key_attr: str) -> Dict[str, Dict[str, Any]]:
    """批量读取工作流详情，返回业务主键到工作流详情的映射。

    返回结构: {entity_id: {status, creator, current_owner, ...}}
    """
    # 构建 workflow_item_id -> entity_id 的映射
    workflow_id_map: Dict[str, str] = {}
    for doc in docs:
        workflow_id = getattr(doc, "workflow_item_id", None)
        entity_id = getattr(doc, key_attr, None)
        if workflow_id and entity_id:
            workflow_id_map[str(workflow_id)] = entity_id

    if not workflow_id_map:
        return {}

    work_items = await BusWorkItemDoc.find({
        "id": {"$in": list(workflow_id_map.keys())},
        "is_deleted": False,
    }).to_list()

    # 构建反向映射: workflow_id -> work_item
    work_item_by_id: Dict[str, Any] = {
        str(work_item.id): work_item
        for work_item in work_items
    }

    result: Dict[str, Dict[str, Any]] = {}
    for workflow_id, entity_id in workflow_id_map.items():
        work_item = work_item_by_id.get(workflow_id)
        if work_item:
            result[entity_id] = {
                "status": work_item.current_state,
                "creator": work_item.creator_id,
                "current_owner": work_item.current_owner_id,
            }

    return result
