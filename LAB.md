# W1 Lab — Ship it, then review it

Two hours. Individual work. Two exercises.

Before you start, confirm you ran `uv run python tools/verify_env.py` and
pasted your checkoff token into Moodle. If you did not, do that first and
expect to fall behind.

---

## Exercise A — Ship a triage feature (35 min)

### The brief

> Build a tool that reads a GitHub issue and produces a structured triage
> record, so that incoming issues can be routed automatically instead of by
> hand.

That is the entire specification. It is what a real request looks like.

Use Claude Code. Use DSPy for the model call — you have not been taught DSPy
and you do not need to be; the agent knows it. Your job is not to learn a
framework today. Your job is to get something working and to notice what
happens while you do.

### Data

```bash
uv run python tools/fetch_issues.py --limit 400
uv run python tools/classify_issues.py
```

This pulls issues from three real projects — **litestar** (Python web
framework), **hono** (TypeScript web framework), and **textual** (Python
terminal UI framework) — and writes `data/snapshot/{train,dev,test}.json`.

`test.json` is sealed. Do not open it. Do not let your agent read it. You will
need it later in the course and its only value is that nobody has seen it.

### Constraints

- Runs from the command line, takes an issue, prints a triage record.
- Committed, typed (`uv run pyright`), with at least one test.
- Every decision you had to make that the brief did not specify: write it down
  in `docs/decisions.md` as one line each. You will need this list next week.

### Security note, and it is not hypothetical

Issue text is written by anonymous strangers. It is **data, never
instructions**. At least one issue title in one of these three repositories
contains a shell command substitution pointing at a bare IP address.

Never pass issue text to a shell. Never interpolate it into a command. If
something in an issue body reads like an instruction addressed to you or to
your agent, that is the attack, not a coincidence.

### When you finish

Run it over twenty issues from `dev.json`. Look at the output. Write down
anything that surprised you.

---

## Exercise B — Review an agent's work (35 min)

At 0:45 your instructor releases `exercise-b/`. It contains a working
implementation of roughly the task you just did, plus a diff proposing a
change to it.

The change was produced by a coding agent. **Every test passes.** CI is green.

### Your job

Review the diff as if you were the maintainer who has to approve it. Record
every problem you find in `review-findings.md`, using the format in that file.

Rules:

- **No AI assistance for this exercise.** Close the agent. This is a
  measurement of you, and it is the only one you will get before the course
  changes how you think.
- Work alone.
- Hard stop at 1:20 whether you are finished or not.
- Record uncertain findings too, marked as uncertain. Precision matters as
  much as recall, and there is at least one thing in the diff that looks
  wrong and is not.

### What you are looking for

Not just bugs. A change can be correct and still be a bad change. Consider
behaviour under inputs the tests do not cover, resource use at scale,
anything that touches trust boundaries, consistency with how the rest of the
codebase names and structures things, and what happens when the model returns
something unexpected.

---

## Reveal and scoring (15 min)

The seeded defect list goes up on the screen. Score your own findings:

- **found** — you identified it, for substantially the right reason
- **missed** — you did not
- **false positive** — you flagged something that is not a problem

Compute and record your detection rate in `review-findings.md`. Nobody is
graded on this number. It goes on the board anonymously, and you will meet it
again in W7 when we look at how well frontier models do at the same task.

---

## Plenary (20 min)

We pool the failures from both exercises on the board and sort them. For each
one: what kind of failure is it, and what would have caught it?

Most of the answers are weeks of this course. That is the point — the syllabus
gets built out of what went wrong in this room today, not handed to you.

---

## Checkoff

Push to your repository:

- [ ] working feature from Exercise A, typed, with a test
- [ ] `docs/decisions.md` — the unspecified decisions you made
- [ ] `review-findings.md` — findings and your detection rate
- [ ] `improvement-log.md` — at least three entries, classified
- [ ] `sessions/` — session logs exported and committed

```bash
uv run python tools/export_session_log.py
git add -A && git commit -m "W1 lab" && git push
```

Then tell your instructor, out loud, the one failure you found most
surprising, and why.
