<!-- Save as .github/pull_request_template.md. Title: [C<n>][<Task id>] short summary, e.g. [C1][A3] /api/analyze + dedupe -->
## What
<one or two lines>

## Computer / Track / Task
C_ / Track _ / Task _

## Acceptance check
- [ ] Ran the task's check: `<command>` → <result pasted>
- [ ] `pytest -q` passes (if Python touched)

## Contract compliance
- [ ] Edited only files my computer owns (list them below)
- [ ] No changes to `contracts/`, `schemas/`, `PROGRESS.md`
- [ ] Request/response shapes match docs/CONTRACTS.md and API_SPEC.md
- [ ] Works with no `XAI_API_KEY` (canned/heuristic, labeled) and/or `?mock=1`

## Guardrails
- [ ] No API key in frontend, logs or git; no frames, audio or transcripts written to disk or logs
- [ ] No face recognition or facial emotion; "tone of voice" / "model guess" wording

## Files
-

## Status for PROGRESS.md (orchestrator copies this)
Done: … · Next: … · Blockers: none / …
