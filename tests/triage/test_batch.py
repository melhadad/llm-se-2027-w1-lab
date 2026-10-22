import io
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from triage import Assessment, Issue, route_batch
from triage.batch import BatchFailure, BatchSuccess, MAX_BATCH_ITEMS
from triage.cli import main
from triage.service import Extractor

RECEIVED = datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)


def record(repo: str = "hono", number: int = 1) -> dict[str, object]:
    return {
        "repo": repo, "number": number, "issue_type": "bug", "component": None,
        "severity": "high", "has_reproduction_steps": False,
        "summary": "Example", "rationale": "Reported failure", "confidence": 0.9,
        "needs_human_review": True,
    }


def test_mixed_batch_preserves_order_and_handles_duplicates() -> None:
    report = route_batch([
        record(), {"malformed": True}, record(), record("litestar"), record("textual"),
    ], received_at=RECEIVED)
    assert (report.total, report.succeeded, report.failed) == (5, 3, 2)
    assert [row.index for row in report.results] == list(range(5))
    errors = [row.error_code for row in report.results if isinstance(row, BatchFailure)]
    assert errors == ["invalid_input", "duplicate_issue"]
    successes = [row.decision for row in report.results if isinstance(row, BatchSuccess)]
    assert [row.queue for row in successes] == ["hono/bugs", "litestar/bugs", "textual/bugs"]
    assert {row.received_at for row in successes} == {RECEIVED}
    assert all(row.triage.needs_human_review for row in successes)


def test_raw_batch_initializes_once_and_isolates_failure() -> None:
    calls: list[int] = []
    initializations: list[int] = []

    def extractor(issue: Issue) -> Assessment:
        calls.append(issue.number)
        if issue.number == 2:
            raise RuntimeError("SYNTHETIC_SECRET")
        return Assessment.model_validate({
            k: v for k, v in record().items() if k not in ("repo", "number", "needs_human_review")
        })

    def factory() -> Extractor:
        initializations.append(1)
        return extractor

    inputs: list[object] = [
        {"repo": "hono", "number": number, "title": "Example"} for number in (1, 2, 1, 3)
    ]
    report = route_batch(inputs, kind="issue", received_at=RECEIVED, extractor_factory=factory)
    assert calls == [1, 2, 3]
    assert initializations == [1]
    assert report.succeeded == 2
    assert [row.error_code for row in report.results if isinstance(row, BatchFailure)] == [
        "prediction_failed", "duplicate_issue",
    ]
    assert "SYNTHETIC_SECRET" not in report.model_dump_json()


def test_configuration_failure_attempted_once_and_invalid_rows_cost_nothing() -> None:
    calls: list[int] = []

    def factory() -> Extractor:
        calls.append(1)
        raise ValueError("SYNTHETIC_SECRET")

    assert route_batch([], kind="issue", received_at=RECEIVED, extractor_factory=factory).total == 0
    route_batch([{}], kind="issue", received_at=RECEIVED, extractor_factory=factory)
    assert calls == []
    items: list[object] = [{"repo": "hono", "number": number, "title": "Example"} for number in (1, 2)]
    report = route_batch(items, kind="issue", received_at=RECEIVED, extractor_factory=factory)
    assert calls == [1]
    assert all(isinstance(row, BatchFailure) and row.error_code == "configuration_error" for row in report.results)
    assert "SYNTHETIC_SECRET" not in report.model_dump_json()


def test_taxonomy_and_model_output_failures() -> None:
    bad = {**record("textual"), "component": "middleware"}
    report = route_batch([bad], received_at=RECEIVED)
    assert isinstance(report.results[0], BatchFailure)
    assert report.results[0].error_code == "invalid_input"

    def extractor(_: Issue) -> Assessment:
        return Assessment.model_validate(record())

    report = route_batch(
        [{"repo": "hono", "number": 1, "title": "Example"}], kind="issue",
        received_at=RECEIVED, extractor_factory=lambda: extractor,
    )
    assert isinstance(report.results[0], BatchFailure)
    assert report.results[0].error_code == "invalid_prediction"


def test_size_and_timestamp_rejected_before_model_work() -> None:
    with pytest.raises(ValueError, match="1000"):
        route_batch([None] * (MAX_BATCH_ITEMS + 1), received_at=RECEIVED)
    with pytest.raises(ValueError, match="timezone"):
        route_batch([], received_at=datetime(2026, 10, 15))


def test_cli_route_and_batch_without_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record()), encoding="utf-8")
    with patch("triage.extract.DSPyExtractor", side_effect=AssertionError("No model calls allowed")):
        assert main(["route", "--record", str(path), "--received-at", "2026-10-15T12:00:00+03:00"]) == 0
        routed = json.loads(capsys.readouterr().out)
        assert routed["queue"] == "hono/bugs"
        assert routed["due_at"] == "2026-10-16T09:00:00Z"
        payload = json.dumps([record(), {}, record("textual")]).encode()
        monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=io.BytesIO(payload)))
        assert main(["batch", "--input", "-", "--received-at", "2026-10-15T09:00:00Z"]) == 1
    batch = json.loads(capsys.readouterr().out)
    assert (batch["succeeded"], batch["failed"]) == (2, 1)


@pytest.mark.parametrize("timestamp", ["2026-10-15T09:00:00", "invalid", "9999-12-31T23:59:59Z"])
def test_bad_timestamp_cli(timestamp: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["route", "--record", "unused", "--received-at", timestamp]) == 2
    assert capsys.readouterr().out == ""


def test_raw_cli_batch_uses_one_model(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "issues.json"
    path.write_text(json.dumps([
        {"repo": "hono", "number": 1, "title": "First"},
        {"repo": "textual", "number": 2, "title": "Second"},
    ]), encoding="utf-8")

    def extractor(_: Issue) -> Assessment:
        data = record()
        return Assessment.model_validate({k: v for k, v in data.items() if k not in ("repo", "number", "needs_human_review")})

    with patch("triage.extract.DSPyExtractor", return_value=extractor) as factory:
        assert main(["batch", "--input", str(path), "--kind", "issue"]) == 0
        factory.assert_called_once_with(None)
    assert json.loads(capsys.readouterr().out)["succeeded"] == 2
