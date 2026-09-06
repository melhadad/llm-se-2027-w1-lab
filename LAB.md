# W1 Lab — Ship it, then review it

Two hours. Individual work. Two exercises.

Before you start, confirm you ran `uv run python tools/verify_env.py` and
pasted your checkoff token into Moodle. If you did not, do that first and
expect to fall behind.

**Keep `improvement-log.md` open for the whole session.** Every time the agent
gets something wrong today — misreads the brief, invents a field, needs telling
twice — stop and write the entry while it is in front of you. Three entries is
the minimum for checkoff and they take a minute each *now*. Written from memory
at 1:55 they are worth nothing, and the file says so itself.

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

`data/snapshot/{train,dev,test}.json` is **already in your repository**. It was
fetched and labelled ahead of the session; you do not need to build it, and you
should not try to during the lab.

The issues come from three real projects — **litestar** (Python web framework),
**hono** (TypeScript web framework), and **textual** (Python terminal UI
framework).

Do not run `tools/fetch_issues.py` today. Forty people pulling 400 issues each
from one lecture-room IP is a rate limit, not a dataset. The tools are there for
later in the course, or if your instructor tells you the snapshot is missing:

```bash
uv run python tools/fetch_issues.py --limit 400   # not during the lab
uv run python tools/classify_issues.py
```

`test.json` is sealed. Do not open it. Do not let your agent read it. You will
need it later in the course and its only value is that nobody has seen it.

### Scope, and where it goes

Triage only: **one issue in, one structured record out.** Not routing, not
queues, not deciding who gets paged — just turning an unstructured issue into
data. Deciding what to *do* with that record is a different job, and you will
meet someone else's answer to it after the break.

Your code goes in **`src/triage/`**. That package is yours: any files you like,
named however you like. Nothing released later in the lab is written into it.

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

Then add your Exercise A entries to `improvement-log.md` — where the agent went
wrong, classified. Do this before 0:45; you will not get the chance afterwards.

---

## Exercise B — Review an agent's work (40 min)

At 0:45 your instructor releases two things into your repository:

**`src/triage_by_agent/`** — a second answer to the brief you just worked on.
Same job as your `src/triage/`, written by someone else. Both are importable
side by side, which is the point:

```python
from triage import ...             # yours
from triage_by_agent import ...    # theirs
```

**`exercise-b/agent-change.diff`** — a change proposed on top of it. An agent
was asked to extend triage into a *routing* agent: decide which queue each
issue belongs in and how fast it is due, and add a batch path for processing a
whole day's issues at once. The agent opened the change with this description:

> Adds routing and batch processing. All tests pass, CI is green.

Note who is making that claim.

### What you are looking for

Not just bugs. A change can be correct and still be a bad change. Consider
behaviour under inputs the tests do not cover, resource use at scale,
anything that touches trust boundaries, consistency with how the rest of the
codebase names and structures things, and what happens when the model returns
something unexpected.

`src/triage_by_agent/` is the code as it stood before the change. If the diff
introduces a second name for something that package already named, that is a
finding.

### Part 1 — Review, by reading (28 min)

Review the diff as the maintainer who has to approve it. Record every problem
in `review-findings.md`.

**Do not run anything, and do not apply the diff yet.** This part measures what
you catch by reading — the only skill that scales to changes you did not write.

Rules:

- **No AI assistance for this exercise.** Close the agent. This is a
  measurement of you, and it is the only one you will get before the course
  changes how you think.
- Work alone.
- Record uncertain findings too, marked as uncertain. Precision matters as
  much as recall, and there is at least one thing in the diff that looks
  wrong and is not.
- **Findings lock at 1:13.** After that, part 1 gets no additions.

### Part 2 — Verify, by running (12 min)

Now apply it and see what the machine knows that you did not.

```bash
git apply --check exercise-b/agent-change.diff \
  || git checkout -- src/triage_by_agent tests/exercise_b
git apply exercise-b/agent-change.diff

uv run pytest
uv run pyright
PYTHONPATH=src uv run python -m triage_by_agent.cli batch --split dev --offline
```

`--offline` swaps the model for a deterministic stub, so this costs nothing and
everyone in the room gets the same answer.

(`PYTHONPATH=src` because this project is not installed into the environment.
`pyproject.toml` tells pytest where `src/` is, but plain `python -m` has no
such setting. Your own Exercise A command line needs the same thing.)

In the part 2 section of `review-findings.md`, record what the tooling found
that you did not, what it missed that you caught, and — for anything you
missed — whether it was findable by reading at all.

That last question is what most of this course is about.

### If you finish part 1 early

Open your `src/triage/` and `src/triage_by_agent/` side by side and add three
lines to `docs/decisions.md`: three places where the two implementations
decided something different about a question the brief never answered. What
fields exist, what happens to an issue with no clear type, what "confident"
means as a number.

Neither is the right answer. That is the finding, and next week is built on it.

---

## Reveal and scoring (13 min)

The seeded defect list goes up on the screen. Score your own findings:

- **found** — you identified it, for substantially the right reason
- **missed** — you did not
- **false positive** — you flagged something that is not a problem

You will end up with **two** detection rates: one for what you found by
reading, and one that includes what the tooling handed you in part 2. The gap
between them is the interesting number, and it is not a measure of you — it is
a measure of which defects a machine can catch and which ones still need a
person. We come back to that in W11.

Nobody is graded on either number. They go on the board anonymously, and you
will meet them again in W7 next to how well frontier models do on the same
diff.

---

## Plenary (20 min)

We pool the failures from both exercises on the board and sort them. For each
one: what kind of failure is it, and what would have caught it?

Most of the answers are weeks of this course. That is the point — the syllabus
gets built out of what went wrong in this room today, not handed to you.

---

## Checkoff

Push to your repository:

- [ ] working feature from Exercise A in `src/triage/`, typed, with a test
- [ ] `docs/decisions.md` — the unspecified decisions you made
- [ ] `review-findings.md` — findings from both parts, and both detection rates
- [ ] `improvement-log.md` — at least three entries, classified
- [ ] `sessions/` — session logs exported and committed

```bash
uv run python tools/export_session_log.py
git add -A && git add -f sessions/ && git commit -m "W1 lab" && git push
```

(`sessions/*.jsonl` is gitignored so that a stray transcript never lands in a
commit by accident. The `-f` is deliberate: you are choosing to commit these.)

Then tell your instructor, out loud, the one failure you found most
surprising, and why.
