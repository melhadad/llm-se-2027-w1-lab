import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from triage.cli import MAX_ISSUE_BYTES, load_issue, main, read_json
from triage.extract import DSPyExtractor
from triage.models import Issue, TriageRecord
from triage.privacy import redact_secrets


def test_oversized_input_is_rejected_before_parsing() -> None:
    class BoundedStream(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            assert size == 65
            return super().read(size)

    stream = BoundedStream(b"x" * 1000)
    with patch("triage.cli.json.loads") as parse:
        with pytest.raises(ValueError, match="byte limit"):
            read_json(stream, 64)
        parse.assert_not_called()
    assert stream.tell() == 65


def test_limit_counts_bytes_and_accepts_exact_boundary() -> None:
    payload = json.dumps({"title": "\u2603"}, ensure_ascii=False).encode("utf-8")
    assert read_json(io.BytesIO(payload), len(payload)) == {"title": "\u2603"}
    with pytest.raises(ValueError, match="byte limit"):
        read_json(io.BytesIO(payload), len(payload) - 1)


@pytest.mark.parametrize("source", ["file", "stdin"])
def test_oversized_cli_input_never_reaches_model(
    source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = b" " * (MAX_ISSUE_BYTES + 1)
    if source == "stdin":
        monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=io.BytesIO(payload)))
        argv = ["--issue", "-"]
    else:
        path = tmp_path / "large.json"
        path.write_bytes(payload)
        argv = ["--issue", str(path)]
    with patch("triage.extract.DSPyExtractor") as factory:
        assert main(argv) == 2
        factory.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "1 MiB" in captured.err


def test_small_stdin_json_and_utf8_bom(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"repo": "hono", "number": 1, "title": "Example"})
    monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=io.BytesIO(payload.encode("utf-8-sig"))))
    args = SimpleNamespace(split=None, issue="-", number=None, repo=None)
    # CLI uses argparse.Namespace; construct the same parsed arguments here.
    from argparse import Namespace

    assert load_issue(Namespace(**vars(args))).title == "Example"


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError, ImportError])
def test_initialization_error_is_sanitized(
    error_type: type[Exception], capsys: pytest.CaptureFixture[str],
) -> None:
    issue = Issue(repo="hono", number=1, title="Example")
    with patch("triage.cli.load_issue", return_value=issue), \
            patch("triage.extract.DSPyExtractor", side_effect=error_type("SYNTHETIC_SECRET")):
        assert main(["--issue", "-"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Configuration error" in captured.err
    assert "SYNTHETIC_SECRET" not in captured.err


def test_parser_recursion_error_is_handled(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("triage.cli.load_issue", side_effect=RecursionError("UNTRUSTED_TEXT")):
        assert main(["--issue", "-"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "UNTRUSTED_TEXT" not in captured.err


@pytest.mark.parametrize("prefix", [
    "sk-", "sk-proj-", "sk-ant-api03-", "AIza", "xai-", "ghp_", "github_pat_",
])
def test_common_key_formats_are_redacted(prefix: str) -> None:
    secret = prefix + "Ab1" * 16
    assert redact_secrets(f"key={secret} and normal issue text") == "key=[REDACTED] and normal issue text"


def test_configured_key_and_private_key_are_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "unrecognized-format-test-credential"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    assert redact_secrets(secret) == "[REDACTED]"
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    footer = "-----END " + "RSA PRIVATE KEY-----"
    assert redact_secrets(f"before {header}\nSYNTHETIC\n{footer} after") == "before [REDACTED] after"
    assert redact_secrets(f"before {header}\nSYNTHETIC") == "before [REDACTED]"


def test_provider_receives_redacted_input_and_output_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-credential")
    secret = "ghp_" + "Ab1" * 16
    issue = Issue(repo="hono", number=1, title=secret, body=f"Example contains {secret}")
    response = json.dumps({
        "issue_type": "bug", "component": "middleware", "severity": "medium",
        "has_reproduction_steps": True, "summary": secret, "rationale": secret,
        "confidence": 1.0,
    })
    with patch("triage.extract.dspy.LM"), patch("triage.extract.dspy.context"), \
            patch("triage.extract.dspy.Predict") as predict:
        predict.return_value.return_value = SimpleNamespace(triage_json=response)
        result = DSPyExtractor("openai/test-model")(issue)
        sent = predict.return_value.call_args.kwargs["issue_json"]
        assert secret not in sent
        assert "[REDACTED]" in sent
        assert result.summary == result.rationale == "[REDACTED]"
        assert issue.title == secret


def test_model_cannot_disable_review() -> None:
    with pytest.raises(ValidationError):
        TriageRecord.model_validate({
            "repo": "hono", "number": 1, "issue_type": "bug", "component": "middleware",
            "severity": "low", "has_reproduction_steps": False, "summary": "Example",
            "rationale": "Example", "confidence": 1.0, "needs_human_review": False,
        })
