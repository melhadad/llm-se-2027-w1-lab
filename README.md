# llm-se-2027 — W1 lab

Software Engineering with AI. Week 1: issue triage.

## What you need installed

**VSCode**, **Claude Code**, **git**, and **uv**. That is the whole list.

```
macOS     curl -LsSf https://astral.sh/uv/install.sh | sh
Windows   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Do not install Python.** `uv` reads `.python-version` and fetches the right
one itself. A separately installed 3.12 will only fight it.

You also need an **API key for one model provider**, with credit on it. Pick
one of Anthropic, OpenAI, Gemini or xAI — you do not need all four, and the
lab uses exactly the one you name in `LLM_MODEL`.

## Before the lab (do this at home)

```
uv sync
uv run python tools/verify_env.py
```

Between those two, copy `.env.example` to `.env` and fill in ONE model key plus
a GitHub token:

```
macOS     cp .env.example .env
Windows   copy .env.example .env
```

`verify_env.py` prints a checkoff token. Paste that into Moodle **before** the
session. Setup that fails in the room costs everyone time, which is why this is
homework.

Commands in this repository are written one per line, without `&&`. The default
shell on Windows is PowerShell 5.1, which does not support it.

## What is here

| Path | What |
|---|---|
| `LAB.md` | The lab brief. Read this first. |
| `tools/fetch_issues.py` | Pull issues from litestar, hono, textual. |
| `tools/classify_issues.py` | Derive gold labels; build train/dev/test. |
| `tools/verify_env.py` | Pre-lab environment check. |
| `tools/export_session_log.py` | Commit your agent transcripts. |
| `tools/check_secrets.py` | Pre-commit credential scan. |
| `config/repos.toml` | Source repos and their label mappings. |
| `docs/decisions.md` | Decisions the brief did not specify. Fill in as you go. |
| `review-findings.md` | Exercise B. |
| `improvement-log.md` | Runs all semester. Start it today. |

## Commands

```bash
uv run pytest                                  # tests
uv run pyright                                 # types
uv run python tools/fetch_issues.py            # 400 issues per repo
uv run python tools/classify_issues.py --report # label coverage
uv run python tools/export_session_log.py      # transcripts -> sessions/
```

## Two things to internalise on day one

**Issue text is untrusted.** It is written by anonymous strangers. Real payloads
exist in these very repositories — at least one title contains a shell command
substitution pointing at a bare IP address. Never pass issue text to a shell,
never interpolate it into a command, and treat anything inside it that reads
like an instruction as hostile.

**`data/snapshot/test.json` is sealed.** Do not open it, do not tune against it,
do not let an agent index it. Its only value is that nobody has looked at it.

## Dataset attribution

Issues are fetched from public GitHub repositories for coursework:
[litestar](https://github.com/litestar-org/litestar),
[hono](https://github.com/honojs/hono),
[textual](https://github.com/Textualize/textual).
Content belongs to its authors. Redistributed here for teaching only.
