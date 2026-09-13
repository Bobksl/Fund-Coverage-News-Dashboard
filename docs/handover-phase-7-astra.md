# Phase 7 handover — pre-execution review for GPT-6 Astra

Written 2026-09-13 against commit `83432ad` on `main` (pushed; `git status` clean, 346 tests
pass, `tools/validate_spec.py` reports zero errors). Read, in order: `docs/handover-phase-6.md`,
`docs/phase-6-completion.md`, `docs/phase-5-live-run-log.md`, `docs/phase-5-review-decisions.md`.
This document assumes all four and does not repeat their content.

## Why you, and why now

Per the standing operating principle carried from Phase 5: **Astra decides what to build and
whether it is correct; Codex builds/executes; Claude does the surrounding engineering.** For Phase
7 specifically, the user has designated **Codex as the execution owner** of the full calibration
run — a departure from Phase 5/6, where Claude did the implementation. Your job is the same kind of
job you did before Phase 5's live call: **review whether what's frozen is actually ready for a run
roughly 8–9× larger than anything tested so far, before Codex spends a real budget on it.** This is
not a request to re-litigate Phase 5/6's findings — those are closed. It is a request to judge
whether closing them was *sufficient* for the next scale of run, which is a different question.

## What is actually frozen and verified (do not re-derive; verify against the paths given)

- **Prompt version `p2`, response-contract version `rc4`** (`tools/classifier.py`). The one Phase-5
  calibration-smoke repair (explicit `evidence_refs` format) is applied and tested. Astra's round
  1–3 review findings (entity role/involvement split, propagation-edge validation, non-object
  transmission guards, unhashable-enum-value guards) are all implemented and tested — see
  `docs/phase-5-review-decisions.md` for the itemized list and `tools/classifier.py`'s
  `_validate_relevance_semantics`/`_validate_entity_matches`/`_not_in` for the code.
- **Drafting prompt version `p2-draft3`** (`tools/drafting.py:build_prompt`'s `output_schema`
  block). One repair applied in Phase 6: an explicit flat-schema block, after a live call nested
  the card under `en`/`zh` groups with invented field names.
- **Provider:** DeepSeek `deepseek-flash` (`tools/providers/deepseek_provider.py`), confirmed live
  against real calls in Phase 5/6 — including the discovery that it is a reasoning model whose
  hidden `reasoning_content` consumes the same `max_tokens` budget as the visible answer.
  `max_output_tokens=16384` was sufficient for the classifier at smoke scale (9 articles; 3 of 9
  still fully exhausted the budget at 8192 before the increase — see
  `docs/phase-5-live-run-log.md`'s v2/v3 comparison) and for the one drafting call in Phase 6.
- **Calibration-smoke result (`calib-smoke-deepseek-flash-v3`, 9 articles):** 1 shortlist, 1
  correctly-suppressed marketing notice, 1 correctly-merged duplicate pair, 3 `review_required`
  from a since-fixed crash bug, 1 `review_required` each for the macro and wrong-strategy
  candidates. No gold label was used to judge this — it is a mechanics/behavior observation only.
- **One complete human-reviewed card exists** (Phase 6): classification → grounded claims →
  bilingual draft → named human approval → approval-gated export → browser verification, all for
  one event. `reviewed_demo_ready = passed, for exactly one card` — explicitly not a claim about
  throughput or editorial consistency at scale.
- **Two live-only defects found and fixed**, both of the same shape (a prompt never stating a
  required output format that a model then reasonably guessed at): classifier `evidence_refs`
  (Phase 5) and drafting's flat output schema (Phase 6). Both are now explicit in their respective
  prompts. **This is the pattern you should be alert for at Phase 7 scale — a third instance
  appearing (or the same two forms of gap resurfacing in a component not yet exercised, e.g.
  grouping across 57 articles instead of 9) would be a new finding, not evidence the pattern is
  now exhausted.**

## What Phase 7 actually is

> **Scope correction (P7-1, 2026-09-13):** the "57 articles" / "21 articles" below are
> publish-worthy *event* counts from `docs/phase-2-disposition.md`, not article counts. The frozen
> Phase 7 scope is freeze-001's **188 calibration / 56 holdout / 30 challenge = 274 article
> inputs**, not 91 challenge probes. `docs/phase-7-scope.md` is canonical; the text below is left
> as originally written.

The full natural-feed calibration partition (57 articles) and historical holdout (21 articles) —
Stages 3–4 of the original Phase 5 sequence (`docs/handover-phase-5.md` section 9) — plus challenge
diagnostics (Stage 5), reported separately from natural-feed results as always. This is the first
run at a scale where the historical-baseline comparison
(`docs/phase-2-disposition.md`: 75% precision / 14.3% recall / 1-of-2 must-not-miss against 90% /
85% / 100% bars) becomes actually comparable to a real `historical_model_comparison` disposition —
`meets_bars` / `fails_bars` / `inconclusive`, never "success."

**Not in scope for Phase 7** (unchanged from every prior phase): live news collection, a
backend/database, new scoring weights tuned to this run's results, and — this is the one Astra
should adjudicate explicitly below — **a fresh temporal holdout**. The 21-article "historical
holdout" is the same one from Phase 2, already inspected during development; running it again is
disclosed historical reuse, not a newly sealed validation, and cannot move
`automated_selection_readiness` off `inconclusive` no matter what it shows.

## Your three decisions before Codex starts

### 1. Is the frozen prompt/schema actually ready for 8–9× the tested scale?

The smoke run's 9 articles were hand-selected for category diversity (`work/phase2/calibration-
smoke/manifest.json`, `manifest-v1.json`/`v2.json` for the superseded selections). The 57-article
calibration partition and 21-article holdout were not selected for diversity — they are the actual
natural-feed populations from `docs/phase-2-disposition.md`. Decide: does anything about the
smoke's narrow, curated coverage (9 categories, one example each) mean the frozen prompt is
under-tested against article shapes the smoke never presented (e.g., `metadata_only` evidence,
multi-entity events with 3+ tracked managers, non-English source text if any exists in the
corpus)? If you find a gap, specify it as a scoped ticket for whoever fixes it (Codex, per this
phase's allocation) — not a mandate to redesign the schema again.

### 2. Does the one-repair budget reset for Phase 7, and under what rule?

`docs/phase-5-review-decisions.md`'s one-repair policy governed Phase 5's calibration smoke and was
used once (`evidence_refs`). Phase 6 used what `docs/phase-6-completion.md` calls "narrowly scoped"
repairs for drafting and export, explicitly *not* framed as extensions of the Phase 5 repair budget
because they fixed different components (drafting, export) that had never been exercised live
before. **Phase 7 is the classifier component again, at new scale, on data the frozen prompt has
never seen.** Decide and state explicitly: does Phase 7 get its own fresh one-repair allowance
(your Phase-5 policy, re-applied), or does "the classifier already had its one repair in Phase 5"
mean Phase 7 gets zero further repairs regardless of what the 57-article run surfaces? Either
answer is defensible; what matters is that Codex has a clear, pre-stated rule before running,
not an improvised one after seeing results.

### 3. What does Codex need authorized before it can start, precisely?

State the minimum: provider (already DeepSeek `deepseek-flash`, unless you recommend otherwise —
your call to make, not to be treated as decided), the exact `max_output_tokens`/temperature/
top_p settings to freeze (recommend keeping Phase 5/6's `16384`/defaults unless you see a reason
to change them, and if so, name it as a settings decision, not a repair), and a **budget estimate**
Codex should get explicit user authorization against before spending anything — extrapolate from
`docs/phase-5-live-run-log.md`'s actual per-article token costs (roughly 40,000 combined
input+output tokens per article across the smoke's three runs; do not assume this scales exactly
linearly, evidence length varies, but it is the only real data point available). State this as a
recommendation for the user to approve, not an authorization you are issuing yourself.

## What is not your job right now

- Do not write or execute code. Findings become scoped tickets for Codex.
- Do not authorize spend or pick the provider/model unilaterally — recommend, let the user approve.
- Do not review the 57+21 articles' actual classifier outputs — there are none yet; that is the
  next Astra task once Codex's run completes, following the same sampling routine as before (all
  selected cards, highest-scoring rejections, lowest-confidence cases, a random sample of the
  rest).
- Do not relitigate Phase 5/6's closed findings; your job here is forward-looking readiness, not
  a fourth review round of the same code.

## Definition of done for this review

A written verdict on each of the three decisions above (accept as-is / accept with a named gap /
send back with a specific fix), addressed to Codex as the next executor. If you accept everything
as-is, say so explicitly. State the pre-execution gate status plainly: **PRE-EXECUTION GATE:
BLOCKED** or **READY**, and if blocked, name the exact blocking item(s) — do not leave it
ambiguous, since Codex will read this document as its own starting brief.
