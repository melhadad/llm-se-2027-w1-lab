"""Exercise the file-reading agent without contacting OpenAI."""

from pathlib import Path
from unittest.mock import patch

from openai import OpenAI
from openai.types.chat import ChatCompletion
import pytest

import myfirstagents3 as agent


@pytest.fixture
def files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "tools"
    root.mkdir()
    (root / "example.txt").write_text("hello world", encoding="utf-8")
    monkeypatch.setattr(agent, "FILE_ROOT", root)
    return root


def completion(*, arguments: str | None = None, content: str | None = None) -> ChatCompletion:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if arguments is not None:
        message["tool_calls"] = [{
            "id": "call_read", "type": "function",
            "function": {"name": "read_file", "arguments": arguments},
        }]
    return ChatCompletion.model_validate({
        "id": "test", "object": "chat.completion", "created": 0, "model": "gpt-5-mini",
        "choices": [{"index": 0, "finish_reason": "tool_calls" if arguments else "stop",
                     "message": message}],
    })


def test_file_path_does_not_depend_on_terminal_directory(
    files: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(files.parent)
    assert agent.read_file("example.txt") == "hello world"
    assert agent.read_file("missing.txt") == "Error: file not found."


def test_tool_cannot_read_outside_tools_or_read_env(files: Path) -> None:
    (files.parent / "outside.txt").write_text("private", encoding="utf-8")
    (files / ".env").write_text("private", encoding="utf-8")
    assert agent.read_file("../outside.txt").startswith("Error:")
    assert agent.read_file(str(files.parent / "outside.txt")).startswith("Error:")
    assert agent.read_file(".env").startswith("Error:")


def test_large_files_and_invalid_utf8_are_rejected(files: Path) -> None:
    (files / "large.txt").write_bytes(b"x" * (agent.MAX_FILE_BYTES + 1))
    (files / "binary.txt").write_bytes(b"\xff")
    assert "64 KiB" in agent.read_file("large.txt")
    assert "UTF-8" in agent.read_file("binary.txt")


def test_file_credentials_are_redacted(files: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "synthetic-test-credential"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    (files / "example.txt").write_text(f"key={secret}", encoding="utf-8")
    assert agent.read_file("example.txt") == "key=[REDACTED]"


@pytest.mark.parametrize("arguments", [
    "not JSON", "[]", "{}", '{"path": 123}',
    '{"path": "example.txt", "extra": true}',
])
def test_invalid_tool_arguments_return_an_error(arguments: str) -> None:
    assert agent.execute_tool("read_file", arguments).startswith("Error:")


def test_unknown_tool_is_not_executed() -> None:
    with patch.object(agent, "read_file") as read:
        assert agent.execute_tool("delete_file", '{"path": "example.txt"}').startswith("Error:")
        read.assert_not_called()


def test_tool_result_is_sent_back_before_the_final_answer(files: Path) -> None:
    assert files.exists()
    with OpenAI(api_key="test-credential") as client, \
            patch.object(client.chat.completions, "create") as create:
        create.side_effect = [
            completion(arguments='{"path": "example.txt"}'),
            completion(content="The file contains hello world."),
        ]
        assert agent.run_agent(client) == "The file contains hello world."
        messages = create.call_args_list[1].kwargs["messages"]
        assert [message["role"] for message in messages] == ["user", "assistant", "tool"]
        assert messages[1]["tool_calls"][0]["id"] == "call_read"
        assert messages[2] == {"role": "tool", "tool_call_id": "call_read", "content": "hello world"}
        assert create.call_count == 2


def test_repeated_tool_requests_stop_at_the_limit(files: Path) -> None:
    assert files.exists()
    with OpenAI(api_key="test-credential") as client, \
            patch.object(client.chat.completions, "create") as create:
        create.return_value = completion(arguments='{"path": "example.txt"}')
        with pytest.raises(RuntimeError, match="request limit"):
            agent.run_agent(client, max_steps=2)
        assert create.call_count == 2


def test_empty_answer_is_reported() -> None:
    with OpenAI(api_key="test-credential") as client, \
            patch.object(client.chat.completions, "create", return_value=completion()):
        with pytest.raises(ValueError, match="no answer"):
            agent.run_agent(client)


def test_missing_key_does_not_initialize_client(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch.object(agent, "load_dotenv"), patch.object(agent, "OpenAI") as client:
        assert agent.main() == 2
        client.assert_not_called()
    assert "OPENAI_API_KEY" in capsys.readouterr().err
