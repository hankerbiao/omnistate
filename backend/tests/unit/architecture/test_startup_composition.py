from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _imports_for(relative_path: str) -> list[str]:
    tree = ast.parse((ROOT / relative_path).read_text())
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    return imports


def test_main_does_not_own_beanie_model_registration() -> None:
    imports = _imports_for("app/main.py")

    assert "beanie" not in imports
    assert not any(imported.endswith(".repository.models") for imported in imports)
    assert "app.shared.infrastructure.bootstrap" in imports


def test_bootstrap_exports_document_models_in_startup_order() -> None:
    from app.shared.infrastructure.bootstrap import get_document_models

    model_names = [model.__name__ for model in get_document_models()]

    assert model_names == [
        "SysWorkTypeDoc",
        "SysWorkflowStateDoc",
        "SysWorkflowConfigDoc",
        "BusWorkItemDoc",
        "BusFlowLogDoc",
        "TestRequirementDoc",
        "TestCaseDoc",
        "AutomationTestCaseDoc",
        "ExecutionAgentDoc",
        "ExecutionEventDoc",
        "ExecutionTaskDoc",
        "ExecutionTaskCaseDoc",
        "UserDoc",
        "RoleDoc",
        "PermissionDoc",
        "NavigationPageDoc",
        "AttachmentDoc",
    ]
