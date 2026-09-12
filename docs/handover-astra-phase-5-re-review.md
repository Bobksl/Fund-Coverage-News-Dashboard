# Phase 5 re-review — handover for GPT-6 Astra

Written 2026-09-12 against commit `bac846d` on `main` (pushed; `git status` clean). This is the
direct response to your pre-run review recorded in `docs/phase-5-review-decisions.md` — read that
file first, it documents what was accepted and exactly what changed for each of your three
decisions. This handover asks you to verify the fixes actually close what you found, not to
re-derive the findings from scratch.

## What changed since your review

All three of your findings were verified against the actual code/config before anything was
touched — Ticket A's exploit was confirmed real (`guggenheim_securities` and a genuinely tracked
platform share the identical `parent_relationship: "business_platform_of"` in
`config/entities.json`), and all four manifest category errors you listed were confirmed on
inspection.

**Ticket A/B/C/D (classifier semantics) — implemented in `tools/classifier.py`:**
- `entity_matches: [{entity_id, role, evidence_refs}]`, `role` ∈ `{subject, adviser, counterparty,
  sponsor, portfolio_company, other}`. Level A now requires an entry with `role=subject` for an
  entity in `direct_entity_ids`/`propagated_entity_ids` — named-only-as-adviser fails regardless of
  entity.
- `propagation_basis` (≥20 chars) required when the Level A subject is reached only via
  propagation, not direct match.
- `sector_readthrough` object required for Level B: `sector_id`, `observed_change`, `basis` ∈
  `{comparable_exposure, sector_aggregate, market_terms}`, `affected_population`,
  `comparability_explanation`, `evidence_refs`. `sector_id` must be one of the declared
  `sector_ids`; `comparability_explanation` has a minimum length.
- Level C keyword denylist/allowlist removed entirely. Replaced with required
  `transmission.consequence_category` (enum) and `transmission.affected_exposure` (≥10 chars,
  specific). `trigger`/`mechanism`/`outcome` remain a non-empty structural requirement only.
- `classifier.RESPONSE_CONTRACT` embedded verbatim in the prompt (`build_prompt`) naming every
  field above, its type/enum, and when it is required.
- `evidence_refs` validity extended to `entity_matches` and `sector_readthrough`, not just scoring
  components.

**Manifest fidelity — `tools/select_calibration_smoke.py`, `work/phase2/calibration-smoke/`:**
- Fixed the self-raise vs. lend-out distinction for `manager_level_financing` (Blue Owl leading
  financing *for* IREN no longer qualifies; Blue Owl Technology Finance Corp.'s own senior-notes
  placement does).
- Excluded "joint venture" from `tracked_manager_wrong_strategy` matching (was matching on the bare
  word "venture"). No replacement candidate exists in the natural-feed corpus under metadata-only
  criteria — recorded as an explicit gap, not forced.
- Added a disambiguating-suffix exclusion around short-alias matches, so an explicit "KKR & Co.
  Inc. — 8-K" filing no longer reads as a namesake collision; the genuine PAG/Cordina case (no such
  disambiguation present) is retained.
- Removed "appoints"/"joins as"/"names " from marketing-term matching (real mandate/leadership
  news, not marketing); added a named-conference-event pattern that correctly picks up "Apollo to
  Present at the Barclays 24th Annual Global Financial Services Conference" instead.
- `manifest-v1.json` preserved unmodified; `manifest.json` (v2, `supersedes: "v1"`) is the current
  frozen manifest — **9 articles, 10 of 12 categories**. `tracked_manager_wrong_strategy` and
  `high_materiality_outside_scope_negative` remain gaps (down from your single flagged gap of 1;
  the wrong-strategy category lost its only match once the false positive was excluded, and no
  honest replacement exists in this corpus).

**Decision 3 — your one-repair policy adopted verbatim** in `docs/phase-5-review-decisions.md`,
governing the still-unrun live calibration stage.

**Tests:** 14 new regression tests reproduce your exact must-pass/must-fail cases —
`tests/test_classifier.py::RelevanceSemanticsTests` (Guggenheim-Securities-as-adviser must fail;
a Pretium/Deephaven-Mortgage-style propagated subject with a stated basis must pass; a padded
generic Level-C statement containing a listed category word must still fail; a correct causal
chain using none of the old keyword-list words must pass) and
`tests/test_select_calibration_smoke.py::ManifestFidelityRegressionTests` (all four manifest
false-positive/negative cases from your table, plus the two new-heuristic false positives that
had to be avoided while fixing them). 321 tests total (up from 307), `validate_spec` clean,
`git diff --check` clean.

## What did not change

**Still genuinely blocked on a credential.** No live model call has been made; `ANTHROPIC_API_KEY`
is not set. The four dispositions are unchanged:
1. `phase2_deterministic_baseline`: FAIL.
2. `historical_model_comparison`: not run.
3. `reviewed_demo_ready`: not passed.
4. `automated_selection_readiness`: inconclusive, pending a fresh temporal validation.

## Your task now

Re-review against the same three decisions, now that the fixes exist:

1. **A/B/C invariants.** Read the updated `_validate_relevance_semantics` and
   `_validate_entity_matches` in `tools/classifier.py` plus the new tests. Confirm the specific
   gap you found (role-blind entity resolution) is actually closed, and that the replacement
   (`entity_matches` + `propagation_basis` + `sector_readthrough` + `consequence_category`/
   `affected_exposure`) doesn't introduce a new one — in particular, whether the fixed vocabulary
   of `entity_matches.role` is complete enough for the rulebook's actual range of relationships, or
   whether the residual judgment call (a model can still lie about `role=subject`) needs an
   additional structural check you can specify precisely.
2. **Manifest sufficiency.** 9 articles, 10 of 12 categories, two gaps now instead of one (the
   wrong-strategy category lost its only — false-positive — match and has no honest replacement in
   this corpus). Decide: proceed with 10 categories as a documented limitation, or require one more
   bounded metadata-only search for `tracked_manager_wrong_strategy` specifically (state the exact
   search criteria if so — title/publisher/access-status only, never labels).
3. **One-repair policy.** Confirm your rule as adopted verbatim in
   `docs/phase-5-review-decisions.md` is complete and needs no amendment before it governs the
   actual live run.

Same ground rules as before: do not write or edit code (describe any remaining defect precisely
enough to become a scoped ticket); do not pick the provider/model or authorize spend; there are
still no classifier outputs to review (that is the next Astra task, after a live or replay run
actually produces predictions). If you accept everything as fixed, say so explicitly.
