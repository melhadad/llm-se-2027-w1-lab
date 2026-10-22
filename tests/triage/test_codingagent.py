"""Offline checks for coding-agent tools and conversation handling."""

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
import pytest

import codingagent as agent


def completion(
    calls: list[tuple[str, dict[str, str]]] | None = None, *, content: str | None = None,
) -> ChatCompletion:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = [
            {"id": f"call_{index}", "type": "function",
             "function": {"name": name, "arguments": json.dumps(arguments)}}
            for index, (name, arguments) in enumerate(calls)
        ]
    return ChatCompletion.model_validate({
        "id": "test", "object": "chat.completion", "created": 0, "model": agent.MODEL,
        "choices": [{"index": 0, "finish_reason": "tool_calls" if calls else "stop",
                     "message": message}],
    })


def test_files_use_the_selected_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tools = agent.WorkspaceTools(tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    assert tools.write_file("nested/hello.txt", "hello world").startswith("Saved")
    assert tools.read_file("nested/hello.txt") == "hello world"
    assert tools.list_files() == "nested/"


@pytest.mark.parametrize("path", [
    "../outside.txt", ".env", ".env.local", ".git/config", ".venv/private.txt",
    "data/snapshot/test.json",
])
def test_protected_paths_are_rejected(tmp_path: Path, path: str) -> None:
    tools = agent.WorkspaceTools(tmp_path)
    with pytest.raises(ValueError):
        tools.write_file(path, "should not be written")
    with pytest.raises(ValueError):
        tools.read_file(path)


def test_listing_hides_credentials_and_file_text_is_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "synthetic-test-credential"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    (tmp_path / ".env").write_text(secret, encoding="utf-8")
    (tmp_path / "hello.txt").write_text(secret, encoding="utf-8")
    tools = agent.WorkspaceTools(tmp_path)
    assert tools.list_files() == "hello.txt"
    assert tools.read_file("hello.txt") == "[REDACTED]"


def test_tool_errors_do_not_crash_or_expose_arguments(tmp_path: Path) -> None:
    tools = agent.WorkspaceTools(tmp_path)
    for name, arguments in [
        ("unknown", "{}"), ("read_file", "not JSON"), ("read_file", '{"path": 42}'),
        ("read_file", '{"path": "missing.txt"}'),
        ("write_file", '{"path": "hello.txt", "content": "hi", "extra": true}'),
    ]:
        assert tools.run_tool(name, arguments).startswith("Error:")
    assert not (tmp_path / "hello.txt").exists()


def test_file_size_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent, "MAX_FILE_BYTES", 8)
    tools = agent.WorkspaceTools(tmp_path)
    (tmp_path / "large.txt").write_text("x" * 9, encoding="utf-8")
    with pytest.raises(ValueError):
        tools.read_file("large.txt")
    with pytest.raises(ValueError):
        tools.write_file("new.txt", "x" * 9)
    assert not (tmp_path / "new.txt").exists()


@pytest.mark.parametrize("answer", ["", "n"])
def test_commands_require_approval(tmp_path: Path, answer: str) -> None:
    tools = agent.WorkspaceTools(tmp_path)
    with patch("builtins.input", return_value=answer), patch.object(agent.subprocess, "run") as run:
        assert "declined" in tools.run_command("echo hello")
        run.assert_not_called()


def test_approved_command_reports_exit_status_and_uses_workspace(tmp_path: Path) -> None:
    tools = agent.WorkspaceTools(tmp_path)
    result = subprocess.CompletedProcess("echo hello", 3, "hello", "")
    with patch("builtins.input", return_value="y"), \
            patch.object(agent.subprocess, "run", return_value=result) as run:
        assert tools.run_command("echo hello") == "Exit code: 3\nhello"
        assert run.call_args.kwargs["cwd"] == tmp_path.resolve()
        assert run.call_args.kwargs["timeout"] == 120


def test_command_timeout_returns_a_tool_result(tmp_path: Path) -> None:
    tools = agent.WorkspaceTools(tmp_path)
    with patch("builtins.input", return_value="y"), \
            patch.object(agent.subprocess, "run", side_effect=subprocess.TimeoutExpired("test", 120)):
        assert "timeout" in tools.run_tool("run_command", '{"command": "echo hello"}')


def test_model_can_write_then_read_and_receive_matching_results(tmp_path: Path) -> None:
    tools = agent.WorkspaceTools(tmp_path)
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": "Create a greeting"}]
    with OpenAI(api_key="test-credential") as client, \
            patch.object(client.chat.completions, "create") as create:
        create.side_effect = [completion([
            ("write_file", {"path": "hello.txt", "content": "hello world"}),
            ("read_file", {"path": "hello.txt"}),
        ]), completion(content="Created and checked hello.txt.")]
        assert agent.run_agent(client, messages, tools) == "Created and checked hello.txt."
    assert (tmp_path / "hello.txt").read_text() == "hello world"
    assert [message["role"] for message in messages] == ["user", "assistant", "tool", "tool", "assistant"]
    assert messages[2] == {"role": "tool", "tool_call_id": "call_0", "content": "Saved hello.txt (11 characters)"}
    assert messages[3] == {"role": "tool", "tool_call_id": "call_1", "content": "hello world"}


def test_failed_turn_does_not_poison_conversation(tmp_path: Path) -> None:
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": "Keep listing"}]
    original = list(messages)
    with OpenAI(api_key="test-credential") as client, \
            patch.object(client.chat.completions, "create") as create:
        create.return_value = completion([("list_files", {"path": "."})])
        with pytest.raises(RuntimeError, match="request limit"):
            agent.run_agent(client, messages, agent.WorkspaceTools(tmp_path), max_steps=2)
        assert create.call_count == 2
    assert messages == original


def test_one_shot_cli_and_model_option(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-credential")
    with patch.object(agent, "load_dotenv"), patch.object(agent, "run_agent", return_value="done") as run:
        assert agent.main(["--workspace", str(tmp_path), "--task", "Create a greeting", "--model", "test-model"]) == 0
        assert run.call_args.kwargs["model"] == "test-model"


def test_missing_key_does_not_initialize_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch.object(agent, "load_dotenv"), patch.object(agent, "OpenAI") as client:
        assert agent.main(["--task", "hello"]) == 2
        client.assert_not_called()
