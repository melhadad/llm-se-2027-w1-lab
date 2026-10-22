from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from triage import TriageRecord, route_issue

RECEIVED = datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)


def record(**changes: object) -> TriageRecord:
    return TriageRecord.model_validate({
        "repo": "hono", "number": 1, "issue_type": "bug", "component": "middleware",
        "severity": "medium", "has_reproduction_steps": True,
        "summary": "Header failure", "rationale": "Concrete example", "confidence": 0.9,
        "needs_human_review": True, **changes,
    })


@pytest.mark.parametrize(("severity", "priority", "hours"), [
    ("critical", "urgent", 1), ("high", "high", 24), ("medium", "normal", 72),
    ("low", "low", 168), ("unknown", "high", 24),
])
def test_deadlines_are_response_targets(severity: str, priority: str, hours: int) -> None:
    result = route_issue(record(severity=severity), RECEIVED)
    assert result.priority == priority
    assert result.due_in_hours == hours
    assert result.due_at == RECEIVED + timedelta(hours=hours)
    assert result.triage.needs_human_review


@pytest.mark.parametrize(("changes", "queue"), [
    ({}, "hono/middleware"),
    ({"severity": "critical", "confidence": 0.1, "issue_type": "unknown"}, "hono/urgent"),
    ({"confidence": 0.79}, "hono/triage"),
    ({"confidence": 0.8}, "hono/middleware"),
    ({"issue_type": "unknown"}, "hono/triage"),
    ({"issue_type": "documentation"}, "hono/documentation"),
    ({"issue_type": "question"}, "hono/support"),
    ({"issue_type": "meta"}, "hono/maintenance"),
    ({"component": None}, "hono/bugs"),
    ({"issue_type": "enhancement", "component": None}, "hono/feature-requests"),
    ({"repo": "litestar", "component": "openapi"}, "litestar/openapi"),
    ({"repo": "textual", "component": None}, "textual/bugs"),
])
def test_queue_precedence(changes: dict[str, object], queue: str) -> None:
    assert route_issue(record(**changes), RECEIVED).queue == queue


def test_no_reproduction_does_not_reduce_urgency() -> None:
    assert route_issue(record(severity="critical", has_reproduction_steps=False), RECEIVED).queue == "hono/urgent"


def test_timezone_normalization_and_day_boundary() -> None:
    timestamp = datetime(2026, 10, 15, 23, 30, tzinfo=timezone(timedelta(hours=3)))
    result = route_issue(record(severity="critical"), timestamp)
    assert result.received_at == datetime(2026, 10, 15, 20, 30, tzinfo=timezone.utc)
    assert result.due_at == datetime(2026, 10, 15, 21, 30, tzinfo=timezone.utc)
    next_day = route_issue(record(severity="high"), timestamp)
    assert next_day.due_at == datetime(2026, 10, 16, 20, 30, tzinfo=timezone.utc)


def test_invalid_timestamps_and_taxonomy() -> None:
    with pytest.raises(ValueError, match="timezone"):
        route_issue(record(), datetime(2026, 10, 15))
    with pytest.raises(ValueError, match="deadline range"):
        route_issue(record(), datetime.max.replace(tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="taxonomy"):
        route_issue(record(repo="textual"), RECEIVED)
    with pytest.raises(ValidationError):
        route_issue(record().model_copy(update={"needs_human_review": False}), RECEIVED)
