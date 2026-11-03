# Parallel work: 4 computers + 1 orchestrator

One track = one person + their coding agent, on their own computer and branch. Ownership is **exclusive**: you edit only your track's files. Everything shared is in `CONTRACTS.md` (frozen at minute 0) and the schemas.

**Mapping (balanced):** Computer 1 = Track A (backend/Grok, heaviest logic). Computer 2 = Track B (live capture). Computer 3 = Track C (HUD + recap). Computer 4 = Track D (demo + data, the lightest) **then** Track E (glasses stretch). If another computer is fully done before Computer 4 finishes D, the orchestrator may reassign E to it; `ios/` has no other owner, so no overlap. Self-contained instructions: [COMPUTER_1](COMPUTER_1.md) · [COMPUTER_2](COMPUTER_2.md) · [COMPUTER_3](COMPUTER_3.md) · [COMPUTER_4](COMPUTER_4.md) · [ORCHESTRATOR](ORCHESTRATOR.md) · [PROGRESS template](PROGRESS.md) · [PR template](PR_TEMPLATE.md).

| Track | Owner role | Owns (only these) |
|---|---|---|
| A (C1) | Backend / Grok | `app/` except `app/cues.py` and `app/canned.py`; `pyproject.toml`; `.env.example`; `tests/test_api.py`, `tests/test_dedupe.py`, `tests/test_grok.py` |
| B (C2) | Live capture frontend | `web/live.html`, `web/live.js`, `web/api.js` |
| C (C3) | HUD + Recap UI | `web/hud.html`, `web/hud.js`, `web/recap.html`, `web/recap.js`, `web/app.css`, `app/cues.py`, `tests/test_cues.py` |
| D (C4) | Demo mode + data | `data/`, `web/demo/`, `web/demo.js`, `app/canned.py`, `scripts/`, `tests/test_schema.py` |
| E (C4 after D, or reassigned) | Glasses (stretch) | `ios/` only |

The **orchestrator** (5th agent, any machine) owns `contracts/` (after the freeze), `PROGRESS.md`, `.github/`, `README.md` and `CLAUDE.md`, and is the only one who merges to `main`. **PROGRESS.md is orchestrator-only**: if 4 branches each edited it, every PR would conflict on the same file. Computers report status in their PR description instead.

## Minute 0: contract freeze (orchestrator, ≤ 8 min; computers read docs meanwhile)
1. `git init`, create `main` with: `CLAUDE.md` (= docs/AGENT_RULES.md), `docs/` (this folder), `schemas/events.schema.json` (verbatim from Graption), `schemas/social_cue.schema.json` (docs/reference), `contracts/` (every file in CONTRACTS.md), an empty `app/__init__.py`, empty owned files for each track (so there are no add/add conflicts), `.github/pull_request_template.md` (= TASKS/PR_TEMPLATE.md), `PROGRESS.md` (= TASKS/PROGRESS.md), and branch protection or the simple rule that only the orchestrator merges.
2. Push. Everyone clones and creates their branch. **Contracts are now frozen.**

## Branches
`c1/backend`, `c2/live`, `c3/hud-recap`, `c4/demo-data`, `c4/glasses` (or `cN/glasses` if reassigned). PRs are small (one task or milestone) and titled `[C1][A2] Grok client`. After each merge, rebase: `git fetch && git rebase origin/main`.

## Sync points (fixed)
| Minute | Sync |
|---|---|
| 0-8 | Contract freeze (above) |
| 30 | **Merge 1:** orchestrator merges ready PRs in order D → A → C → B (→ E). Everyone rebases. Smoke test: demo mode on the real backend. **E go/no-go** (no glasses frames means E stops). |
| 55 | **Merge 2:** same order. Live mode + recap on the real backend with a key. |
| 70 | **Feature freeze.** Final merge (E only if working). Bug fixes go through tiny PRs from the file owner; the orchestrator fast-merges them. |
| 70-90 | Dry runs (DEMO_SCRIPT.md). |

Merge order rationale: D brings data and canned output the backend imports, A brings the server, C's `app/cues.py` is imported by A (A uses a stub until Merge 1, see Track A), and B is the pure consumer.

## Rules for every agent
Paste at the top of every prompt: *"Read CLAUDE.md, docs/CONTRACTS.md and docs/TASKS/<your track>.md. Edit only the files your track owns. Do not change contracts/ or schemas/. If you need a contract change, stop and tell me."*
Cross-track bug? Note it in your PR; the orchestrator routes it to the owner. Don't edit their file.
