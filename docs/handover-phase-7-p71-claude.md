# Phase 7 handover — close ticket P7-1 (the last pre-execution blocker)

Written 2026-09-13 against commit `0f3c1e6` on `main` (pushed; `git status` clean, 367 tests
pass, `tools/validate_spec.py` reports zero errors, `git diff --check` clean). Read, in order:
`docs/phase-7-pre-execution-review.md` (the full pre-execution audit — you are closing exactly
one of its four tickets), `docs/handover-phase-7-astra.md`, `docs/phase-6-completion.md`. Do not
re-derive what those already establish.

## Where things actually stand

Codex ran a pre-execution audit of Phase 7 (the full 57-article-scale calibration run, deferred
from Phase 5/6) and found the gate BLOCKED on four tickets: P7-1 through P7-4. Claude (this
session's predecessor) implemented P7-2, P7-3 and P7-4 in full — including wiring
`tools/inference_budget.py`'s spend ledger into `tools/providers/deepseek_provider.py` (it existed
and was unit-tested but was never actually called before) — and fixed two regressions the audit's
own changes had introduced. All of that is committed and pushed (`0f3c1e6`). **P7-1 is the one
ticket left, and it is not a bugfix — it's a data/policy reconciliation task.** No one has
authorized a spending cap yet; that is a separate, later step for the user, not for you to request
or assume.

## What P7-1 actually is (quoted from the audit, `docs/phase-7-pre-execution-review.md`)

> **P7-1 — Freeze the actual Stage D scope.** Failure: the handover describes 91 challenge
> probes, but the immutable split lists 30 and excludes two source records before partitioning.
> Change: record the 188/56/30 governing membership and explicit exclusions; optionally add a
> separately named, hashed 59-input linked replay diagnostic manifest without changing
> freeze-001. Verify exact IDs, counts, disjointness/overlap, and prompt-input hashes, using only
> ID projections of the registry. Synthetic test: overlapping cohort IDs replay once, excluded IDs
> cannot enter the frozen comparison, and same article with different settings cannot replay
> (already covered elsewhere — see below). Prompt/schema change: no. New live smoke: no.

**Concretely, what this means and where the data already lives** (verify these yourself; do not
trust this summary blindly):

- `work/phase2/freeze-001/split-manifest.json` is the **already-frozen, immutable** source of
  truth: `natural_feed.calibration` (188 article IDs), `natural_feed.holdout` (56 article IDs),
  `challenge.article_ids` (30 article IDs). These three lists, 274 IDs total, are the actual Phase
  7 Stage A–D scope. **Do not modify this file. It is frozen (`freeze-001`) and immutable.**
- `work/phase2/challenge/challenge-registry.jsonl` is a **broader, 91-record, evaluator-only**
  registry (curated probe categories, coverage minimums — see
  `work/phase2/challenge/coverage-report.json`) that some earlier handover language imprecisely
  called "the challenge scope." It is not the frozen scope. Per the audit: 59 of its 91 records are
  "linked" natural-feed probes (present in `natural_feed.calibration`/`natural_feed.holdout`
  already), and 32 are independent challenge-only records — of which only 30 made it into the
  frozen `challenge.article_ids` (two are excluded upstream: `f6400cea-3e84-5bd7-b063-5a3aa338d076`,
  already labeled elsewhere and not independent, and `e0f8d0fc-e619-5649-85cb-950a8c028ce9`,
  undated). **`challenge_category`/`selection_reason` fields in this registry are evaluator-only
  per `tools/records.py:EVALUATOR_ONLY` — an ID projection (article IDs alone) is fine to move
  around; those fields must never cross into anything the classifier reads.**
- **Correction (found while closing P7-1):** by the registry's own `linked_natural_feed_article_id`
  projection it is **60 linked / 31 independent**, as the audit says, not 59/32. 59 of the 60
  linked probes are frozen natural-feed inputs; the 60th is the quarantined `f6400cea…`. 30 of the
  31 independent probes are the frozen challenge partition; the 31st is the undated `e0f8d0fc…`.
  See `docs/phase-7-scope.md`.
- Running "all 91 registered probes" is explicitly **not authorized** — it was a scope
  illustration in the cost estimate, not a decision. Do not build tooling that defaults to it.

## Deliverables

1. **A canonical, git-tracked scope document** (e.g. `docs/phase-7-scope.md`) that states, in one
   place, the governing counts (188/56/30 = 274 unique classifier inputs), quotes or links the
   `split-manifest.json` fields it comes from, and explicitly records the two upstream exclusions
   and why each is excluded. This replaces any "91 challenge probes" framing wherever it appears in
   Phase 7-facing docs (check `docs/handover-phase-7-astra.md` and
   `docs/phase-7-pre-execution-review.md`'s Decision 3 cost table for where that framing already
   correctly says 274 vs. where a reader might still assume 91 — add a pointer/correction, don't
   silently rewrite the audit's own historical numbers).
2. **A frozen, hashed run-manifest artifact** (git-ignored, under `work/phase2/` — follow the
   existing pattern in `tools/corpus.py:runner_manifest`/`inference_manifest`) that
   `tools/run_model_experiment.py` can actually consume for Stage A (calibration), Stage B/C
   (holdout), and Stage D (challenge) — i.e., three manifests (or one with three named partitions)
   whose `article_ids` are exactly the 188/56/30 lists above, each with a SHA-256 of its own ID
   list for later verification (mirror `tools.select_calibration_smoke.build_manifest`'s
   `article_ids_sha256` pattern).
3. **Optionally**, a separately named, hashed 59-article "linked diagnostic" manifest (the natural
   articles that also appear in the broader 91-registry) — purely a replay-only diagnostic view,
   never mixed into the 274-input frozen comparison, and never given its own live billed run. Build
   this only if you can do it cleanly from ID projections alone; skip it if it adds risk of
   confusing the two scopes rather than clarifying them.
4. **Synthetic tests** (new test file, e.g. `tests/test_phase7_scope.py`) proving, on real project
   data (not just fixtures — read the actual frozen files) or on a faithful synthetic
   reproduction if you decide reading the real 274-ID lists into a test is impractical:
   - The 188/56/30 lists are pairwise disjoint (zero overlap between calibration, holdout,
     challenge).
   - The two named excluded article IDs are absent from all three lists.
   - The frozen manifest's article-ID hash is stable (same input → same hash) and changes if any
     ID is added/removed.
   - If you build the supplementary 59-ID diagnostic manifest: every one of its IDs is present in
     `natural_feed.calibration` or `natural_feed.holdout`, and it is never accepted as an input to
     whatever function/CLI path would trigger a live/billed run (only a replay-shaped path, if one
     exists, or simply: it is a data artifact with no run entry point at all — your call, state
     which).
   - Do not re-implement the "same article, different settings, does not replay" test — that's
     already covered by `tests/test_phase7_accounting.py::Phase7AccountingTests::
     test_different_settings_do_not_replay_the_same_article`. Confirm it still passes; don't
     duplicate it.

## Constraints (same as every prior phase — do not relitigate these)

- **No gold label, event group, challenge category, selection reason, or any other
  `tools.records.EVALUATOR_ONLY` field may cross into anything the classifier/drafter reads.**
  Use `tools.records.leakage_scan` to check any new payload you build, the same way existing code
  does.
- **`freeze-001` (both `freeze-record.json` and `split-manifest.json`) is immutable. Do not edit
  it, do not regenerate it, do not "fix" its numbers even if you think a different split would be
  better** — that would silently invalidate the historical-comparison hash chain. Your job is to
  correctly *read and reconcile documentation against* this frozen artifact, not change it.
- **No live provider call, no spending.** This ticket is pure data/documentation/test work. If you
  find yourself wanting to run `tools/run_model_experiment.py` against a real credential to verify
  something, don't — verify structurally instead (hashes, ID-set operations, existing replay
  fixtures).
- **No new prompt/schema repair.** P7-1 explicitly does not touch the classifier prompt
  (`tools/classifier.py:RESPONSE_CONTRACT`/`PROMPT_RULES`) or `p2`/`rc4`. If you think you've found
  a reason to change either, stop and report it separately — don't fold it into this ticket.
- Full test suite + `tools/validate_spec.py` + `git diff --check` must be clean before you call
  this done, same bar as every prior phase. Commit and push when finished, with an honest message
  (what was reconciled, what remains ambiguous if anything, exact new/changed file list).

## What is explicitly NOT your job here

- Approving or recommending a spending cap — Codex's audit already recommended a provisional
  $25 figure with its full reasoning (Decision 3 of `docs/phase-7-pre-execution-review.md`); that
  number stands or gets revisited by the user, not by you re-deriving it.
- Running Stage A/B/C/D against a live provider.
- Reopening the closed Phase 5/6 classifier-semantics decisions
  (`docs/phase-5-review-decisions.md`) or the P7-2/P7-3/P7-4 implementation just landed in
  `0f3c1e6` — read them to understand context, don't re-review or re-implement them.

## Definition of done

- `docs/phase-7-scope.md` (or equivalent) exists and unambiguously states 188/56/30/274 as the
  frozen scope, with the two exclusions named and explained.
- A frozen, hashed manifest artifact exists under git-ignored `work/phase2/` that
  `tools/run_model_experiment.py` (or a thin wrapper around it) could actually consume for each of
  Stage A/B/D without further reconciliation work.
- New tests pass; full suite, `validate_spec`, `git diff --check` all clean.
- Committed and pushed, with the gate status restated: this ticket closing does not by itself mean
  **PRE-EXECUTION GATE: READY** — say explicitly whether you believe all four P7 tickets are now
  closed (they should be, after this) and that the only remaining blocker is the user's explicit
  spending-cap authorization, or name anything else you found that still blocks it.
