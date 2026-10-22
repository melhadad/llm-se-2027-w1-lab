"""Bounded batch orchestration with isolated failures and lazy model setup."""

from collections.abc import Callable
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from triage.models import Issue, TriageRecord
from triage.routing import RoutingRecord, normalize_received_at, route_issue
from triage.service import Extractor, triage_issue

MAX_BATCH_ITEMS = 1000
InputKind = Literal["triage", "issue"]
ErrorCode = Literal["invalid_input", "duplicate_issue", "configuration_error", "invalid_prediction", "prediction_failed"]


class BatchSuccess(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    index: int = Field(ge=0)
    status: Literal["ok"] = "ok"
    decision: RoutingRecord


class BatchFailure(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    index: int = Field(ge=0)
    status: Literal["error"] = "error"
    error_code: ErrorCode


class BatchReport(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    received_at: datetime
    total: int
    succeeded: int
    failed: int
    results: list[BatchSuccess | BatchFailure]


def route_batch(
    items: list[object], *, kind: InputKind = "triage", received_at: datetime,
    extractor_factory: Callable[[], Extractor] | None = None,
) -> BatchReport:
    if len(items) > MAX_BATCH_ITEMS:
        raise ValueError("batch exceeds the 1000-item limit")
    if kind not in ("triage", "issue"):
        raise ValueError("unknown batch input kind")
    timestamp = normalize_received_at(received_at)
    results: list[BatchSuccess | BatchFailure] = []
    seen: set[tuple[str, int]] = set()
    extractor: Extractor | None = None
    initialization_failed = False
    for index, item in enumerate(items):
        try:
            source = Issue.model_validate(item) if kind == "issue" else TriageRecord.model_validate(item)
            # Taxonomy validation belongs to input errors for pre-triaged records.
            decision = route_issue(source, timestamp) if isinstance(source, TriageRecord) else None
        except (ValueError, TypeError):
            results.append(BatchFailure(index=index, error_code="invalid_input"))
            continue
        identity = (source.repo, source.number)
        if identity in seen:
            results.append(BatchFailure(index=index, error_code="duplicate_issue"))
            continue
        seen.add(identity)
        if isinstance(source, Issue):
            if extractor is None and not initialization_failed:
                try:
                    if extractor_factory is None:
                        raise ValueError("raw issues require an extractor")
                    extractor = extractor_factory()
                except Exception:
                    initialization_failed = True
            if initialization_failed or extractor is None:
                results.append(BatchFailure(index=index, error_code="configuration_error"))
                continue
            try:
                decision = route_issue(triage_issue(source, extractor), timestamp)
            except (ValidationError, ValueError, TypeError):
                results.append(BatchFailure(index=index, error_code="invalid_prediction"))
                continue
            except Exception:
                results.append(BatchFailure(index=index, error_code="prediction_failed"))
                continue
        assert decision is not None
        results.append(BatchSuccess(index=index, decision=decision))
    succeeded = sum(isinstance(result, BatchSuccess) for result in results)
    return BatchReport(
        received_at=timestamp, total=len(items), succeeded=succeeded,
        failed=len(items) - succeeded, results=results,
    )
