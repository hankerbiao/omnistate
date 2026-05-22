"""Status mapping rules for execution events."""

from __future__ import annotations

from app.modules.execution.application.constants import CaseStatus


def resolve_case_status(
    event_type: str,
    phase: str | None,
    event_status: str | None,
    failed_cases: int | None,
) -> str | None:
    """Map execution event into case status."""
    normalized_status = (event_status or "").strip().upper()
    if normalized_status in {CaseStatus.PASSED, CaseStatus.FAILED, CaseStatus.SKIPPED, CaseStatus.RUNNING}:
        return normalized_status

    normalized_type = (event_type or "").strip().lower()
    normalized_phase = (phase or "").strip().lower()
    if normalized_type != "progress":
        return None
    if normalized_phase == "case_start":
        return CaseStatus.RUNNING
    if normalized_phase == "case_finish":
        return CaseStatus.FAILED if (failed_cases or 0) > 0 else CaseStatus.PASSED
    return None
