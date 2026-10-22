"""Best-effort credential redaction; this does not detect all sensitive data."""

import os
import re

_KEY_PATTERNS = (
    re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"xai-[A-Za-z0-9_-]{32,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"-----BEGIN ([A-Z0-9 ]*PRIVATE KEY)-----[\s\S]*?(?:-----END \1-----|\Z)"),
)
_CREDENTIAL_ENV_NAMES = (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY", "GITHUB_TOKEN",
)


def redact_secrets(text: str) -> str:
    # Redact configured values too, including keys with unrecognized formats.
    secrets: list[str] = sorted(
        {value for name in _CREDENTIAL_ENV_NAMES if len(value := os.getenv(name, "")) >= 12},
        key=lambda value: len(value), reverse=True,
    )
    for secret in secrets:
        text = text.replace(secret, "[REDACTED]")
    for pattern in _KEY_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text
