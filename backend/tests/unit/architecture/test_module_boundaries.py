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
    imports = _module_imports("app/modules/workflow/application/mutation_service.py")

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

    assert "ExecutionService" not in source


def test_progress_coordinator_does_not_instantiate_execution_service_directly() -> None:
    source = (ROOT / "app/modules/execution/application/progress_coordinator.py").read_text()

    assert "ExecutionService" not in source


def test_task_scheduler_does_not_instantiate_execution_service_directly() -> None:
    source = (ROOT / "app/modules/execution/service/task_scheduler.py").read_text()

    assert "ExecutionService" not in source


def test_workflow_api_dependencies_do_not_access_private_service_members() -> None:
    source = (ROOT / "app/modules/workflow/api/dependencies.py").read_text()

    assert "._query_service" not in source
    assert "._mutation_service" not in source


def test_execution_helpers_do_not_call_private_dispatch_methods_across_services() -> None:
    progress_source = (ROOT / "app/modules/execution/application/progress_coordinator.py").read_text()
    scheduler_source = (ROOT / "app/modules/execution/service/task_scheduler.py").read_text()

    assert "._build_task_dispatch_command" not in progress_source
    assert "._dispatch_existing_task" not in progress_source
    assert "._build_task_dispatch_command" not in scheduler_source
    assert "._dispatch_existing_task" not in scheduler_source


def test_execution_task_command_service_uses_case_resolver_collaborator() -> None:
    source = (ROOT / "app/modules/execution/application/task_command_service.py").read_text()

    assert "ExecutionTaskCaseMixin" not in source
    assert "ExecutionCaseResolver" in source


def test_execution_dispatch_service_uses_serializer_collaborator() -> None:
    source = (ROOT / "app/modules/execution/application/task_dispatch_service.py").read_text()

    assert "ExecutionTaskQueryMixin" not in source
    assert "ExecutionTaskSerializer" in source


def test_execution_dispatch_service_uses_dispatch_coordinator() -> None:
    source = (ROOT / "app/modules/execution/application/task_dispatch_service.py").read_text()

    assert "ExecutionTaskDispatchMixin" not in source
    assert "ExecutionTaskDispatchCoordinator" in source


def test_execution_dispatch_service_uses_case_coordinator() -> None:
    source = (ROOT / "app/modules/execution/application/task_dispatch_service.py").read_text()

    assert "ExecutionTaskCaseMixin" not in source
    assert "ExecutionTaskCaseCoordinator" in source


def test_terminal_routes_do_not_hold_module_level_terminal_service_singleton() -> None:
    source = (ROOT / "app/modules/terminal/api/routes.py").read_text()

    assert "terminal_service = TerminalService()" not in source


def test_auth_routes_do_not_depend_on_rbac_service_facade() -> None:
    route_files = [
        "app/modules/auth/api/routes_login.py",
        "app/modules/auth/api/routes_users.py",
        "app/modules/auth/api/routes_roles.py",
        "app/modules/auth/api/routes_permissions.py",
        "app/modules/auth/api/routes_navigation.py",
    ]

    for relative_path in route_files:
        source = (ROOT / relative_path).read_text()
        assert "RbacServiceDep" not in source
        assert "RbacService" not in source


def test_test_specs_routes_do_not_depend_on_workflow_service_facade() -> None:
    route_files = [
        "app/modules/test_specs/api/test_required_routes.py",
        "app/modules/test_specs/api/test_case_routes.py",
    ]

    for relative_path in route_files:
        source = (ROOT / relative_path).read_text()
        assert "AsyncWorkflowService" not in source
        assert "AsyncWorkflowServiceAdapter" not in source


def test_workflow_command_service_does_not_use_facade_union_or_hasattr_dispatch() -> None:
    source = (ROOT / "app/modules/workflow/application/workflow_command_service.py").read_text()

    assert "AsyncWorkflowService" not in source
    assert "| WorkflowMutationService" not in source
    assert "hasattr(" not in source


def test_removed_facade_modules_do_not_exist() -> None:
    removed_paths = [
        "app/modules/workflow/service/workflow_service.py",
        "app/modules/execution/application/execution_service.py",
        "app/modules/auth/service/rbac_service.py",
    ]

    for relative_path in removed_paths:
        assert not (ROOT / relative_path).exists()


def test_application_exports_do_not_expose_removed_facades_or_adapters() -> None:
    workflow_application = (ROOT / "app/modules/workflow/application/__init__.py").read_text()
    execution_application = (ROOT / "app/modules/execution/application/__init__.py").read_text()
    auth_services = (ROOT / "app/modules/auth/service/__init__.py").read_text()

    assert "AsyncWorkflowServiceAdapter" not in workflow_application
    assert "ExecutionService" not in execution_application
    assert "RbacService" not in auth_services


def test_test_specs_projection_hook_only_handles_delete_side_effects() -> None:
    source = (ROOT / "app/modules/test_specs/application/workflow_projection_hook.py").read_text()

    assert "def after_transition" not in source


def test_test_specs_command_services_use_authorized_entity_helper() -> None:
    command_service_files = [
        "app/modules/test_specs/application/requirement_command_service.py",
        "app/modules/test_specs/application/test_case_command_service.py",
    ]

    for relative_path in command_service_files:
        source = (ROOT / relative_path).read_text()
        assert "ensure_authorized_entity" in source
        assert "ensure_permission(" not in source


# ============================================================
#  架构守护：分层依赖规则
# ============================================================


_ALLOWED_CROSS_MODULE_REPO_IMPORTS: dict[str, set[str]] = {
    # ── test_specs ──────────────────────────────────────────
    "app/modules/test_specs/service/_service_support.py": {"app.modules.workflow.repository.models"},
    "app/modules/test_specs/service/_workflow_status_support.py": {
        "app.modules.workflow.repository.models",
        "app.modules.auth.repository.models",
    },
    "app/modules/test_specs/service/change_log_service.py": {"app.modules.auth.repository.models"},
    "app/modules/test_specs/service/requirement_service.py": {"app.modules.auth.repository.models"},
    "app/modules/test_specs/service/test_case_service.py": {
        "app.modules.workflow.repository.models",
        "app.modules.attachments.repository.models",
    },
    "app/modules/test_specs/domain/policies.py": {"app.modules.workflow.repository.models"},
    # ── workflow ────────────────────────────────────────────
    "app/modules/workflow/application/common.py": {"app.modules.test_specs.repository.models"},
    # ── execution ───────────────────────────────────────────
    "app/modules/execution/application/case_resolver.py": {"app.modules.test_specs.repository.models"},
    "app/modules/execution/service/task_scheduler.py": {"app.modules.execution.repository.models"},
    "app/modules/execution/application/task_case_coordinator.py": {"app.modules.test_specs.repository.models"},
    # ── execution_plan ─────────────────────────────────────
    "app/modules/execution_plan/service/execution_plan_service.py": {
        "app.modules.execution.repository.models",
        "app.modules.test_specs.repository.models",
    },
    # ── failure_analysis ────────────────────────────────────
    "app/modules/failure_analysis/service/failure_analysis_service.py": {"app.modules.execution.repository.models"},
    # ── lineage ──────────────────────────────────────────────
    "app/modules/lineage/service/lineage_service.py": {
        "app.modules.execution.repository.models",
        "app.modules.test_specs.repository.models",
    },
    # ── search ───────────────────────────────────────────────
    "app/modules/search/service/search_service.py": {
        "app.modules.execution.repository.models",
        "app.modules.test_specs.repository.models",
    },
    # ── terminal ─────────────────────────────────────────────
    "app/modules/terminal/api/routes.py": {"app.modules.auth.repository.models"},
    # ── ai_analysis ──────────────────────────────────────────
    "app/modules/ai_analysis/service/ai_service.py": {
        "app.modules.test_case_collection.repository.models",
        "app.modules.test_specs.repository.models",
    },
}

# API 层允许跨模块读 repository 的例外清单（应尽可能少）
_API_ALLOWED_REPO_IMPORTS: set[str] = {
    "app/modules/terminal/api/routes.py",
}


def _is_allowed_repo_import(file_path: str, import_module: str) -> bool:
    """检查一个跨模块 repository 导入是否在允许清单中（前缀匹配）。"""
    allowed = _ALLOWED_CROSS_MODULE_REPO_IMPORTS.get(file_path, set())
    for prefix in allowed:
        if import_module == prefix or import_module.startswith(prefix + "."):
            return True
    return False


def test_api_modules_do_not_import_repository_models_directly() -> None:
    """API 层不应直接导入 repository/models（有少量例外需加入 _API_ALLOWED_REPO_IMPORTS）。"""
    api_dirs = sorted((ROOT / "app/modules").glob("*/api/"))
    violations: list[str] = []

    for api_dir in api_dirs:
        for pyfile in sorted(api_dir.rglob("*.py")):
            relative = pyfile.relative_to(ROOT).as_posix()
            if relative in _API_ALLOWED_REPO_IMPORTS:
                continue
            imports = _module_imports(relative)
            for imp in imports:
                if ".repository.models" in imp or ".repository.models." in imp:
                    violations.append(f"{relative} → {imp}")

    assert not violations, (
        f"API 模块不应直接导入 repository/models 文档模型。"
        f"发现 {len(violations)} 个违规:\n" + "\n".join(violations)
    )


def test_domain_modules_do_not_import_api_or_service_or_infrastructure() -> None:
    """Domain 层不应依赖 API、Service 或 Infrastructure。"""
    domain_dirs = sorted((ROOT / "app/modules").glob("*/domain/"))
    violations: list[str] = []

    forbidden_prefixes = (".api.", ".service.", ".infrastructure.")

    for domain_dir in domain_dirs:
        for pyfile in sorted(domain_dir.rglob("*.py")):
            if pyfile.name == "__init__.py":
                continue
            relative = pyfile.relative_to(ROOT).as_posix()
            imports = _module_imports(relative)
            for imp in imports:
                if any(fp in imp for fp in forbidden_prefixes):
                    violations.append(f"{relative} → {imp}")

    assert not violations, (
        f"Domain 层不应导入 API/Service/Infrastructure。"
        f"发现 {len(violations)} 个违规:\n" + "\n".join(violations)
    )


def test_cross_module_repository_imports_are_documented() -> None:
    """跨模块的 repository 直接导入必须有显式的白名单条目。"""
    modules_root = ROOT / "app/modules"
    violations: list[str] = []

    for module_dir in sorted(modules_root.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("_"):
            continue
        for pyfile in sorted(module_dir.rglob("*.py")):
            relative = pyfile.relative_to(ROOT).as_posix()
            imports = _module_imports(relative)
            cross_module_repo_imports = [
                imp for imp in imports
                if "repository.models" in imp
                and not imp.startswith(f"app.modules.{module_dir.name}.")
            ]
            if not cross_module_repo_imports:
                continue

            for imp in cross_module_repo_imports:
                if not _is_allowed_repo_import(relative, imp):
                    violations.append(f"{relative} → {imp} (未在白名单中)")

    assert not violations, (
        f"发现未建档的跨模块 repository 导入。"
        f"请将合法导入添加到 _ALLOWED_CROSS_MODULE_REPO_IMPORTS 白名单，"
        f"并优先考虑通过 Application 端口访问。\n" + "\n".join(violations)
    )


def test_module_document_models_exported_consistently() -> None:
    """每个有 Beanie 文档的模块都应通过 DOCUMENT_MODELS 导出。"""
    modules_root = ROOT / "app/modules"

    for module_dir in sorted(modules_root.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("_"):
            continue
        models_init = module_dir / "repository/models/__init__.py"
        if not models_init.exists():
            continue

        source = models_init.read_text()
        # 检查是否定义了 DOCUMENT_MODELS
        assert "DOCUMENT_MODELS" in source, (
            f"{models_init.relative_to(ROOT)} 应导出 DOCUMENT_MODELS 列表"
        )
        # 检查 DOCUMENT_MODELS 是否为非空列表
        lines = source.splitlines()
        doc_models_lines = [
            i for i, line in enumerate(lines)
            if "DOCUMENT_MODELS" in line and "=" in line
        ]
        assert len(doc_models_lines) > 0, (
            f"{models_init.relative_to(ROOT)} 需要定义 DOCUMENT_MODELS"
        )
