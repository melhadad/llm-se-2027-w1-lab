# Unspecified decisions

The brief did not tell you everything. Every time you or your agent chose
something the brief did not specify, add a line here.

Examples of the kind of thing that counts: what fields the record has, what
happens to an issue with no clear type, how confident is confident enough,
what the output looks like when the model returns nothing usable.

You will need this list in W2, when we reconstruct the requirements this
build implicitly assumed. The comparison across the cohort is the lesson, so
write down what you actually decided, not what you think is the right answer.

---

- Intake accepts one JSON issue object from a file/stdin or one issue selected by project and number from train/dev; routing recommendations and batch intake are now supported, while fetching GitHub URLs and mutating external queues remain outside scope.
- Supported projects are litestar, hono, and textual; full repository names are normalized, while unknown projects are rejected.
- Required intake fields are repo, positive integer number, and nonblank title; missing/null bodies become empty strings, and existing labels, gold labels, and all other metadata are discarded before prediction.
- Input is limited to 1,000 title characters and 60,000 body characters; oversized inputs fail rather than being silently truncated.
- DSPy Predict calls the model selected by --model or LLM_MODEL; .env is loaded from the project root without overriding existing environment variables.
- Output contains repo, number, issue_type, component, severity, has_reproduction_steps, summary, rationale, confidence, and needs_human_review.
- Issue types are bug, enhancement, documentation, question, meta, and unknown; ambiguous cases may remain unknown.
- Components mirror config/repos.toml; component is null when unsupported/uncertain, and Textual always uses null because it has no component taxonomy.
- Severity uses critical/high/medium/low/unknown based on reported impact, without claiming independent verification; severity has no dataset gold labels.
- Reproduction status is true for concrete steps, a runnable example, or a reproduction link; false when absent and null when unclear; links are never fetched.
- Confidence is a model self-estimate rather than a calibrated probability; values outside [0,1] or nonfinite values are rejected.
- Every record requires human review, including confidence 1.0; deterministic routing recommendations preserve this flag, external actions still require review, and TriageRecord rejects needs_human_review=false.
- Issue text is passed only as JSON data to the model, never to a shell or tool; prompt instructions and strict validation reduce but cannot eliminate semantic prompt injection.
- Malformed/extra model fields or project-incompatible components fail closed; no fabricated fallback record is emitted.
- CLI stdout contains only the successful JSON record; errors go to stderr with exit 2 for input/configuration problems and exit 1 for prediction problems; provider error details are suppressed to avoid exposing secrets.
- DSPy response caching is disabled; model calls have a 60-second provider timeout, at most one provider retry, and a 1,800-token output budget; DSPy may make an adapter fallback call.
- train/dev are selectable snapshots; test.json remains sealed and is excluded from CLI split choices and verification.
- Automated tests use mocked model responses and cannot establish real classification quality; a live 20-issue dev review requires a valid configured provider key.
- Binary input reads are bounded before UTF-8 decoding or JSON parsing: 1 MiB per file/stdin issue and 16 MiB per local snapshot, including ignored fields; invalid encoding and parser recursion errors fail as input errors.
- All initialization exceptions use a fixed CLI error message; arbitrary provider/constructor exception text is never echoed by our error handler.
- Common provider API-key and GitHub token formats, private key blocks, and configured credentials of at least 12 characters are redacted before prediction and in summary/rationale; input Issue objects stay unchanged and redaction does not establish that arbitrary private data is safe to send.
- Routing is a deterministic policy, not a second LLM prediction; its record embeds the original TriageRecord and adds queue, priority, due_in_hours, received_at, due_at, and policy_version=1.
- User-approved response targets are critical=1h, high=24h, medium=72h, low=168h, unknown=24h, measured continuously from receipt; these are response deadlines, not resolution or business-hour promises.
- Routing precedence is critical severity to urgent, then unknown type/confidence below 0.8 to triage, then documentation/question/meta ownership, then supported components for bugs/enhancements, then type fallback; every queue is prefixed with the project key.
- Missing reproduction steps never lower urgency, and the unknown-severity response target is 24 hours independent of confidence.
- Caller-supplied receipt timestamps must include a timezone and leave room for the full seven-day policy horizon; they are normalized to UTC, and all items in one batch share a single receipt time captured before predictions.
- Daily batch input is a JSON array, defaulting to existing triage records without model calls; --kind issue enables raw-issue triage plus routing with a lazily initialized, reused extractor.
- Batches are capped at 16 MiB/1000 items and processed sequentially; results preserve input order and contain either a decision or a fixed safe error code without raw exception messages or issue text.
- Duplicate identities are scoped by project and issue number; only the first valid occurrence is processed, including when prediction fails, and later duplicates are reported without another model invocation.
- Batch configuration failures are attempted once, provider/output failures are isolated per item, empty/all-invalid batches never initialize a model, and no synthetic triage record replaces a failure.
- Batch exit codes are 0 for complete success, 1 for item-level failures with a JSON report, and 2 for invalid top-level input; retrying uses failed indexes from the original input and deduplication is limited to the current batch.
