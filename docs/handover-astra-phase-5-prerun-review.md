# Phase 5 pre-run review — handover for GPT-6 Astra

Written 2026-09-12 against commit `0be3e3b` on `main` (pushed; `git status` clean, 307 tests
pass, `tools/validate_spec.py` reports zero errors). Supersedes nothing — this is the next step
inside `docs/handover-phase-5.md`, which is still the authoritative scope document. Read that
file first if you have not already; this one assumes it.

## Why you, and why now

Per the standing operating principle: **Astra decides what to build and whether it is correct;
Claude does the building; Codex takes hard repo-level fixes.** Claude has finished essentially
all of the offline engineering `docs/handover-phase-5.md` assigned to it for this slice. What is
left is exactly the reasoning work that document reserved for you — and it needs to happen
**before** any billed API call, not after. Do not treat this as a code-review pass; the tests
already prove the code does what it claims to do. Your job is to judge whether what it claims to
do is the *right* thing, and to make three decisions the engineering work cannot make for itself.

## What actually shipped (verified, not just reported)

Confirmed directly in this session, not taken on faith from the implementation report:
- `git log`: commit `0be3e3b` — "strengthen classifier invariants, wire approval into export, add
  live-run entry point" — is on `main` and pushed to `origin/main`.
- `python -m unittest discover -s tests`: **307 tests pass** (up from 252 before this slice).
- `python tools/validate_spec.py`: **zero errors**.
- `work/phase2/calibration-smoke/manifest.json` (git-ignored, local only) exists and matches the
  reported shape: **11 articles, 11 of 12 required categories**, selected by title/publisher/
  access-status metadata only (`selection_method` field states no gold or evaluator file was
  read), frozen with a recorded `article_ids_sha256`.

New/changed modules worth reading before you decide anything below:
- `tools/classifier.py` — added `_validate_relevance_semantics` and evidence-reference validity
  checks: Level A now requires a resolved entity + `identity_gate: pass` + role-establishing
  identity; Level B requires a sector plus a substantive trigger/mechanism (not just a sector tag);
  Level C requires a non-generic trigger/mechanism naming a real consequence category. Also added
  `build_inference_settings`/`settings_hash`, threaded into every hash and raw-output record so two
  runs with different sampling/temperature settings can never collide or be silently conflated.
- `tools/run_model_experiment.py` — the actual entry point for a live or replay-only run: freeze
  preflight → provider → `StructuredClassifier` → `runner.run` → a manifest recording provider,
  model, settings hash, usage and latency. Never reads labels.
- `tools/providers/anthropic_provider.py` — a real Messages API adapter (fetched current docs at
  implementation time per the standing instruction), transport-level retry/timeout kept separate
  from the classifier's schema-level retry, 9 tests against an injected fake client (no network).
- `tools/claims.py` — deterministic regex-based amount/figure extraction grounded to a verbatim
  evidence span; a drafted card can cite a number but never invent one.
- `tools/reviewed_export.py` — the approval-ledger-gated export path: only an exact
  `(event_id, revision, content_hash)` triple with a recorded approval is exported. Five required
  invalidation scenarios are tested (pending, rejected, approved, content changed, revision bumped).

## What is genuinely blocked

**No live model call has been made.** `ANTHROPIC_API_KEY` is not set in this environment, and no
provider/model/spending-cap authorization has been given by the user beyond the earlier "skip live
inference for now" answer during Phase 4. The four dispositions Claude reported are accurate and
should not be restated as anything stronger:
1. `phase2_deterministic_baseline`: FAIL (unchanged — 75%/14.3%/1-of-2 vs. 90%/85%/100% bars).
2. `historical_model_comparison`: not run.
3. `reviewed_demo_ready`: not passed (no analyst approval this session).
4. `automated_selection_readiness`: inconclusive, pending a fresh temporal validation.

## Your three decisions, before anyone authorizes a billed call

### 1. Are the Level A/B/C invariants in `classifier.py` actually correct?

Read `_validate_relevance_semantics` (and its tests in `tests/test_classifier.py`) against
`docs/editorial-rulebook.md`'s "A/B/C eligibility" table and the "Ordered decision rules" (ED01-
ED09), not against the code's own docstring. The specific question: does requiring "a sector plus
a substantive trigger/mechanism" for Level B, and "a non-generic trigger/mechanism naming a real
consequence category" for Level C, actually match the rulebook's standard — or is it now stricter
or looser than intended? The rulebook's worked failure cases are a good check: "One irrelevant peer
headline generalized to all private credit is not Level B" and "'Rates matter to markets' without
event-specific consequences is not Level C." Confirm the validator would actually reject those two
and accept the rulebook's positive examples (comparable BDC credit-quality deterioration; a policy
change with a specific borrower-coverage mechanism). If you find a gap, specify the exact fix
(schema field or validation rule), not just "tighten this" — that goes back to Claude as a scoped
ticket, not a rewrite invitation.

### 2. Is an 11-of-12-category calibration set sufficient to freeze and proceed?

`work/phase2/calibration-smoke/manifest.json` is missing `high_materiality_outside_scope_negative`
— a high-materiality event with no monitored-entity/sector connection at all, i.e. the case that
should score high on "this looks important" but correctly fail the identity/relevance gate. That
category exists specifically to catch a scorer that confuses magnitude with relevance. Decide:
(a) proceed with 11 categories and treat the gap as a documented limitation of this smoke run, or
(b) require one more calibration article search before freezing further, and if so, state the
search criteria precisely enough that it doesn't become gold-informed article selection (must stay
title/publisher/access-status only, never touch labels or event groups). Do not silently accept
the gap without recording the decision, and do not block indefinitely searching for a perfect one.

### 3. What is the one allowed calibration-driven prompt repair, precisely?

`docs/phase-4-plan.md` (slice 4B) permits **at most one** bounded prompt repair after the
calibration smoke run, before the prompt/config/model is frozen for the full comparison. Define,
in advance, the decision rule for when to spend that repair — for example: "a repair is justified
only if ≥3 of the 11 smoke articles fail on the same identifiable prompt-context gap (e.g., a
missing rule the model needed and didn't have), not for a single miscalibrated score, an unlucky
sampling draw, or a borderline A/B/C call a human would also find genuinely ambiguous." Write the
actual rule you want applied — this document is not asking you to approve a placeholder, it is
asking you to author the rule, since no one else has editorial authority to decide when a prompt
change is warranted mid-experiment. Also state explicitly what evidence must be recorded when the
repair is used (before/after prompt hash, which articles motivated it, what changed) so it can be
audited afterward as bounded and disclosed rather than silent tuning.

## What is not your job right now

- Do not write or edit code. If your review finds a defect, describe it precisely enough for
  Claude to fix as a scoped ticket.
- Do not pick the provider/model or authorize spend. That authorization is the user's decision;
  your role is to make sure the engineering and the calibration design are sound *before* they
  spend money on it. If you have a recommendation on model choice (e.g. which current Claude or
  GPT tier best fits a bounded structured-classification task at this cost/quality point), state
  it as a recommendation for the user to approve — do not treat it as decided.
- Do not review classifier *outputs* yet — there are none. That review (the sampling routine
  described in `docs/handover-phase-5.md`: all selected cards, highest-scoring rejections,
  lowest-confidence cases, a random sample of the rest) is the next Astra task, after a live or
  replay run actually produces predictions.

## Definition of done for this review

A short written verdict on each of the three decisions above (accept as-is / accept with a named
gap / send back with a specific fix), plus the authored prompt-repair adjudication rule verbatim,
addressed back to whichever engineer (Claude or Codex) picks up the next slice. If you accept
everything as-is, say so explicitly rather than leaving silence to be read as approval.
