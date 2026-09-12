# Phase 3 entry-gate check — 2026-09-11

Disposition: **blocked. Phase 3 ingestion-pilot implementation is not authorized.** The Phase 2
exit evidence required by [phase-2-experiment.md](phase-2-experiment.md) does not exist in this
checkout. No collector was written and no source endpoint was contacted.

This is an independent re-check of the handover's mandatory entry condition, not a restatement of
the prior disposition. It confirms the earlier finding in
[phase-2-batch-review.md](phase-2-batch-review.md) against the actual files.

## What was verified in the checkout

Branch `codex/phase-1-editorial-spec` at `cf9c8c3`, clean tree, ahead of origin by three commits.
Nothing was reset, overwritten or pushed.

- `python tools/validate_spec.py` → 7 JSON files, 30 entities, 23 sources, 8 sectors, 11 themes,
  15 event types, 18 hypothetical cases, zero errors (Python 3.13.14).
- `python -m unittest discover -s tests -v` → 7 tests, all pass.
- `git diff --check` → clean.
- These checks cover the specification validator, the article-only packet boundary and the
  evaluator label audit. None of them exercises retrieval, classification, grouping, scoring or
  ranking, because no such code exists.
- Repository code inventory: `tools/validate_spec.py`, `tools/review_packet.py`,
  `tools/audit_labels.py`. There is no evidence-record implementation, no decision validator, no
  classifier adapter, no event grouper, no scoring/ranking runner and no evaluator.
- Private evaluator state under `work/phase2/evaluator/label-review-002/audit.json`: 20 label
  rows, `structurally_valid: true`, zero errors, `freeze_ready: false`, scope recorded as
  "calibration only; not empirical performance". Decisions are 9 publish / 4 reserve / 7 reject
  across 20 event groups, all singletons; 5 must-not-miss rows; 0 unresolved review rows.
  No label content, rationale or group ID left the evaluator side.

## Unmet dependencies, against the agreed exit criteria

| Required exit artifact | Status |
|---|---|
| Frozen labels **and** evidence payload, frozen before inference | Absent. Submitted bytes are hashed and preserved, but `freeze_ready` is false and the linked article text was never captured as a frozen model input. A link-packet hash does not freeze source content. |
| Independent human labeling | Partial. One reviewer labeled 20 articles and corrected three items. No second reviewer, no shuffled relabel, no adjudication record. |
| Natural-feed holdout with positive-event denominator | Absent. No predeclared source roster, date window or completeness log exists, so the handpicked intake cannot estimate natural prevalence. |
| Challenge holdout with positive-event denominator | Absent. Protocol minimum is ≥20 distinct publish-worthy events per evaluable cohort; the entire starter batch yields 9 publish-labeled articles. |
| Temporal split manifest, lineage isolation, disclosed exceptions | Absent. No split was constructed. |
| Precision / recall / must-not-miss / identity-role results | Absent. No inference of any kind has run; there is no prediction file to evaluate. |
| Clustering (false merge/split) results | Untestable on current data. All 20 gold groups are singletons, so duplicate consolidation cannot be measured. |
| Bilingual 20-card grounding and parity QA | Absent. |
| Analyst usefulness and review-time evidence | Absent. |
| Explicit unresolved failures and a disposition supporting the pilot | Absent. Two calibration taxonomy/rubric disagreements remain open and undocumented as resolved; no pass/fail/inconclusive disposition has been issued. |

Passing structural checks, completed human labels and a full source review are not substitutes
for pipeline evaluation. None of the above is waived by the prepared Phase 3 handover prompt.

## What may proceed now, as Phase 2 work

Ticket 2–4 engineering in [phase-2-experiment.md](phase-2-experiment.md) can be implemented
against synthetic fixtures without waiting for the holdout: the decision-record data contract from
[decision-record.md](decision-record.md), a decision validator, deterministic baseline matching,
predicted event grouping, scoring/ranking and a saved-output replay path. That work is assigned and
reported as Phase 2, never as a satisfied Phase 3 prerequisite. Benchmark inference still requires
the joint evidence/label/split freeze.

Corpus expansion, second-reviewer labeling and evidence capture are the blocking external inputs
and are not engineering tasks.

## Not done, deliberately

No collector, no HTTP retrieval, no endpoint reconnaissance, no source manifest and no schema that
would compete with the Phase 2 decision record. Existing interfaces were read only to confirm which
implementation dependencies are missing.
