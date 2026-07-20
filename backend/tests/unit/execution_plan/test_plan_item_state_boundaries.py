"""执行计划条目状态边界测试。

这些测试守住一个设计约束：计划条目的流程状态只能由 PlanCommandService
的明确入口推进，API 路由或核心 CRUD service 不能直接改 status / execution_task_id / result_id。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "app" / "modules" / "execution_plan"
COMMAND_SERVICE = BACKEND_ROOT / "application" / "plan_command_service.py"

PROCESS_FIELDS = {"status", "execution_task_id", "result_id", "result_source"}


def _assigned_plan_item_process_attrs(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    attrs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Attribute):
                    continue
                if target.attr not in PROCESS_FIELDS:
                    continue
                if isinstance(target.value, ast.Name) and target.value.id in {"item", "item_doc"}:
                    attrs.add(target.attr)
    return attrs


def test_plan_item_process_fields_are_only_assigned_in_command_service() -> None:
    offenders: list[str] = []
    for path in BACKEND_ROOT.rglob("*.py"):
        if path == COMMAND_SERVICE:
            continue
        assigned = _assigned_plan_item_process_attrs(path)
        if assigned:
            rel = path.relative_to(ROOT)
            offenders.append(f"{rel}: {sorted(assigned)}")

    assert offenders == [], (
        "计划条目流程字段只能在 PlanCommandService 内更新，"
        "请走 dispatch_plan_item/apply_execution_result/submit_manual_result: "
        + "; ".join(offenders)
    )


def test_command_service_exposes_explicit_process_entrypoints() -> None:
    from app.modules.execution_plan.application.plan_command_service import PlanCommandService

    for method_name in ("dispatch_plan_item", "apply_execution_result", "submit_manual_result"):
        assert callable(getattr(PlanCommandService, method_name, None))

    assert not hasattr(PlanCommandService, "dispatch_item")
    assert not hasattr(PlanCommandService, "submit_result")


@pytest.mark.parametrize("field", PROCESS_FIELDS)
def test_update_item_request_schema_excludes_process_fields(field: str) -> None:
    from app.modules.execution_plan.schemas.execution_plan import UpdatePlanItemRequest

    assert field not in UpdatePlanItemRequest.model_fields
