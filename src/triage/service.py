"""Triage orchestration, independent of the model provider."""

from typing import Protocol

from triage.models import COMPONENTS, Assessment, Issue, TriageRecord


class Extractor(Protocol):
    def __call__(self, issue: Issue, /) -> Assessment: ...


def triage_issue(issue: Issue, extractor: Extractor) -> TriageRecord:
    assessment = extractor(issue)
    if assessment.component is not None and assessment.component not in COMPONENTS[issue.repo]:
        raise ValueError("model returned a component outside the project's taxonomy")
    return TriageRecord(
        **assessment.model_dump(),
        repo=issue.repo,
        number=issue.number,
        needs_human_review=True,
    )
