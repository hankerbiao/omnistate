"""测试用例字段 diff 工具"""
from __future__ import annotations

import json
from typing import Any

# 参与变更记录的业务字段（不含派生/工作流/系统字段）
TRACKED_FIELDS = frozenset({
    "title",
    "lab_id",
    "catalog_path",
    "ref_req_id",
    "owner_id",
    "reviewer_id",
    "auto_dev_id",
    "version",
    "is_active",
    "change_log",
    "priority",
    "estimated_duration_sec",
    "required_env",
    "tags",
    "test_category",
    "is_destructive",
    "pre_condition",
    "post_condition",
    "risk_level",
    "failure_analysis",
    "confidentiality",
    "visibility_scope",
    "attachments",
    "custom_fields",
    "deprecation_reason",
    "is_deleted",
})

IGNORED_DERIVED_FIELDS = frozenset({
    "catalog_path_key",
    "id",
    "workflow_item_id",
    "status",
    "created_at",
    "updated_at",
    "lab_name",
    "catalog_breadcrumb",
    "approval_history",
})


def _normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda x: x[0])}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return json.loads(json.dumps(value, default=str))


def _values_equal(old: Any, new: Any) -> bool:
    return _normalize(old) == _normalize(new)


def compute_field_changes(
    old_snapshot: dict[str, Any] | None,
    new_snapshot: dict[str, Any],
    tracked_fields: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """计算字段级变更列表。"""
    fields = tracked_fields or TRACKED_FIELDS
    changes: list[dict[str, Any]] = []

    if old_snapshot is None:
        for field in sorted(fields):
            new_value = new_snapshot.get(field)
            if new_value is None or new_value == "" or new_value == [] or new_value == {}:
                continue
            changes.append({
                "field": field,
                "old_value": None,
                "new_value": new_value,
                "change_type": "added",
            })
        return changes

    all_keys = set(fields)
    for field in sorted(all_keys):
        old_value = old_snapshot.get(field)
        new_value = new_snapshot.get(field)
        if _values_equal(old_value, new_value):
            continue
        if old_value is None or old_value == "" or old_value == [] or old_value == {}:
            change_type = "added"
        elif new_value is None or new_value == "" or new_value == [] or new_value == {}:
            change_type = "removed"
        else:
            change_type = "modified"
        changes.append({
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "change_type": change_type,
        })
    return changes
