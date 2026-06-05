"""测试用例步骤校验"""
from __future__ import annotations

from typing import Any

MAX_STEPS_PER_ARRAY = 100
MAX_NAME_LENGTH = 200
MAX_TEXT_LENGTH = 4000


def _step_fields(step: Any) -> tuple[str, str, str, str]:
    if isinstance(step, dict):
        return (
            str(step.get("step_id", "")),
            str(step.get("name", "")),
            str(step.get("action", "")),
            str(step.get("expected", "")),
        )
    return (
        str(getattr(step, "step_id", "")),
        str(getattr(step, "name", "")),
        str(getattr(step, "action", "")),
        str(getattr(step, "expected", "")),
    )


def validate_test_case_steps(
    steps: list[Any] | None,
    *,
    field_name: str = "steps",
) -> list[dict[str, str]]:
    """校验并规范化步骤数组。

    空数组合法；数组内每一步的四字段 trim 后须非空，step_id 须唯一。
    """
    if steps is None:
        return []
    if not isinstance(steps, list):
        raise ValueError(f"{field_name} must be a list")
    if len(steps) > MAX_STEPS_PER_ARRAY:
        raise ValueError(f"{field_name}: at most {MAX_STEPS_PER_ARRAY} steps allowed")

    seen_ids: set[str] = set()
    normalized: list[dict[str, str]] = []
    for index, step in enumerate(steps, start=1):
        step_id, name, action, expected = _step_fields(step)
        step_id = step_id.strip()
        name = name.strip()
        action = action.strip()
        expected = expected.strip()

        if not step_id:
            raise ValueError(f"{field_name}[{index}]: step_id is required")
        if not name:
            raise ValueError(f"{field_name}[{index}]: name is required")
        if not action:
            raise ValueError(f"{field_name}[{index}]: action is required")
        if not expected:
            raise ValueError(f"{field_name}[{index}]: expected is required")
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(f"{field_name}[{index}]: name exceeds {MAX_NAME_LENGTH} characters")
        if len(action) > MAX_TEXT_LENGTH:
            raise ValueError(f"{field_name}[{index}]: action exceeds {MAX_TEXT_LENGTH} characters")
        if len(expected) > MAX_TEXT_LENGTH:
            raise ValueError(f"{field_name}[{index}]: expected exceeds {MAX_TEXT_LENGTH} characters")
        if step_id in seen_ids:
            raise ValueError(f"{field_name}[{index}]: duplicate step_id '{step_id}'")

        seen_ids.add(step_id)
        normalized.append({
            "step_id": step_id,
            "name": name,
            "action": action,
            "expected": expected,
        })
    return normalized


def validate_test_case_step_fields(data: dict[str, Any]) -> dict[str, Any]:
    """校验 payload 中的 steps / cleanup_steps（若提供）。"""
    result = dict(data)
    if "steps" in result:
        result["steps"] = validate_test_case_steps(result["steps"], field_name="steps")
    if "cleanup_steps" in result:
        result["cleanup_steps"] = validate_test_case_steps(
            result["cleanup_steps"],
            field_name="cleanup_steps",
        )
    return result
