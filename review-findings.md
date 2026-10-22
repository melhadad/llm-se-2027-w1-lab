Name:
Date: 2026-10-15

# Exercise A - Execution findings

Implementation verification: 43 automated tests pass using mocked model
responses, and pyright reports no errors (DSPy boundary warnings remain).
On 2026-10-15 the CLI was executed on 20 dev issues, but all returned exit code 2
because the configured provider key was a placeholder. No triage records were
produced, so a live classification-quality review remains incomplete.
After the key was saved, a live preflight found an unsupported mixed-case model
identifier. Retrying with the documented lowercase `openai/gpt-6.1-sol` reached
an insufficient-quota/billing error. The user then requested leaving the
blocked-run findings for now; no further live attempts were made.
The sealed test split was not opened.
Intake validation also passed for 20 dev issues spanning all three projects;
this checks parsing only, not the quality of model classifications.

Run evidence: `data/reviews/dev-triage-config-failures.json` records all 20 attempts,
including issue identifiers, existing gold labels, exit codes, stderr, and null
records. `tools/review_dev.py` reproduces the sample with seed 20261015:
7 Hono, 7 Litestar, and 6 Textual issues. It invokes the actual triage CLI, without
mocking the model. The following are execution findings, not model classifications.

---
### Surprise 1

- **Input issue json**: Hono #4164, "AWS API Gateway V2 and Hono Lambda"; selected from dev.json. All other 19 selected issues behaved identically.
- **Output triaged issue**: No stdout JSON; exit code 2; stderr includes `Configuration error: check LLM_MODEL, the provider API key in .env, and installed dependencies.`
- **What is surprising**: 43 passing mock-based tests did not mean the tool was ready for a live run. Intake and unit tests work, but the actual classification step never started because credentials were placeholders. This is an integration/setup failure, not evidence of inaccurate classifications.

### Surprise 2

- **Input issue json**: All 20 attempts listed in the evidence JSON.
- **Output triaged issue**: Every attempt also emitted `Failed to initialize disk cache, falling back to memory-only cache: unable to open database file` before the configuration error.
- **What is surprising**: Dependency cache initialization happens at import time even though the provider key is rejected before model construction, and even though LM response caching is disabled. The cache warning reports a fallback rather than the cause of the missing classifications. Third-party stderr is not covered by our application's error-message sanitization.

### Surprise 3

- **Input issue json**: The sampled dev inputs contain 10 non-null gold issue types and zero non-null gold components across the 20 issues.
- **Output triaged issue**: No classifications available to compare. This is an input-label coverage observation only.
- **What is surprising**: Even a successful rerun would not support a component-accuracy claim for this particular sample. Missing labels do not establish that a predicted component/type is wrong, and severity/reproduction still need manual review.

### Next step

Once API quota is available, run
`uv run python tools/review_dev.py --model openai/gpt-6.1-sol` and inspect all 20
returned records against their original dev issue text. Approved network access
was required in this workspace. Do not substitute mocked predictions for the
missing outputs. The current evidence records zero successful classifications.

### Surprise 4 - multiple independent setup failures

- **Input issue json**: Hono #4164, reused for a live preflight after credentials were saved.
- **Output triaged issue**: No record. The sandbox attempt failed with ConnectionError; approved network access then exposed LMUnsupportedModelError for `openai/gpt-6.1-Sol`; the lowercase model retry produced LMRateLimitError categorized as insufficient quota/billing. Sanitized diagnostic evidence is saved in `data/reviews/dev-triage-preflight.json`.
- **What is surprising**: Saving an API key was necessary but insufficient. Network permissions, the exact model identifier, and available API quota were separate prerequisites. The normal CLI's generic prediction error did not distinguish them. No inference about model classification quality is possible from these failures.
- **Model reference**: The official model identifier is `gpt-6.1-sol`: https://developers.openai.com/api/docs/models/gpt-6.1-sol .


# Exercise B — Review findings

## Part 1 — found by reading

Record every problem you find in the released diff. One block per finding.
Add as many as you need. Do not delete the unused ones — an empty block is
information too.

**These lock at 1:13.** Once you start running the code, anything new goes in
part 2 instead. That boundary is the measurement: without it there is no way to
tell what reading caught from what the test runner caught.

Confidence: `certain` | `probable` | `uncertain`

---

### Finding 1

- **Location** (file:line):
- **Confidence**:
- **What is wrong**:
- **Why it matters** (what breaks, for whom, when):
- **What would have caught this** (a test? a type? a review rule? nothing?):

---

### Finding 2

- **Location**:
- **Confidence**:
- **What is wrong**:
- **Why it matters**:
- **What would have caught this**:

---

### Finding 3

- **Location**:
- **Confidence**:
- **What is wrong**:
- **Why it matters**:
- **What would have caught this**:

---

### Finding 4

- **Location**:
- **Confidence**:
- **What is wrong**:
- **Why it matters**:
- **What would have caught this**:

---

### Finding 5

- **Location**:
- **Confidence**:
- **What is wrong**:
- **Why it matters**:
- **What would have caught this**:

---

### Finding 6

- **Location**:
- **Confidence**:
- **What is wrong**:
- **Why it matters**:
- **What would have caught this**:

---

## Part 2 — found by running

After `git apply`, `uv run pytest`, `uv run pyright` and the batch run.

### What the tooling found that I did not

- **Which tool** (pytest / pyright / running it):
- **What it showed**:
- **Would I have found this by reading?** (be honest):

### What I found by reading that the tooling did not

- 

### Anything the tooling reported that turned out not to be a problem

- 

---

## Scoring (fill in after the reveal)

| | part 1 (reading) | part 1 + part 2 |
|---|---|---|
| Seeded defects found | | |
| Seeded defects missed | | |
| False positives | | |

**Reading detection rate**: found / (found + missed) = ____%

**Combined detection rate**: found / (found + missed) = ____%

The gap between those two is not a measure of you. It is a measure of which
defects a machine can catch and which ones still need a person — and the
second group is the reason this course exists.

### One sentence: what did you miss, and why do you think you missed it?


