from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_workflow_api_aggregator_stays_small() -> None:
    assert sum(1 for _ in (ROOT / "app/modules/workflow/api/routes.py").read_text().splitlines()) <= 120


def test_auth_api_aggregator_stays_small() -> None:
    assert sum(1 for _ in (ROOT / "app/modules/auth/api/routes.py").read_text().splitlines()) <= 120
