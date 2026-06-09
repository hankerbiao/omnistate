from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.modules.test_specs.schemas import RequirementResponse
from app.modules.test_specs.service.requirement_service import RequirementService


def _fake_requirement_doc() -> SimpleNamespace:
    return SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        model_dump=lambda: {
            "req_id": "TR-2026-00001",
            "workflow_item_id": "wi-1",
            "title": "req",
            "description": None,
            "category": None,
            "tags": [],
            "source": None,
            "acceptance_criteria": None,
            "baseline_version": None,
            "target_version": None,
            "target_components": [],
            "firmware_version": None,
            "priority": "P1",
            "key_parameters": [],
            "risk_points": None,
            "tpm_owner_id": "u-1",
            "tpm_owner_name": None,
            "manual_dev_id": None,
            "manual_dev_name": None,
            "auto_dev_id": None,
            "auto_dev_name": None,
            "case_count": 0,
            "attachments": [],
            "planned_start_date": date(2026, 1, 1),
            "planned_end_date": date(2026, 3, 31),
            "is_deleted": False,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        },
    )


def test_doc_to_dict_serializes_planned_dates_as_strings() -> None:
    data = RequirementService._doc_to_dict(_fake_requirement_doc())

    assert data["planned_start_date"] == "2026-01-01"
    assert data["planned_end_date"] == "2026-03-31"
    RequirementResponse.model_validate({**data, "status": "IN_REVIEW"})
