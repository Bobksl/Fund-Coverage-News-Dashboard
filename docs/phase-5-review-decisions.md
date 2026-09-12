# Phase 5 external review decisions — 2026-09-12

Source: an external senior-reviewer pass (Astra role, per `docs/handover-phase-5.md`'s model
allocation) against `main` at `0be3e3b`, before any billed inference. This records what was
accepted, what changed, and the calibration one-repair policy adopted for the *live* run that has
not happened yet. Nothing here is itself the one allowed calibration-driven repair — these are
pre-inference corrections, explicitly carved out from that budget.

## Decision 1 — A/B/C semantic invariants (accepted, implemented)

The review found `tools/classifier.py`'s Level A/B/C checks confused structural completeness
(fields present, non-empty) with an actual evidenced connection. Verified concretely: a synthetic
response naming `guggenheim_securities` in `propagated_entity_ids` with an unrelated party and
action passed the prior Level A check, because `config/entities.json` gives
`guggenheim_securities` and `guggenheim_investments` the identical `parent_relationship:
"business_platform_of"` — the relationship type alone cannot carry the distinction between a
routine adviser and a monitored platform.

Implemented:
- **Entity role.** New `entity_matches` field: `{entity_id, role, evidence_refs}`, `role` one of
  `subject, adviser, counterparty, sponsor, portfolio_company, other`. Level A now requires an
  entry with `role=subject` for an entity in `direct_entity_ids`/`propagated_entity_ids` — a name
  appearing only as adviser/counterparty/sponsor is not Level A regardless of which entity it is.
- **Propagation basis.** When the subject entity is reached only via `propagated_entity_ids` (no
  direct match), a `propagation_basis` string (≥20 chars) is required, stating the evidenced
  business/vehicle involvement and its path to the tracked parent — never left to be inferred from
  `parent_relationship` alone.
- **Sector read-through.** Level B now requires a structured `sector_readthrough` object
  (`sector_id`, `observed_change`, `basis` ∈ `{comparable_exposure, sector_aggregate,
  market_terms}`, `affected_population`, `comparability_explanation`, `evidence_refs`) instead of
  presence-only trigger/mechanism prose. One comparable instrument/company is sufficient; multiple
  publishers or companies are not required.
- **Level C structure over keywords.** Removed the keyword denylist/allowlist entirely (it was
  simultaneously too strict — a correct explanation using none of the listed words failed — and
  too loose — a padded generic phrase containing "risk" passed). Replaced with required
  `transmission.consequence_category` (enum) and `transmission.affected_exposure` (a specific,
  non-generic string, ≥10 chars); trigger/mechanism/outcome remain a structural (non-empty)
  requirement only.
- **Response contract.** `classifier.RESPONSE_CONTRACT` is now embedded verbatim in the prompt
  (`build_prompt`), naming every field above, its type/enum and when it is required, so the model
  is never asked to infer the schema from prose.

What this cannot do: verify that an asserted `role=subject` or `propagation_basis` is *true* — a
model that dishonestly labels an adviser as the subject is not caught by structural validation.
That residual judgment is exactly what a post-run reviewer sample (Astra-level review of selected
cards, high-scoring rejections, and a random sample) is for; these checks gate what can be
gated mechanically.

Tests: `tests/test_classifier.py::RelevanceSemanticsTests` includes the review's exact
must-pass/must-fail acceptance cases (Guggenheim-Securities-as-adviser must fail; a Pretium/
Deephaven-Mortgage-style propagated subject with a stated basis must pass; a padded generic
Level-C statement containing a category word must still fail; a correct causal chain using none of
the old keyword-list words must pass).

## Decision 2 — Calibration-smoke manifest fidelity (accepted, manifest superseded)

The review inspected `work/phase2/calibration-smoke/manifest.json` (v1) against titles/publishers/
metadata only (no gold) and found several category assignments were structurally present but not
credible fits:

| v1 category → article | Problem | v2 fix |
|---|---|---|
| Wrong strategy → Enbridge/KKR joint venture | "Venture" matched "joint venture" wording, not an off-strategy activity | Removed bare "venture"; excluded "joint venture" explicitly. No replacement candidate exists in the corpus under tighter criteria — recorded as a gap, not forced. |
| Manager financing → Blue Owl leads financing *for* IREN | Blue Owl is the lender to a third party, not raising financing for itself | Added a self-raise vs. lend-out distinction (`SELF_RAISE_TERMS` vs `LENDER_OUT_MARKERS`); reassigned to Blue Owl Technology Finance Corp.'s own senior-notes placement |
| Ambiguous identity → KKR & Co. Inc. 8-K | An explicit, unambiguous filing by the named legal entity is not a namesake collision | Added disambiguating-suffix exclusion (`& Co`, `Inc`, `8-K`, etc.) around a short-alias match; kept the genuine PAG/Cordina case, which has no such disambiguation |
| Marketing → "Utmost appoints Aberdeen to manage RE debt" | A real investment mandate, not routine marketing | Removed "appoints"/"joins as"/"names " from marketing terms (they signal leadership/mandate news, not marketing) |

`work/phase2/calibration-smoke/manifest-v1.json` is preserved unmodified for audit.
`work/phase2/calibration-smoke/manifest.json` (v2, `supersedes: "v1"`) is the current, frozen
manifest: 9 articles, covering 10 of 12 required categories. `tracked_manager_wrong_strategy` and
`high_materiality_outside_scope_negative` have no credible candidate in the natural-feed corpus
under metadata-only criteria and are recorded as an explicit gap
(`missing_category_disposition` in the manifest), per the review's own closing instruction: *"If
no defensible candidate or replacement exists, record the gap and stop selection; do not inspect
gold or search indefinitely."*

Regression tests for every specific false-positive/false-negative above:
`tests/test_select_calibration_smoke.py::ManifestFidelityRegressionTests`.

## Decision 3 — One-repair policy (adopted verbatim, governs the future live run)

The following governs the *one* calibration-driven prompt/schema repair Phase 5 handover section 7
allows, once a provider credential exists and Stage 2 (calibration smoke) actually runs. It has not
been exercised — no live inference has occurred.

> **Trigger.** After preserving the complete initial smoke outputs, one repair may be used only
> when either:
> 1. At least two smoke articles concerning distinct source-described events exhibit the same
>    specification defect, with the omitted, contradictory or ambiguous instruction identified
>    against the public rulebook; or
> 2. One failure exposes a structural contract defect that makes valid rulebook classifications
>    unrepresentable or later predictions uninterpretable, demonstrated with an
>    article-independent synthetic counterexample.
>
> Duplicate reports of one event count once. Error count alone never qualifies.
>
> **Qualifying failures.** An omitted required editorial rule; contradictory or ambiguous prompt
> wording producing the repeated pattern above; or a schema field, enum or required structure
> incapable of representing a valid rulebook decision. The record must show the problem exists in
> the supplied specification, not merely in the model's answer. If that distinction cannot be
> established, the repair is not permitted.
>
> **Non-qualifying failures.** Individual wrong anchors, false positives, false negatives,
> borderline A/B/C disagreements, label disagreements, factual mistakes despite adequate context,
> stochastic variation, and failure to follow an already-clear instruction. Repetition does not
> convert clear-instruction noncompliance into a specification omission.
>
> **Scope.** One minimal, generic prompt/schema change addressing one documented defect and its
> necessary consistency changes. No article IDs, article-specific facts, gold event IDs, copied
> analyst rationales or case-specific exceptions may enter the repaired prompt/schema. Do not
> change labels, smoke membership, scoring thresholds, ontology scope, provider/model or sampling
> settings under this allowance. Fixes identified before inference (like Decisions 1–2 above)
> belong to the initial baseline, not this budget.
>
> **Execution and stopping.** Verify the change with synthetic positive/negative contract cases,
> then rerun the entire unchanged smoke set once under new immutable run IDs, preserving all
> original outputs. Use the repaired version regardless of whether headline smoke accuracy
> improves; do not choose versions by score. No second calibration-driven repair is allowed. If the
> contract remains structurally invalid, stop the comparison and record the blocker. Otherwise
> freeze the final prompt, schema, config, model and settings before full calibration and
> historical-holdout inference in fresh contexts.
>
> **Audit.** Record pre-repair prompt/schema versions and hashes; affected smoke article IDs;
> observed pattern; public rulebook authority; specification-versus-model diagnosis; exact generic
> change; post-repair versions and hashes; synthetic results; rerun IDs; and complete before/after
> smoke outputs. Confirm that no outputs from the planned historical-holdout model comparison were
> inspected before repair; separately disclose the holdout's already-known historical reuse. Save
> predictions before evaluator access.
>
> If unused, record explicitly: `calibration_prompt_repair = not_used`.

## Round 2 — external re-review, same date

The round-1 fixes above were re-reviewed and found improved but not yet closed. Verified
concretely: `guggenheim_securities`/`otf` and similar entity-graph claims were checked against
`config/entities.json` and ED02 (`docs/editorial-rulebook.md`) again; `comparability_explanation`
was confirmed to bypass validation when given a non-string value (`_text()` silently coerced it to
`""`, which then skipped, rather than failed, the length check).

**Ticket A — role/involvement conflation (accepted, implemented).** `entity_matches.role`
(`subject`/`adviser`/`counterparty`/`sponsor`) conflated two independent axes ED02 keeps separate:
what an entity economically IS in an event, and whether it was actually, evidentially involved. A
lender or sponsor can be directly involved; forcing it to relabel itself "subject" to pass the gate
was itself a defect. Replaced with two fields: `economic_role` (`borrower, lender, sponsor,
manager, fund, insurer, adviser_arranger, other` — ED02's actual vocabulary) and `involvement`
(`direct_involvement, incidental_mention, unresolved`). Level A now gates on `involvement=
direct_involvement` for an entity in `direct_entity_ids`; `economic_role` is descriptive only.

**Ticket A — propagation path validated against real ontology edges (accepted, implemented).**
The prior `propagation_basis` length check accepted "An unrelated company connects somehow to
this parent" — any sufficiently long sentence, regardless of whether the claimed parent
relationship exists in `config/entities.json`. `direct_entity_ids` now must name the actually
evidenced business (with a `direct_involvement` entity_matches entry and non-empty
`evidence_refs` — also newly required); `propagated_entity_ids` must be the real `parent` (per
config) of a `direct_entity_ids` member, checked structurally, not merely asserted in prose. The
test fixture was also corrected to match ED02's actual direct-vs-propagated shape: Deephaven
Mortgage (the evidenced platform) in `direct_entity_ids`, Pretium (its real config parent) in
`propagated_entity_ids` — the reverse of the round-1 fixture, which had this backwards.

**Ticket B — enforcement gaps (accepted, implemented).** `sector_readthrough`'s
`comparability_explanation` now has an explicit string-type check (the `_text()` coercion bug
above); all `SECTOR_READTHROUGH_TEXT_FIELDS` are type-checked. Level B now also requires the
`transmission` object (trigger/mechanism/outcome), previously enforced only for C, so a response
with `sector_readthrough` but no transmission no longer passes.

**Ticket C — accepted with a named, undissolved residual limit.** The review reproduced a
structurally-complete-but-semantically-generic C response (`consequence_category="risk"`,
`affected_exposure="all investment markets"`) passing validation, and explicitly declined to
recommend another keyword blacklist or length threshold to chase it (the same failure mode as the
phrase list removed in round 1: simultaneously too strict and too easy to game). The fix applied
is a strengthened, explicit prompt instruction (`PROMPT_RULES`) stating the required
trigger→mechanism→consequence chain and warning against generic `affected_exposure` phrasing —
not a new mechanical gate. This is recorded as a genuine, accepted residual limitation
(`tests/test_classifier.py::RelevanceSemanticsTests::
test_level_c_structurally_complete_but_semantically_generic_is_a_known_residual_limit`), closed by
post-run human/Astra-level review sampling, not by schema validation.

**Ticket D — response contract completeness (accepted, implemented).** `RESPONSE_CONTRACT` now
defines `event_identity`'s and `components`' nested fields, and states the direct-vs-propagated
semantics explicitly (direct = the evidenced business; propagated = a parent reached only via a
real config edge from it) rather than leaving those definitions to prose elsewhere in the prompt.

**Decision 2 — manifest, round 2 (accepted, implemented, one factual correction applied in round
3).** Ran the reviewer's exact bounded search (title/publisher/access-status only, natural
evidence-file order): a tracked manager explicitly transacting equity ownership of an operating
business, no debt/credit-sector language, no stated monitored-sector or manager-wide
capital/governance consequence. The rule change (adding `EQUITY_TRANSACTION_TERMS`, removing the
"pag" short-alias token from ambiguity matching) was correctly described here in an earlier draft
as reassigning "the PAG/Cordina article" -- **that was inaccurate**. `select()` keeps the first
matching record in evidence-file order, and the actual article the corrected rule selects for
`tracked_manager_wrong_strategy` is `bb270ed1-50ac-5052-842e-1c1f78716755` ("KKR to sell minority
stake in Nordic Bioscience to Founder Claus Christiansen"), which appears earlier in the file than
PAG/Cordina. Both are credible instances of the same equity-transaction shape; the manifest happens
to contain the KKR one. **"Established" in `category_confidence` means an established, credible
*selection shape* under the bounded search criteria -- not an established rejection or any other
classification verdict.** Whether this specific KKR/Nordic Bioscience article is actually A, B, C
or none is exactly what live inference (once authorized) determines; nothing here prejudges it.
Separately, the search also fixed `manager_level_financing` to require the matched entity actually
be manager-typed in
`config/entities.json` (`entity_type: "manager"`) rather than any alias substring match — which
correctly disqualified "Blue Owl Technology Finance Corp." (OTF, `entity_type: "vehicle"`, whose
name happens to contain its manager's shorter alias) as *manager*-level financing. Net effect:
`manager_level_financing` and `ambiguous_or_namesake_identity` are now honest gaps (no credible
candidate exists in this corpus under the corrected criteria), alongside the pre-existing
`high_materiality_outside_scope_negative` gap — 9 of 12 categories filled in `manifest.json` (v3,
`supersedes: "v2"`), with each category's `category_confidence` (`established` vs
`candidate_shape_only` vs `gap`) now recorded explicitly rather than implying uniform verified
coverage. `manifest-v1.json` and `manifest-v2.json` are both preserved unmodified.

**Decision 3 — no amendment; one wording correction accepted.** The one-repair policy required no
changes. The review correctly flagged that this document's prior closing line ("Pre-inference
gate: still blocked on a credential, not on any of the above") was itself imprecise: at the time it
was written, the gate was *also* blocked on the round-1 findings being open, not solely on the
credential. That line is corrected below.

Regression tests for every round-2 finding: `tests/test_classifier.py::RelevanceSemanticsTests`
(the corrected Deephaven Mortgage/Pretium fixture, a lender with genuine `direct_involvement`, an
invented/no-edge propagation path, missing `evidence_refs` on a `direct_involvement` claim, the
non-string `comparability_explanation`, missing B `transmission`) and
`tests/test_select_calibration_smoke.py::ManifestFidelityRegressionTests` (the vehicle-vs-manager
shadowing case, and PAG/Cordina correctly matching wrong_strategy rather than ambiguous identity
-- though it is not the article this manifest's `select()` actually picks; see the round-3
correction above).

## Round 3 — external re-review, same date

**Ticket A (propagation) — the round-2 fix was insufficient; now fixed.** The review reproduced
two remaining defects: (1) an immediate-parent-only check rejected a genuine multi-hop ancestry
(`otf -> blue_owl_credit -> blue_owl`, all real `parent` edges in `config/entities.json`); (2)
propagation could be rooted in an entity present in `direct_entity_ids` but with no
`direct_involvement` match of its own (e.g. `direct_entity_ids=[neuberger, deephaven_mortgage]`
with only `neuberger` evidenced, incorrectly allowing propagation to `pretium` via the unevidenced
`deephaven_mortgage`). `_validate_propagation_edges` now walks the full config parent chain
(cycle-guarded) from each entity that is itself evidenced (`involvement=direct_involvement`) and
requires every `propagated_entity_ids` entry to be within that ancestor set — not merely an
immediate parent, and not reachable through an unevidenced entity. Both reproductions are now the
regression tests (`test_level_a_accepts_a_genuine_multi_level_ancestry`,
`test_level_a_rejects_propagation_rooted_in_an_unevidenced_direct_entity`).

**Ticket D (object-shape enforcement) — confirmed and fixed.** `transmission="not an object"`
(a non-dict) previously raised `AttributeError` from `parsed.get("transmission").get(...)` inside
validation, uncaught by `run_attempts` (which only wraps the provider call and `json.loads`, not
the `validate()` call itself) — meaning a single malformed field would have crashed the whole
`propose()`/`draft()` call, not produced a `review_required` outcome for that attempt. Fixed with
`_transmission_object()` (type-checks before use, in both the B and C branches) plus a defensive
`try/except` around `validate()` in `run_attempts` itself, so an unanticipated validator crash
degrades to one `schema_invalid` attempt rather than aborting the batch — directly relevant now
that a live run with a real budget is imminent: one malformed response must never waste the tokens
already spent on every other candidate in the same batch. Tests:
`test_level_b_non_object_transmission_is_a_review_case_not_a_crash`,
`test_level_c_non_object_transmission_is_a_review_case_not_a_crash`.

**Manifest correction accepted.** An earlier round-2 description of this document incorrectly
stated the bounded search "reassigned the PAG/Cordina article" to `tracked_manager_wrong_strategy`.
`select()` picks the first matching record in evidence-file order, and the article the corrected
rule actually selects is `bb270ed1-50ac-5052-842e-1c1f78716755` ("KKR to sell minority stake in
Nordic Bioscience to Founder Claus Christiansen"), which appears earlier in the file than
PAG/Cordina — both are credible instances of the same equity-transaction shape, but only one is in
the frozen manifest. Corrected throughout this document, `tools/select_calibration_smoke.py`'s
embedded `selection_method` text (which is written into the frozen manifest itself), and the
"established" semantics: **established means an established, credible selection shape, never an
established classification verdict.** `manifest.json` v3's article set and hash are unchanged by
this correction — only the prose describing it was wrong, not the selection.

**Decision on 9-of-12 coverage: accepted, no further search.** The three gaps
(`manager_level_financing`, `ambiguous_or_namesake_identity`, `high_materiality_outside_scope_negative`)
stand as documented limitations of this bounded smoke test.

**Gate status: still blocked, independent of a credential.** The reviewer explicitly declined to
treat credential availability as sufficient — "Credential availability also does not itself
constitute provider/model or spending authorization" — and held the gate BLOCKED pending the two
fixes above. Both are now implemented and tested (333 tests total, up from 329; `validate_spec`
clean; `git diff --check` clean). A provider (DeepSeek `deepseek-v4.1-flash`) and a spending cap
(¥6.59 CNY) were separately supplied by the user in the same turn as this review — handled in
`docs/phase-5-live-run-log.md`, not in this document, since credential handling and code-review
adjudication are different concerns and must not be mixed in one audit trail.

## Status carried forward unchanged

`phase2_deterministic_baseline = FAIL`. `historical_model_comparison = not_run` (no provider
credential). `reviewed_demo_ready = not_passed`. `automated_selection_readiness =
inconclusive_pending_fresh_temporal_validation`. Provider/model choice and spending remain
unapproved. **Pre-inference gate: blocked on a credential.** Both rounds of pre-inference
correctness review (Decisions 1–2, this document) are now implemented and tested; a credential is
the only presently identified remaining blocker, but that statement is provisional on whichever
review is current at the time it is read, not a standing guarantee that no further review round
will find anything else before a billed call is authorized.
