"""
工作流领域规则

只包含业务语义逻辑，不依赖 HTTP/数据库。
"""
from typing import Any, Dict, Iterable, Optional

from app.modules.workflow.domain.exceptions import MissingRequiredFieldError
from app.modules.workflow.repository.models import OwnerStrategy


def ensure_required_fields(required_fields: Iterable[str], form_data: Dict[str, Any]) -> None:
    """确保表单中包含所有必填字段。"""
    for field in required_fields:
        if field not in form_data:
            raise MissingRequiredFieldError(field)


def build_process_payload(required_fields: Iterable[str], form_data: Dict[str, Any]) -> Dict[str, Any]:
    """提取流程处理所需的 payload，保留必填字段及 remark。"""
    payload = {field: form_data[field] for field in required_fields}
    if "remark" in form_data and form_data["remark"] is not None:
        payload["remark"] = form_data["remark"]
    return payload


def resolve_owner(
    strategy: str,
    work_item: Dict[str, Any],
    form_data: Dict[str, Any],
) -> Optional[int]:
    """
    根据处理人策略计算新的处理人。

    策略：
    - KEEP：保持当前处理人不变
    - TO_CREATOR：设置为创建人
    - TO_SPECIFIC_USER：设置为表单中传入的 target_owner_id
    """
    if strategy == OwnerStrategy.TO_CREATOR.value:
        return work_item["creator_id"]
    if strategy == OwnerStrategy.TO_SPECIFIC_USER.value:
        target_owner_id = form_data.get("target_owner_id")
        if not target_owner_id:
            raise MissingRequiredFieldError("target_owner_id")
        return target_owner_id
    return work_item.get("current_owner_id")


def normalize_sort(order_by: str, direction: str) -> str:
    """规范化排序字段与方向，返回 Mongo/Beanie sort 表达式。"""
    allowed_fields = {"created_at": "created_at", "updated_at": "updated_at", "title": "title"}
    field = allowed_fields.get(order_by, "created_at")
    prefix = "-" if direction.lower() == "desc" else ""
    return f"{prefix}{field}"
