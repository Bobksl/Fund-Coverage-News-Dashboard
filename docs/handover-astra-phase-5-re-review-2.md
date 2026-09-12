# Phase 5 re-review round 2 — handover for GPT-6 Astra

Written 2026-09-12 against commit `af7afab` on `main` (pushed). This is the direct response to
your second review. Read `docs/phase-5-review-decisions.md`'s "Round 2" section first — it records
what changed for each of your six findings (Ticket A ×3, B, C, D, plus the manifest bounded search
and the wording correction). This handover is a compact summary asking you to confirm closure, not
a re-derivation.

## What changed

**Ticket A (role/involvement split) — implemented.** `entity_matches.role` replaced with
`economic_role` (ED02's actual vocabulary: `borrower, lender, sponsor, manager, fund, insurer,
adviser_arranger, other`) and `involvement` (`direct_involvement, incidental_mention,
unresolved`). Level A gates on `involvement=direct_involvement` only; `economic_role` never grants
or vetoes by itself — a lender with genuine direct involvement now passes
(`test_level_a_a_lender_can_be_directly_involved`).

**Ticket A (propagation path) — implemented.** `direct_entity_ids` now holds the evidenced
business; `propagated_entity_ids` must be a real config `parent` of a `direct_entity_ids` member
(`_validate_propagation_edges`, checked against `config/entities.json`, not asserted in prose). The
Pretium/Deephaven Mortgage fixture is corrected to the actual ED02 shape (direct: Deephaven
Mortgage; propagated: Pretium — the reverse of what round 1 shipped). An invented/sibling parent
with convincing prose now fails on the edge check, not the length check
(`test_level_a_propagated_parent_with_no_real_ontology_edge_fails`, using your exact reproduction
sentence). `direct_involvement` now also requires non-empty `evidence_refs`
(`test_level_a_direct_involvement_without_evidence_refs_fails`).

**Ticket B — implemented.** Fixed the live bug you found: `comparability_explanation=123` no
longer bypasses validation (`_text()` was silently coercing non-strings to `""`, which skipped
rather than failed the length check — confirmed and reproduced in
`test_level_b_non_string_comparability_explanation_fails`). Level B now also requires the
`transmission` object (`test_level_b_missing_transmission_fails`), not `sector_readthrough` alone.

**Ticket C — accepted with the residual limitation named, not hidden.** Your reproduction
(`consequence_category="risk"`, `affected_exposure="all investment markets"`) is preserved as a
passing test
(`test_level_c_structurally_complete_but_semantically_generic_is_a_known_residual_limit`), with a
docstring stating explicitly that no further keyword/length heuristic was added per your guidance,
and that this is closed by post-run human review, not schema validation. `PROMPT_RULES` gained the
explicit trigger→mechanism→consequence chain instruction you asked to restore.

**Ticket D — implemented.** `RESPONSE_CONTRACT` now defines `event_identity`'s and `components`'
nested fields and states the direct-vs-propagated semantics explicitly.

**Decision 2 (manifest) — implemented via your exact bounded search.** PAG/Cordina reassigned
`ambiguous_or_namesake_identity` → `tracked_manager_wrong_strategy` (found via the search you
specified: tracked manager, explicit equity-ownership transaction, unrelated operating industry,
no credit/debt language). `manager_level_financing` now requires the matched entity be
manager-typed in config (`entity_type: "manager"`), which correctly disqualifies OTF (a vehicle
whose name contains its manager's shorter alias as a substring). Net result — and this is smaller
than what you asked to preserve as an "explicit exception," so flagging it precisely:
`manager_level_financing` and `ambiguous_or_namesake_identity` are now both gaps (no credible
candidate under the corrected criteria), alongside the pre-existing `high_materiality` gap — **9 of
12 categories filled**, not 10. Each category is now tagged `established` / `candidate_shape_only`
/ `gap` in the manifest (`category_confidence` field) rather than presented as uniform verified
coverage. `manifest-v1.json` and `manifest-v2.json` both preserved; `manifest.json` is v3.

**Decision 3 — accepted, one wording correction made.** No policy change. The prior "gate blocked
only by a credential" line is corrected to note that statement is provisional on the review found
so far, not a standing guarantee.

**Tests:** 8 new/replaced regression tests reproduce your exact reproductions and acceptance
criteria (the invented-parent case, the non-string `comparability_explanation`, the missing-B-
transmission case, the vehicle-vs-manager shadowing case, the PAG/Cordina reassignment, the named
residual C limitation). 329 tests total (up from 321), `validate_spec` clean, `git diff --check`
clean.

## What did not change

Still blocked on a credential; no live call made. Four dispositions unchanged (baseline FAIL,
comparison not run, reviewed-demo not passed, automated-readiness inconclusive).

## Your task now

1. **Confirm Tickets A/B/D are closed** against the updated code/tests, or specify precisely what
   remains.
2. **Confirm the C residual-limitation framing is acceptable** as a permanent, disclosed
   limitation (sampled by post-run review) rather than something that still needs a mechanical fix
   — or state what specific structural check (not a keyword/length heuristic) would close it.
3. **Decide on the manifest's 9-of-12 outcome**: accept as the honest result of the corrected
   criteria (two additional categories, `manager_level_financing` and
   `ambiguous_or_namesake_identity`, becoming gaps rather than false positives), or specify a
   further bounded, metadata-only search for one or both.
4. If everything above is accepted, say so explicitly — the pre-inference gate should then be
   assessed purely on whether a provider credential exists, not on any remaining code concern.

Same ground rules: no code edits, no provider/model/spend decisions, no classifier-output review
yet (there are no outputs).
