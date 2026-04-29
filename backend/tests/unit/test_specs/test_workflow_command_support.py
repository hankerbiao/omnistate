from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.application._workflow_command_support import (  # noqa: E402
    ensure_authorized_entity,
)
from app.modules.workflow.application import OperationContext  # noqa: E402
from app.modules.workflow.domain.exceptions import PermissionDeniedError  # noqa: E402


class _MissingEntityError(Exception):
    pass


async def _get_entity(_entity_id: str) -> dict[str, str]:
    return {"id": "entity-1", "workflow_item_id": "wi-1", "owner_id": "u-1"}


async def _get_work_item(work_item_id: str) -> dict[str, str]:
    return {"id": work_item_id, "current_owner_id": "u-1"}


def _allow_owner(actor: dict[str, Any], entity: dict, work_item: dict | None) -> bool:
    return actor["actor_id"] == entity["owner_id"] and work_item is not None


def _deny(_actor: dict[str, Any], _entity: dict, _work_item: dict | None) -> bool:
    return False


def test_ensure_authorized_entity_returns_entity_and_workflow_id() -> None:
    entity, workflow_item_id = asyncio.run(
        ensure_authorized_entity(
            context=OperationContext(actor_id="u-1", role_ids=[]),
            entity_id="entity-1",
            getter=_get_entity,
            error_cls=_MissingEntityError,
            checker=_allow_owner,
            action="update entity",
            workflow_getter=_get_work_item,
        )
    )

    assert entity["id"] == "entity-1"
    assert workflow_item_id == "wi-1"


def test_ensure_authorized_entity_rejects_permission_denied() -> None:
    try:
        asyncio.run(
            ensure_authorized_entity(
                context=OperationContext(actor_id="u-2", role_ids=[]),
                entity_id="entity-1",
                getter=_get_entity,
                error_cls=_MissingEntityError,
                checker=_deny,
                action="update entity",
                workflow_getter=_get_work_item,
            )
        )
    except PermissionDeniedError:
        return

    raise AssertionError("expected PermissionDeniedError")
