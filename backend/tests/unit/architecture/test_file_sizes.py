from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_workflow_api_aggregator_stays_small() -> None:
    assert sum(1 for _ in (ROOT / "app/modules/workflow/api/routes.py").read_text().splitlines()) <= 120


def test_auth_api_aggregator_stays_small() -> None:
    assert sum(1 for _ in (ROOT / "app/modules/auth/api/routes.py").read_text().splitlines()) <= 120


def test_execution_plan_api_aggregator_stays_small() -> None:
    routes = ROOT / "app/modules/execution_plan/api/routes.py"
    assert sum(1 for _ in routes.read_text().splitlines()) <= 80


def test_execution_plan_api_route_modules_stay_focused() -> None:
    api_dir = ROOT / "app/modules/execution_plan/api"
    route_modules = sorted(api_dir.glob("routes_*.py"))

    assert route_modules
    oversized = {
        path.name: len(path.read_text().splitlines())
        for path in route_modules
        if len(path.read_text().splitlines()) > 260
    }
    assert oversized == {}


def test_project_services_stay_focused() -> None:
    service_dir = ROOT / "app/modules/project/service"
    limits = {
        "project_service.py": 300,
        "project_dashboard_service.py": 350,
        "project_demo_service.py": 200,
    }
    oversized = {
        filename: len((service_dir / filename).read_text().splitlines())
        for filename, limit in limits.items()
        if len((service_dir / filename).read_text().splitlines()) > limit
    }
    assert oversized == {}
