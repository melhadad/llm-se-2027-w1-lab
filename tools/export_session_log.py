"""Export Claude Code session transcripts into the repository.

    uv run python tools/export_session_log.py

Claude Code stores transcripts outside your project, under ~/.claude/projects/
as JSONL, one file per session. They are not in git, so they are not evidence
until you put them there.

Why this matters more than it looks
-----------------------------------
The improvement loop later in the course consumes these logs. You cannot
reconstruct in week 12 what your agent got wrong in week 3 from memory, and a
reflection written from memory is fiction. Run this at the end of every
working session and commit the result.

Redaction: any line matching a credential pattern is replaced before writing.
Transcripts contain whatever was on your screen, which sometimes includes
things that should not be in a public repository.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "sessions"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"

REDACT = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{32,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{30,}"),
    re.compile(r"xai-[A-Za-z0-9]{32,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
]


def redact(text: str) -> str:
    for pattern in REDACT:
        text = pattern.sub("[REDACTED-CREDENTIAL]", text)
    return text


def project_key(path: Path) -> str:
    """Claude Code encodes the project path as a flattened directory name."""
    return str(path).replace("/", "-").replace("\\", "-")


def main() -> None:
    DEST.mkdir(exist_ok=True)
    if not CLAUDE_PROJECTS.exists():
        print(f"no transcripts found at {CLAUDE_PROJECTS}")
        print("If you used a different agent, copy its logs into sessions/ by hand.")
        return

    candidates = [d for d in CLAUDE_PROJECTS.iterdir() if d.is_dir() and ROOT.name in d.name]
    if not candidates:
        candidates = sorted(CLAUDE_PROJECTS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:1]
        if candidates:
            print(f"no exact project match; using most recent: {candidates[0].name}")

    exported = 0
    for directory in candidates:
        for src in sorted(directory.glob("*.jsonl")):
            stamp = datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc).strftime("%Y%m%dT%H%M")
            dest = DEST / f"{stamp}-{src.stem[:8]}.jsonl"
            if dest.exists():
                continue
            dest.write_text(redact(src.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
            exported += 1
            print(f"exported {dest.relative_to(ROOT)}")

    if exported == 0:
        print("nothing new to export")
    else:
        print(f"\n{exported} session(s) exported. Now commit them:")
        print("    git add sessions/ && git commit -m 'session logs'")


if __name__ == "__main__":
    main()
