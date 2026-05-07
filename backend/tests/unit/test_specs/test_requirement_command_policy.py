from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.application import CreateRequirementCommand  # noqa: E402
from app.modules.test_specs.application.requirement_command_service import (  # noqa: E402
    RequirementCommandService,
)
from app.modules.workflow.application import OperationContext  # noqa: E402
from app.modules.workflow.domain.exceptions import PermissionDeniedError  # noqa: E402


class _FakeRequirementService:
    def __init__(self) -> None:
        self.created_payloads: list[dict] = []

    async def create_requirement(self, payload: dict) -> dict:
        self.created_payloads.append(payload)
        return {"req_id": "REQ-1", **payload}


def test_non_tpm_cannot_create_requirement() -> None:
    requirement_service = _FakeRequirementService()
    service = RequirementCommandService(
        requirement_service=requirement_service,
        workflow_command_service=object(),
    )

    with pytest.raises(PermissionDeniedError):
        asyncio.run(
            service.create_requirement(
                OperationContext(actor_id="qa-1", role_ids=["ROLE_QA"]),
                CreateRequirementCommand(payload={"title": "demo"}),
            )
        )

    assert requirement_service.created_payloads == []


def test_tpm_can_create_requirement_and_defaults_owner() -> None:
    requirement_service = _FakeRequirementService()
    service = RequirementCommandService(
        requirement_service=requirement_service,
        workflow_command_service=object(),
    )

    result = asyncio.run(
        service.create_requirement(
            OperationContext(actor_id="tpm-1", role_ids=["ROLE_TPM"]),
            CreateRequirementCommand(payload={"title": "demo"}),
        )
    )

    assert result["req_id"] == "REQ-1"
    assert result["tpm_owner_id"] == "tpm-1"
    assert requirement_service.created_payloads == [{"title": "demo", "tpm_owner_id": "tpm-1"}]
