# Phase 6 completion — one real, human-reviewed bilingual card — 2026-09-13

Written against `main`, closing `docs/handover-phase-6.md`. Read that handover first for what
Phase 6 was scoped to do and why; this records what actually happened, including two genuine
defects found and fixed along the way, neither of which was known when the handover was written.

## What actually ran

**Event:** `pe-e3737767c25b` (article `edf49c19-e476-542a-9a5e-bae5e211812d`) — "Blue Owl
Technology Finance Corp. Closes $150 Million Private Placement of Senior Unsecured Notes", Level
A, `shortlist`, score 76, from `calib-smoke-deepseek-flash-v3`.

1. **Claims.** `tools/claims.py:extract_amount_claims` pulled the $150 million figure (matched
   twice, in the title-line and body) and the $800 million cumulative-financing figure verbatim
   from `work/phase2/evidence-store/edf49c19-e476-542a-9a5e-bae5e211812d.txt`. The 7.60% coupon is
   not a currency amount, so it was added as a hand-verified `tools.claims.manual_claim` with
   `evidence_span="7.60% senior unsecured notes"`, confirmed as a literal substring of the body.
2. **Drafting — one genuine spec gap found and repaired.** The first two live `deepseek-flash`
   calls (via `tools/drafting.py:Drafter` + the existing `DeepSeekProvider`) both came back
   `review_required`. Attempt set 1 (max_output_tokens=4096) returned empty content — the model
   spent its entire token budget before emitting visible JSON, the same reasoning-budget failure
   mode Phase 5 diagnosed for the classifier (`docs/handover-phase-5.md` section 9's v1). Raising
   to 16384 (matching the classifier's setting) fixed that, but exposed a second, different
   problem: the model returned a nested `{"event_identity":..., "en":{"factual_summary":...,
   "investment_interpretation":...}, "zh":{...}}` shape instead of the flat `headline_en`/
   `summary_en`/`interpretation_en`/`headline_zh`/`summary_zh`/`interpretation_zh`/`claim_refs`/
   `canonical_source_url` contract `tools.drafting.validate_card` actually checks. Inspecting
   `tools/drafting.py:build_prompt` showed why: `DRAFT_RULES` describes behaviour but never names
   the required output fields, unlike the classifier's prompt, which embeds
   `classifier.RESPONSE_CONTRACT` verbatim (Decision 1, `docs/phase-5-review-decisions.md`). This is
   the same class of gap as the classifier's `evidence_refs` repair, just never hit before because
   drafting had never been run against a live model. **Repair applied** (`tools/drafting.py`,
   `build_prompt`): added an explicit `output_schema` object to the prompt payload naming all eight
   required fields and forbidding nested `en`/`zh` groups or renamed keys. Covered by
   `tests/test_drafting.py::DrafterTests::test_drafting_prompt_names_the_required_flat_output_fields`.
   The next call (prompt_version `p2-draft3`) returned `ready_for_analyst_review` with zero
   defects on the first attempt.
3. **Human review.** The user reviewed the full EN/ZH card content in chat (headline, summary,
   interpretation, source link, figure/party parity) and approved it. Recorded via
   `tools/approval_ledger.py:append_review` — `reviewer_id="bob"`, `status="approved"`, bound to
   the exact `(event_id="pe-e3737767c25b", revision=1, content_hash=9fbb0cc...d93c1e4)` triple. The
   ledger lives at `work/phase2/phase6-review/approval-ledger.csv` (git-ignored).
4. **Export — one more genuine gap found and repaired.** `tools/reviewed_export.py:write_reviewed_feed`
   wrote the approved card to `work/phase2/phase6-review/reviewed-feed/`. Packaging it for browser
   verification (a new, isolated export dir, distinct from `work/phase2/demo-feed/` and
   `work/demo-export/`, with the header/footer text changed so the two editions are never
   confused) reused `site/index.html` + `site/app.js` unmodified except for that labelling text.
   Serving it live crashed `site/app.js`'s `init()` (`TypeError: Cannot read properties of
   undefined (reading 'includes')`) because the reviewed feed's `index.json` never wrote a `dates`
   key — only `dates_with_cards` — while `app.js` reads both (`meta.dates` for the navigable range,
   `meta.dates_with_cards` to flag which have a card). This export path had never actually been
   served before, so the gap was latent. **Repair applied** (`tools/reviewed_export.py`,
   `write_reviewed_feed`): the index now also writes `"dates": sorted(by_date)` — the same list as
   `dates_with_cards`, since this feed only ever knows about dates that have an approved card.
   Covered by `tests/test_reviewed_export.py::WriteReviewedFeedTests::test_writes_one_file_per_date_and_an_index_with_only_approved_cards`.
5. **Browser verification.** Served on `127.0.0.1:8643` from
   `work/phase2/phase6-review/reviewed-demo-export/` (git-ignored). Confirmed: the approved card
   renders with correct headline/summary/interpretation, Level A pill, score 76, `otf` /
   `financing` tags, a working `https://www.blueowltechnologyfinance.com/...` source link, and
   `partition: reviewed · status: analyst_approved`; the EN/中文 toggle correctly swaps to the
   Chinese rendering (checked at the Unicode-codepoint level, not just visually, since some
   terminals mis-render CJK — the served bytes and DOM text are correct UTF-8). The disclosure
   banner states cards here are approved at an exact revision/hash. Confirmed no evaluator-only
   field (`tools.records.EVALUATOR_ONLY`) or the `DEEPSEEK_API_KEY` credential appears anywhere in
   the served directory's four files (`index.html`, `app.js`, `data/index.json`,
   `data/2026-09-04.json`).

## Updated dispositions

1. `phase2_deterministic_baseline` = **FAIL** (unchanged, historical).
2. `historical_model_comparison` = **not_run** (unchanged — still explicitly deferred to Phase 7;
   Phase 6 ran exactly one drafting call plus the smoke run's existing classification, not a
   comparison at scale).
3. `reviewed_demo_ready` = **passed, for exactly one card.** One event was classified (Phase 5),
   grounded in verbatim claims, drafted bilingually by a live model, approved by a named human
   reviewer at an exact content hash, exported only through the approval-gated path, and verified
   rendering correctly in a real browser. This is not a full edition and should not be read as one
   — it demonstrates the complete loop end-to-end for a single event, nothing about throughput,
   editorial consistency across many cards, or reviewer workload at scale.
4. `automated_selection_readiness` = **inconclusive_pending_fresh_temporal_validation** (unchanged
   — one human-approved card says nothing about automated selection quality; only a fresh,
   prospectively-frozen temporal holdout can move this, and that remains out of scope here).

## What is still Phase 7's job, unchanged

Per `docs/handover-phase-6.md`'s carry-forward section: the full 57-article calibration partition
and 21-article historical holdout, challenge diagnostics, and any prompt/schema repair discovered
during that larger run (its own independent one-repair budget, not an extension of either repair
used here or in Phase 5). The two repairs in this phase were narrowly scoped to what actually broke
the single-card loop (drafting's flat-schema gap, the reviewed-feed's missing `dates` key) and
should not be read as pre-clearing changes for the larger Phase 7 run — that run may surface
different gaps at a different scale and needs its own adjudication.

> **Scope correction (P7-1, 2026-09-13):** "57-article" and "21-article" above are publish-worthy
> event counts, not article counts. Phase 7's frozen scope is 188/56/30 = 274 article inputs; see
> `docs/phase-7-scope.md`.

## Verification

345 pre-existing tests plus 2 new ones (346 total) pass; `tools/validate_spec.py` reports zero
errors; `git diff --check` clean. Nothing sensitive was committed: `.env`, the approval ledger, the
raw model outputs, and every export directory created in this phase live under git-ignored `work/`.
