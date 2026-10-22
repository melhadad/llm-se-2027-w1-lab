"""Deterministic queue ownership and response deadlines; no model calls."""

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict

from triage.models import COMPONENTS, IssueType, Severity, TriageRecord

Priority = Literal["urgent", "high", "normal", "low"]
POLICY_VERSION = "1"
_TARGETS: dict[Severity, tuple[Priority, int]] = {
    "critical": ("urgent", 1), "high": ("high", 24),
    "medium": ("normal", 72), "low": ("low", 168), "unknown": ("high", 24),
}
_QUEUES: dict[IssueType, str] = {
    "bug": "bugs", "enhancement": "feature-requests", "documentation": "documentation",
    "question": "support", "meta": "maintenance", "unknown": "triage",
}


class RoutingRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    triage: TriageRecord
    queue: str
    priority: Priority
    due_in_hours: int
    received_at: datetime
    due_at: datetime
    policy_version: Literal["1"] = POLICY_VERSION


def normalize_received_at(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("received_at must include a timezone")
    received_at = value.astimezone(timezone.utc)
    # Validate the full policy horizon before any potentially billable work.
    try:
        _ = received_at + timedelta(hours=168)
    except OverflowError as exc:
        raise ValueError("received_at is outside the supported deadline range") from exc
    return received_at


def route_issue(record: TriageRecord, received_at: datetime | None = None) -> RoutingRecord:
    # Revalidate the public boundary, including records created with model_copy.
    record = TriageRecord.model_validate(record.model_dump())
    if record.component is not None and record.component not in COMPONENTS[record.repo]:
        raise ValueError("component is outside the project's taxonomy")
    timestamp = normalize_received_at(received_at if received_at is not None else datetime.now(timezone.utc))
    priority, hours = _TARGETS[record.severity]
    if record.severity == "critical":
        queue = "urgent"
    elif record.issue_type == "unknown" or record.confidence < 0.8:
        queue = "triage"
    elif record.issue_type in ("documentation", "question", "meta"):
        queue = _QUEUES[record.issue_type]
    elif record.component is not None:
        queue = record.component
    else:
        queue = _QUEUES[record.issue_type]
    return RoutingRecord(
        triage=record, queue=f"{record.repo}/{queue}", priority=priority,
        due_in_hours=hours, received_at=timestamp, due_at=timestamp + timedelta(hours=hours),
    )
