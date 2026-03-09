from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CreateWorkItemCommand:
    type_code: str
    title: str
    content: str
    parent_item_id: str | None = None


@dataclass(slots=True)
class TransitionWorkItemCommand:
    work_item_id: str
    action: str
    form_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReassignWorkItemCommand:
    work_item_id: str
    target_owner_id: str
    remark: str | None = None


@dataclass(slots=True)
class DeleteWorkItemCommand:
    work_item_id: str
