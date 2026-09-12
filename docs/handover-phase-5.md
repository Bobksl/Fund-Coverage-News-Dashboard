# Phase 5 handover — multi-model, Astra-led

Written 2026-09-12 against commit `de423f8` on `codex/phase-1-editorial-spec` (pushed to
`origin/codex/phase-1-editorial-spec`). Supersedes `docs/handover-claude-phase-4.md`, which this
phase's work closed except for the one slice deferred below.

**Primary recipient: GPT-6 Astra** (architect / investment-reasoning engine / senior reviewer).
**Secondary recipient: Claude Sonnet 5** (bulk implementation). **Tertiary: Codex** (repo-level
integration/debugging). See "Model allocation for this phase" below before assigning any task —
do not default everything to the strongest model.

## Where the project actually is

Read in order before doing anything:
1. `docs/phase-4-plan.md` — still the authoritative review and acceptance criteria; only 4B is open.
2. `docs/demo-readme.md` — current run commands and honest capability list, updated this phase.
3. `docs/phase-2-disposition.md` — the deterministic-baseline FAIL that must not be erased or reframed.
4. `tools/classifier.py`, `tools/drafting.py` — the injected-provider adapters, now carrying the
   full manager ontology, scoring definitions and stricter nested validation.
5. `tools/approval_ledger.py`, `tools/export_demo.py` — new this phase; the review sign-off and
   isolated-serving mechanisms.
6. `git log -3` / `git diff 15c11c7..de423f8` — the actual Phase 4 change, not a paraphrase of it.

**Phase 4 (slices 4A, 4C, 4D) is done and tested.** 252 unit tests pass (33 new this phase), the
spec validator reports zero errors, and a real browser check confirmed safe rendering (a
hostile-title/`javascript:`-URL synthetic card renders as inert text, no script fired), the
honest today/empty state, the historical-jump shortcut, and per-day capacity with the challenge
cohort excluded from the ordinary calendar. None of this used a live model.

**Slice 4B — the bounded model comparison — was explicitly deferred**, not attempted and failed.
When asked, the user chose "skip live inference for now" over naming a provider. That is the one
open item this phase inherits. Everything else in `docs/phase-4-plan.md`'s acceptance table is
either met or honestly reported as not met (see the two dispositions at the end of the previous
handover: `reviewed_demo_ready` not passed, `automated_selection_readiness` FAIL, both unchanged
by design).

Do not reopen or re-litigate 4A/4C/4D. Do not re-scaffold the pipeline. Continue from `next_action
= complete_4B_then_real_analyst_review`.

## What Phase 5 actually is

This is **not** a generic "Phase 5: database/backend" slot. This repository has no database and
no backend service by design (`docs/phase-4-plan.md`: "Keep Python + files + vanilla HTML/JS. No
Next.js, hosted database, cron..."), and the static UI/export work that a generic project
template would call "Phase 6: frontend" is also already done (`site/`, `tools/export_demo.py`).
Map this project's remaining work onto the *generic* AI-project phase model like this before
assigning anything:

| Generic phase (reference) | Status here |
|---|---|
| 0 Product spec | Done (Phase 1 ontology/rulebook) |
| 1 Ontology + editorial rules | Done — `config/*.json`, `docs/editorial-rulebook.md` |
| 2 Filtering prototype | Done — deterministic baseline, measured FAIL (`docs/phase-2-disposition.md`) |
| 3 News ingestion | **Not done.** Phase 3 here delivered a mechanics demo on a frozen historical corpus, not a live collector. Out of scope for Phase 5 unless explicitly authorized — do not start it as a side effect of 4B. |
| 4 AI intelligence pipeline | Adapter, prompt, schema and validation done (this phase); **live inference not yet run** — this is the actual Phase 5 task |
| 5 Database/backend | N/A by design |
| 6 Frontend/dashboard | Done — `site/` + `tools/export_demo.py` |
| 7 Calibration/QA | Partially blocked on 4B; the analyst-review half (approval ledger) is built and unused |
| 8 Deployment/handover | This document |

So **Phase 5 = finish the generic "Phase 4: AI intelligence pipeline" + the calibration half of
"Phase 7"**: connect one real provider, run the bounded comparison, then close the loop with an
actual human analyst review through `tools/approval_ledger.py`. Do not start a live news
collector (generic Phase 3) under this handover; that needs its own explicit scope decision.

## Model allocation for this phase

Operating principle, unchanged from the user's standing instruction: **Astra decides what to
build and whether it is correct; Claude does most of the building; Codex takes the hard
repo-level integration/debugging.** Concretely for the work above:

**Astra High** — before any billed call:
- Confirm the classifier response schema (`tools/classifier.py:REQUIRED_OUTPUT`,
  `_validate_output`) and the ontology now embedded in `build_prompt` are actually sufficient for
  a real classification experiment; this is a reasoning review, not a re-read of the code.
- Design or approve the 10-15 article calibration set selection criteria (must be chosen *before*
  seeing model output — `docs/phase-4-plan.md` slice 4B): direct vehicles, sector-only relevance,
  macro transmission, ambiguous roles, irrelevant marketing, inaccessible evidence.
- Define the adjudication rule for the *one* allowed calibration-driven prompt repair: what
  failure pattern justifies it, what does not.
- After the calibration + historical-holdout run completes, review the actual outputs —
  borderline cases, false positives/negatives, confidence — and adjudicate whether the
  classification method is viable. Do not have Astra re-read every passing case; sample per the
  routine described in the standing instruction (all selected cards, the highest-scoring
  rejections, the lowest-confidence cases, a random sample of the rest).

**Claude Sonnet 5 Medium** — implementation:
- Write the actual provider-callable (the function passed to `classifier.StructuredClassifier`
  and `drafting.Drafter` as `provider`) for whichever API is authorized: request construction,
  timeout/retry at the transport level (the adapter already retries at the schema level), and
  populating `usage` (`input_tokens`, `output_tokens`, `cost_basis`) from what the provider
  actually reports — never invented.
- Run the synthetic contract tests, then the calibration smoke run, save raw outputs via
  `RawOutputStore` before any evaluator access, and freeze prompt/config/model parameters
  (`tools.corpus.freeze_record` / `verify_freeze`) before the full comparison.
- Once cards exist, exercise `tools/approval_ledger.py` for a real reviewer's approve/reject
  decisions (a human analyst, never a model — `docs/editorial-rulebook.md`: "This is an explicit
  editorial judgement, not a model-selected bypass") and re-run `tools/export_demo.py` so only
  approved revisions are exported.
- Write the focused tests this slice needs: a live-shaped provider stub that returns realistic
  malformed/partial responses, cost/usage aggregation, and an end-to-end
  calibration-run-then-freeze-then-evaluate test using synthetic (not real) evidence.

**Codex High** — only if Claude gets stuck on: provider SDK integration quirks, concurrency/retry
edge cases across a real batch run, or a test failure that spans classifier/drafting/runner/
evaluator simultaneously. Not a default assignment.

**Do not use Astra for:** writing the HTTP client, wiring retries, formatting JSON, or anything
`docs/phase-4-plan.md` already fully specifies mechanically. That is exactly the "commodity
coding" this allocation exists to keep off the expensive model.

## Constraints carried forward unchanged

- Read current official provider docs at implementation time; do not invent a model name or
  pricing from this or any prior handover.
- Never read or expose credential values in any report, log, or committed file.
- Inference must run in fresh context containing only allowlisted source evidence and public
  editorial config — never this or any prior conversation's gold labels, event IDs, rationale,
  challenge categories, or evaluator files.
- The old (Phase 2) holdout is a disclosed historical comparison, not a newly sealed validation.
  A future automated-readiness claim needs a fresh temporal holdout with sufficient independently
  labeled publish-worthy events — do not recollect data just to make a demo pass, and do not pad
  or resize the existing challenge cohort after seeing results.
- `freeze-001`/`run-001` stay immutable. All private artifacts stay under ignored `work/`. No
  force-add, history rewrite, `.git` deletion, or remote push without explicit authorization
  (this phase's Phase 4 commit was pushed only after the user explicitly said "push it").
- Benchmark publish labels are never card approval. Only `tools/approval_ledger.py` rows written
  by a named reviewer count. Export only the exact approved revision (hash-checked).
- Validate with the full unittest suite, spec validator and a real browser check before reporting
  done. Add focused tests for the new behavior (see above). Do not weaken tests to route around
  environment issues; record those separately.

## Definition of done for Phase 5

Report, honestly:
- Actual provider/model ID, parameters, prompt/config hashes, raw outputs and reported usage —
  or, if authorization is still missing, that this phase also ended without a live run.
- Calibration and historical-holdout metrics, reported separately from each other and from the
  Phase 2 baseline, with the same rigor (precision/recall/must-not-miss, false merges/splits,
  review-required rate, costs and latency).
- Whether any card actually received a recorded analyst approval this time — if not,
  `reviewed_demo_ready` stays not-passed; do not report review-readiness on `pending_review`
  cards.
- An updated `automated_selection_readiness` disposition against the real Phase 2 submission
  standard (Sharpe-equivalent for this project: precision ≥90%/recall ≥85%/must-not-miss 100%
  from `docs/phase-2-experiment.md`'s bars) — pass, fail, or inconclusive, never "success" on an
  untested or partially tested model.
- Remaining input needed from the user, if any, stated once and precisely (not a re-ask of
  something already answered in this handover chain).
