from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _line_count(relative_path: str) -> int:
    return sum(1 for _ in (ROOT / relative_path).read_text().splitlines())


def test_workflow_service_facade_stays_small() -> None:
    assert _line_count("app/modules/workflow/service/workflow_service.py") <= 220


def test_workflow_api_aggregator_stays_small() -> None:
    assert _line_count("app/modules/workflow/api/routes.py") <= 120


def test_auth_api_aggregator_stays_small() -> None:
    assert _line_count("app/modules/auth/api/routes.py") <= 120
