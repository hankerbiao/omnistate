from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CreateRequirementCommand:
    payload: dict[str, Any]


@dataclass(slots=True)
class UpdateRequirementCommand:
    req_id: str
    payload: dict[str, Any]


@dataclass(slots=True)
class DeleteRequirementCommand:
    req_id: str


@dataclass(slots=True)
class CreateTestCaseCommand:
    payload: dict[str, Any]


@dataclass(slots=True)
class UpdateTestCaseCommand:
    case_id: str
    payload: dict[str, Any]


@dataclass(slots=True)
class DeleteTestCaseCommand:
    case_id: str


@dataclass(slots=True)
class LinkAutomationCaseCommand:
    case_id: str
    auto_case_id: str
    version: str | None = None


@dataclass(slots=True)
class UnlinkAutomationCaseCommand:
    case_id: str
