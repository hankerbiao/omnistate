"""test_case_step_validator 单元测试"""
import pytest

from app.modules.test_specs.domain.test_case_step_validator import (
    validate_test_case_steps,
    validate_test_case_step_fields,
)


def _step(step_id: str = "s1", name: str = "安装内存", action: str = "上电", expected: str = "正常启动"):
    return {
        "step_id": step_id,
        "name": name,
        "action": action,
        "expected": expected,
    }


def test_validate_empty_steps():
    assert validate_test_case_steps([]) == []


def test_validate_normalizes_trim():
    result = validate_test_case_steps([{
        "step_id": " id-1 ",
        "name": " 步骤 ",
        "action": " 动作 ",
        "expected": " 期望 ",
    }])
    assert result == [{
        "step_id": "id-1",
        "name": "步骤",
        "action": "动作",
        "expected": "期望",
    }]


def test_validate_duplicate_step_id():
    with pytest.raises(ValueError, match="duplicate step_id"):
        validate_test_case_steps([_step("dup"), _step("dup", name="第二步")])


def test_validate_required_fields():
    with pytest.raises(ValueError, match="name is required"):
        validate_test_case_steps([_step(name="   ")])


def test_validate_max_steps():
    steps = [_step(f"s{i}") for i in range(101)]
    with pytest.raises(ValueError, match="at most 100"):
        validate_test_case_steps(steps)


def test_validate_payload_fields():
    payload = validate_test_case_step_fields({
        "title": "case",
        "steps": [_step()],
        "cleanup_steps": [],
    })
    assert payload["steps"][0]["name"] == "安装内存"
    assert payload["cleanup_steps"] == []
