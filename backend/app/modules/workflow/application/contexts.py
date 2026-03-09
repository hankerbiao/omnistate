from dataclasses import dataclass, field


@dataclass(slots=True)
class OperationContext:
    actor_id: str
    role_ids: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    request_id: str | None = None
