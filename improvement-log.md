# Improvement log

Every time the agent gets something wrong, it goes here. Not the fix — the
*failure*, classified.

This file runs for the whole semester. In W12 you will use it to show what
changed about how you work. That only works if it was written as things
happened, so write entries the day they occur. An improvement log
reconstructed from memory in week eleven is a creative writing exercise.

## The taxonomy

Classify every entry as exactly one of:

| Class | Meaning | Where the fix usually belongs |
|---|---|---|
| `capability` | the model could not do this | change the task, or the model |
| `context` | it could have, but did not know something | what the agent is given to read |
| `tool` | it lacked a way to act or to check | tooling |
| `spec` | the request was ambiguous and it guessed | the specification |
| `concept` | it used the wrong idea or the wrong name | the domain model |
| `bug` | ordinary defect, nothing AI-specific | the code |

The class matters more than the fix. Choosing between `context` and `spec`
forces you to say whether the agent lacked information or you did — and those
have different remedies.

---

## Entries

### E1

- **Date**: 2026-10-15
- **What happened**: The first implementation allowed model-reported confidence to disable human review even though confidence was not calibrated and issue text could influence predictions.
- **Class**: concept
- **Evidence** (session log timestamp, commit, or file:line): Earlier service.py review policy; tests/triage/test_security.py::test_model_cannot_disable_review.
- **What I did about it**: Required human review for every record and made the output schema reject needs_human_review=false.
- **Did it work?**: Regression tests pass; this prevents confidence from bypassing review but does not establish model accuracy or eliminate prompt injection.

---

### E2

- **Date**: 2026-10-15
- **What happened**: Input field limits were applied only after the entire JSON file/stdin stream had already been read and parsed, so ignored fields could still consume excessive memory.
- **Class**: bug
- **Evidence**: Original cli.py load_issue read_text/stdin.read calls; tests/triage/test_security.py::test_oversized_input_is_rejected_before_parsing.
- **What I did about it**: Added bounded binary reads before decoding/parsing, with a 1 MiB issue limit and a 16 MiB snapshot limit.
- **Did it work?**: Tests verify oversized file/stdin rejection, byte counting, boundary behavior, and rejection before parsing or model initialization.

---

### E3

- **Date**: 2026-10-15
- **What happened**: Prediction errors were sanitized, but initialization ValueError messages were printed verbatim. A synthetic exception demonstrated that sensitive text could reach stderr.
- **Class**: bug
- **Evidence**: Review's synthetic constructor exception; tests/triage/test_security.py::test_initialization_error_is_sanitized.
- **What I did about it**: Replaced arbitrary initialization exception messages with a fixed configuration error and covered ValueError, RuntimeError, and ImportError.
- **Did it work?**: Regression tests confirm no synthetic secret or partial JSON reaches stdout/stderr through this handler; third-party logging remains outside this guarantee.

---

### E4

- **Date**: 2026-10-15
- **What happened**: The initial implementation was validated with mocked predictions and intake parsing, but the required live 20-issue dev review remained unfinished. Those checks could not demonstrate that the configured model could produce even one real triage record.
- **Class**: concept
- **Evidence**: data/reviews/dev-triage-config-failures.json contains 20 CLI attempts, all exit code 2 and record=null; review-findings.md, Surprise 1.
- **What I did about it**: Added a reproducible runner using the real CLI and recorded actual failures without inventing model outputs or claiming classification accuracy.
- **Did it work?**: Execution evidence is reproducible; subsequent live preflight attempts were blocked by network permissions, model spelling, then API quota. The user requested stopping at the blocked-run findings, so classification behavior remains unverified.

---

### E5

- **Date**: 2026-10-15
- **What happened**: Fixing exception disclosure replaced every initialization error with one generic message. This protected arbitrary exception text but removed the actionable distinction between a missing/placeholder key, unsupported model, and dependency failure.
- **Class**: bug
- **Evidence**: All 20 stderr entries in data/reviews/dev-triage-config-failures.json have the same generic configuration message; cli.py initialization error handler.
- **What I did about it**: Recorded the tradeoff and checked setup without displaying secret values. Subsequent live preflight diagnostics reported only exception classes and safe failure categories; they identified model spelling and then insufficient API quota. A future fix should use predefined safe error codes for known configuration/provider conditions.
- **Did it work?**: The current quota blocker is identified, but more specific safe CLI diagnostics have not been implemented. See data/reviews/dev-triage-preflight.json.

---

### E6

- **Date**: 2026-10-15
- **What happened**: The new review runner reinitialized the CLI for every issue despite a provider configuration failure that was already known before the run. The result was 20 identical errors and repeated cache warnings rather than useful classification evidence.
- **Class**: bug
- **Evidence**: tools/review_dev.py subprocess loop; all 20 results in data/reviews/dev-triage-config-failures.json.
- **What I did about it**: Preserved the failure evidence, requested a locally saved credential update, and manually preflighted one issue before considering another batch. Added a --model override to the runner so the documented lowercase identifier can be used without changing secrets.
- **Did it work?**: Manual preflight prevented another 20 repeated failures after the quota error. Automatic batch preflight remains outstanding; the user requested leaving the blocked-run findings for now.
