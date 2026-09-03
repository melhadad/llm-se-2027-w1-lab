# llm-se-2027 — W1 lab

Software Engineering with AI. Week 1: issue triage.

## Before the lab (do this at home)

```bash
uv sync
cp .env.example .env          # fill in ONE model key + a GitHub token
uv run python tools/verify_env.py
```

It prints a checkoff token. Paste that into Moodle **before** the session.
Setup that fails in the room costs everyone time, which is why this is homework.

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
