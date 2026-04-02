from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _module_imports(relative_path: str) -> list[str]:
    source = (ROOT / relative_path).read_text()
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    return imports


def test_workflow_service_does_not_depend_on_test_specs_models() -> None:
    imports = _module_imports("app/modules/workflow/service/workflow_service.py")

    assert "app.modules.test_specs.repository.models" not in imports


def test_test_specs_services_do_not_depend_on_workflow_service_implementation() -> None:
    requirement_imports = _module_imports("app/modules/test_specs/service/requirement_service.py")
    test_case_imports = _module_imports("app/modules/test_specs/service/test_case_service.py")
    support_imports = _module_imports("app/modules/test_specs/application/_workflow_command_support.py")

    assert "app.modules.workflow.service.workflow_service" not in requirement_imports
    assert "app.modules.workflow.service.workflow_service" not in test_case_imports
    assert "app.modules.workflow.service.workflow_service" not in support_imports


def test_event_ingest_service_does_not_instantiate_execution_service_directly() -> None:
    source = (ROOT / "app/modules/execution/application/event_ingest_service.py").read_text()

    assert "ExecutionService()" not in source
