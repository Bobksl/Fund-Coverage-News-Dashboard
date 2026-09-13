# Phase 6 handover — one real, human-reviewed bilingual edition

Written 2026-09-13 against commit `cb96b53` on `main` (pushed; `git status` clean, 345 tests pass,
`tools/validate_spec.py` reports zero errors). Read `docs/phase-5-live-run-log.md` and
`docs/phase-5-review-decisions.md` first — they are the record of how Phase 5 actually closed and
must not be re-litigated here.

## Where Phase 5 actually ended, and why

Phase 5's live-model work ran a 9-article calibration **smoke** test against DeepSeek
`deepseek-flash` (Stages 1–2 of `docs/handover-phase-5.md` section 9), including one diagnosed
token-budget failure (v1), one genuine specification gap found and fixed via the single allowed
prompt repair — `evidence_refs` values were `"title"`/`"body"`/quoted excerpts instead of the
required `article_id` (v2 → repair → v3) — and one real crash bug found and hardened
(`primary_event_type` returned as a nested object; `tools/classifier.py`'s enum checks are now
type-safe against any unhashable model output, not just this one shape).

**The full calibration partition (57 natural-feed articles) and historical holdout (21 articles) —
Stages 3–4 — were never run.** The remaining budget after the smoke run (~¥4 of an original ¥6.59
cap) does not credibly cover a batch 8–9× larger. Rather than leave that dangling, **the user has
made an explicit scope decision: defer Stages 3–4, and the challenge diagnostics (Stage 5), to
Phase 7, to be executed by Codex with its own budget authorization.** Phase 5 is closed on that
basis. Do not reopen it or re-attempt the full calibration/holdout run under this phase 6 handover.

Final Phase 5 dispositions (do not restate these as anything stronger):
1. `phase2_deterministic_baseline` = **FAIL** (unchanged, historical).
2. `historical_model_comparison` = **not_run** (explicitly deferred to Phase 7 — not
   `meets_bars`/`fails_bars`/`inconclusive`; genuinely not attempted at scale).
3. `reviewed_demo_ready` = **not_passed** at the moment Phase 5 closed — **this is what Phase 6
   exists to change**, honestly, for one real card.
4. `automated_selection_readiness` = **inconclusive_pending_fresh_temporal_validation** (unchanged;
   stays true even after Phase 7 runs, since a historical holdout re-use is disclosed reuse, not a
   fresh prospectively-frozen temporal holdout — see `docs/phase-5-review-decisions.md`).

## What Phase 6 actually is

**Not** a bigger model run. Phase 6 finishes the smallest complete, honest version of the actual
product loop — `frozen evidence → classification → claims → bilingual draft → real human
approval → approved-only export` — using the one real, credible result Phase 5's smoke run
already produced, rather than waiting on Phase 7's larger budget to produce more:

**Event:** `edf49c19-e476-542a-9a5e-bae5e211812d` — "Blue Owl Technology Finance Corp. Closes $150
Million Private Placement of Senior Unsecured Notes." Classified Level A, `shortlist`, total score
76, in `calib-smoke-deepseek-flash-v3` (`work/phase2/live-runs/calib-smoke-deepseek-flash-v3/`,
git-ignored — read it directly, don't re-derive). This is a real capital-formation event for a
tracked manager's own vehicle (OTF), correctly distinguished from the manager itself per
`docs/phase-5-review-decisions.md`'s manager-vs-vehicle fix.

### Steps

1. **Build grounded claims.** `tools/claims.py:claims_for_decision` (or
   `extract_amount_claims`/`manual_claim` directly) against the evidence body in
   `work/phase2/evidence-store/`. The article has real figures worth extracting: the $150 million
   note issuance, the 7.60% coupon, and the $800 million cumulative financing figure. Every claim
   must be a verbatim span from the actual body text — do not invent or round a figure.
2. **Draft the bilingual card.** `tools/drafting.py:Drafter`, with the DeepSeek provider adapter
   (`tools/providers/deepseek_provider.py`) already built and working — reuse it, do not rebuild
   it. Budget note: a drafting call is roughly the same size as one classification call (~1–2 more
   calls against the remaining ~¥4 balance is trivial; confirm the credential is still the one
   already in the local, git-ignored `.env` — never re-request or re-paste it, and never commit
   it). Validate EN/ZH parity per `tools/drafting.py:validate_card` before treating the card as
   ready.
3. **Get an actual human review.** The user reviews the drafted card content (headline, summary,
   interpretation, EN/ZH parity) and records approve/reject via
   `tools/approval_ledger.py:append_review` with a real `reviewer_id` — never a model, never this
   session self-approving. If rejected or edited, redraft and re-review; only the exact approved
   `(event_id, revision, content_hash)` counts.
4. **Export.** `tools/reviewed_export.py:write_reviewed_feed`, producing one real dated edition
   under a new git-ignored output directory (do not overwrite `work/phase2/demo-feed/`, which is
   the baseline-mechanics demo and must stay visibly separate per `docs/demo-readme.md`). Package
   with `tools/export_demo.py`'s pattern (an isolated `work/`-rooted export directory, served on
   `127.0.0.1` only) or extend it to also serve the reviewed feed — your call, but keep the
   baseline-mechanics and analyst-reviewed feeds distinguishable in the UI, never silently merged.
5. **Browser-verify** the exported reviewed edition: the approved card renders with correct EN/ZH
   toggle, source link, and figures; nothing evaluator-only or credential-bearing is exposed in the
   served directory (reuse the checks in `tests/test_export_demo.py` as a template for what to
   verify by hand).
6. **Update the four dispositions.** If step 3 actually approves the card:
   `reviewed_demo_ready` = **passed**, with the caveat that it covers exactly one card, not a full
   edition, and say so explicitly rather than implying broader readiness. If the user rejects it
   after review, that is a legitimate, complete Phase 6 outcome too — record
   `reviewed_demo_ready = not_passed` with the reviewer's stated reason, not a forced retry loop.

### Constraints carried forward, unchanged

- No gold label, event group, rationale, or evaluator file crosses the inference boundary at any
  step — same allowlist discipline as every prior phase.
- The credential lives only in the local, git-ignored `.env`; never printed, never committed, never
  written into any run manifest or exported artifact.
- `freeze-001`/`run-001` and the calibration-smoke manifests (`v1`/`v2`/`v3`) stay immutable. Any
  new artifact from this phase goes under a new, clearly-named path in git-ignored `work/`.
- No scope creep: no live news collection, no backend/database, no new scoring weights tuned to
  this one card, no second model call pattern beyond drafting the one card above.
- Full test suite + `validate_spec` + `git diff --check` clean before calling this phase done, same
  bar as every prior phase.

## What is explicitly Phase 7's job, not Phase 6's

> **Scope correction (P7-1, 2026-09-13):** "57 articles" / "21 articles" below are publish-worthy
> event counts, not article counts. Phase 7's frozen scope is 188/56/30 = 274 article inputs; see
> `docs/phase-7-scope.md`.

- The full calibration partition (57 articles) and historical holdout (21 articles) — Stage 3–4 of
  the original Phase 5 sequence — run against the same frozen prompt (`p2`) and settings this phase
  established, under Codex's own budget authorization. Do not start this under Phase 6.
- Challenge diagnostics (Stage 5), reported separately from natural-feed results as always.
- Any prompt/schema change discovered during that larger run needs its own repair adjudication —
  the one repair used in Phase 5 (`evidence_refs` format) does not carry forward as a second
  allowance for Phase 7's larger batch; a new, independent one-repair budget applies there if
  needed, following the same policy in `docs/phase-5-review-decisions.md`.
- A fresh, prospectively-frozen temporal holdout with independently labeled positive events —
  the only thing that can move `automated_selection_readiness` off `inconclusive` — remains out of
  scope for both Phase 6 and Phase 7 unless separately authorized.

## Definition of done for Phase 6

- One real bilingual card exists, drafted from grounded claims, with EN/ZH parity validated.
- A named human reviewer's approve/reject decision is recorded in `tools/approval_ledger.py`.
- If approved: exported via the approval-gated path and verified in a real browser.
- All four dispositions restated accurately, with `reviewed_demo_ready` updated honestly based on
  what actually happened in step 3 above.
- Tests/validator/diff-check clean; nothing committed that shouldn't be (credentials, gold labels,
  evaluator files).
