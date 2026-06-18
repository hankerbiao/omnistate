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
    from app.modules.attachments.repository.models import DOCUMENT_MODELS as ATTACHMENT_DOCUMENT_MODELS
    from app.modules.auth.repository.models import DOCUMENT_MODELS as AUTH_DOCUMENT_MODELS
    from app.modules.execution.repository.models import DOCUMENT_MODELS as EXECUTION_DOCUMENT_MODELS
    from app.modules.execution_plan.repository.models import DOCUMENT_MODELS as EXECUTION_PLAN_DOCUMENT_MODELS
    from app.modules.test_case_collection.repository.models import DOCUMENT_MODELS as COLLECTION_DOCUMENT_MODELS
    from app.modules.test_specs.repository.models import DOCUMENT_MODELS as TEST_SPECS_DOCUMENT_MODELS
    from app.modules.workflow.repository.models import DOCUMENT_MODELS as WORKFLOW_DOCUMENT_MODELS
    from app.modules.project.repository.models import DOCUMENT_MODELS as PROJECT_DOCUMENT_MODELS
    from app.shared.infrastructure.bootstrap import get_document_models

    expected = [
        *WORKFLOW_DOCUMENT_MODELS,
        *TEST_SPECS_DOCUMENT_MODELS,
        *EXECUTION_DOCUMENT_MODELS,
        *AUTH_DOCUMENT_MODELS,
        *ATTACHMENT_DOCUMENT_MODELS,
        *EXECUTION_PLAN_DOCUMENT_MODELS,
        *COLLECTION_DOCUMENT_MODELS,
        *PROJECT_DOCUMENT_MODELS,
    ]

    assert sorted(get_document_models(), key=str) == sorted(expected, key=str)
