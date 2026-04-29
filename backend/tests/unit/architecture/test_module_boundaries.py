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
