"""Exercise the model boundary without a network request or real credentials."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from triage.extract import DSPyExtractor
from triage.models import Issue


@pytest.mark.parametrize("response", [
    "not JSON", '{"issue_type":"bug"}',
    json.dumps({
        "issue_type": "bug", "component": "middleware", "severity": "medium",
        "has_reproduction_steps": True, "summary": "An example fails.",
        "rationale": "A failing example is supplied.", "confidence": 0.9,
    }),
])
def test_model_boundary(response: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-credential")
    issue = Issue.model_validate({
        "repo": "hono", "number": 1, "title": "Middleware error",
        "labels": ["bug"], "gold_type": "bug",
    })
    with patch("triage.extract.dspy.LM"), patch("triage.extract.dspy.context"), \
            patch("triage.extract.dspy.Predict") as predict:
        predict.return_value.return_value = SimpleNamespace(triage_json=response)
        extractor = DSPyExtractor("openai/test-model")
        if response.startswith('{"issue_type": "bug", "component"'):
            assert extractor(issue).issue_type == "bug"
        else:
            with pytest.raises(ValidationError):
                extractor(issue)
        inputs = predict.return_value.call_args.kwargs
        assert json.loads(inputs["issue_json"]) == issue.model_dump()
        assert json.loads(inputs["allowed_components"]) == ["middleware", "testing"]


def test_placeholder_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-xxxx")
    with pytest.raises(ValueError, match="real OPENAI_API_KEY"):
        DSPyExtractor("openai/test-model")
