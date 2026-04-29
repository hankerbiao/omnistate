from __future__ import annotations

import ast
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parent

GENERATED_PATH_MARKERS = (
    "/__pycache__/",
    "/.pytest_cache/",
    "/.ruff_cache/",
    "/.mypy_cache/",
    "/.pyright/",
    "/node_modules/",
    "/.vitepress/cache/",
    "/.vitepress/dist/",
)
GENERATED_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".log",
    ".coverage",
    ".DS_Store",
)

API_CROSS_MODULE_MODEL_EXCEPTIONS = {
    # Terminal resolves the authenticated user document in its websocket/API boundary today.
    (
        "app/modules/terminal/api/routes.py",
        "app.modules.auth.repository.models",
    ),
}


def _tracked_backend_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "backend"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.splitlines()


def _python_files(*roots: str) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        files.extend(sorted((ROOT / root).rglob("*.py")))
    return files


def _imports_for(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    return imports


def test_generated_or_local_artifacts_are_not_tracked() -> None:
    offenders = []
    for path in _tracked_backend_files():
        normalized = "/" + path
        if any(marker in normalized for marker in GENERATED_PATH_MARKERS):
            offenders.append(path)
        elif path.endswith(GENERATED_SUFFIXES):
            offenders.append(path)

    assert offenders == []


def test_removed_message_manager_compatibility_wrappers_do_not_exist() -> None:
    removed_paths = [
        ROOT / "app/shared/kafka/kafka_message_manager.py",
        ROOT / "app/shared/rabbitmq/rabbitmq_message_manager.py",
    ]

    for path in removed_paths:
        assert not path.exists()


def test_api_cross_module_model_imports_are_explicit_exceptions() -> None:
    violations = []
    for path in _python_files("app/modules"):
        relative_path = path.relative_to(ROOT).as_posix()
        parts = relative_path.split("/")
        if len(parts) < 5 or parts[3] != "api":
            continue

        current_module = parts[2]
        for imported in _imports_for(path):
            if not imported.startswith("app.modules."):
                continue
            imported_parts = imported.split(".")
            if len(imported_parts) < 5:
                continue
            imported_module = imported_parts[2]
            is_model_import = imported_parts[3:5] == ["repository", "models"]
            is_cross_module = imported_module != current_module
            if (
                is_model_import
                and is_cross_module
                and (relative_path, imported) not in API_CROSS_MODULE_MODEL_EXCEPTIONS
            ):
                violations.append((relative_path, imported))

    assert violations == []


def test_api_aggregator_files_stay_small() -> None:
    aggregators = [
        ROOT / "app/shared/api/main.py",
        ROOT / "app/modules/workflow/api/routes.py",
        ROOT / "app/modules/auth/api/routes.py",
    ]

    for path in aggregators:
        line_count = len(path.read_text().splitlines())
        assert line_count <= 120, f"{path.relative_to(ROOT)} has {line_count} lines"


def test_redundancy_governance_document_exists() -> None:
    doc = ROOT / "docs/handover/backend-redundancy-governance-review.md"
    text = doc.read_text()

    assert "Classification Rules" in text
    assert "Standing Architecture Rules" in text
    assert "Review Procedure" in text
