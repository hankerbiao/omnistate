from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _module_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text()


def _class_field_names(relative_path: str, class_name: str) -> set[str]:
    tree = ast.parse(_module_source(relative_path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields: set[str] = set()
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.add(item.target.id)
            return fields
    raise AssertionError(f"class {class_name} not found in {relative_path}")


def test_requirement_document_does_not_define_status_field() -> None:
    fields = _class_field_names(
        "app/modules/test_specs/repository/models/requirement.py",
        "TestRequirementDoc",
    )

    assert "status" not in fields


def test_test_case_document_does_not_define_status_field() -> None:
    fields = _class_field_names(
        "app/modules/test_specs/repository/models/test_case.py",
        "TestCaseDoc",
    )

    assert "status" not in fields


def test_requirement_and_test_case_indexes_do_not_reference_status() -> None:
    requirement_source = _module_source("app/modules/test_specs/repository/models/requirement.py")
    test_case_source = _module_source("app/modules/test_specs/repository/models/test_case.py")

    assert 'IndexModel("status")' not in requirement_source
    assert '[("status", ASCENDING), ("created_at", DESCENDING)]' not in requirement_source
    assert 'IndexModel("status")' not in test_case_source


def test_workflow_projection_hook_does_not_write_status_back_to_projection_docs() -> None:
    source = _module_source("app/modules/test_specs/application/workflow_projection_hook.py")

    assert ".status =" not in source
    assert '["status"] =' not in source
