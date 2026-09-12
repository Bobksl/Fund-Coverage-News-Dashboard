# Phase 2 disposition — 2026-09-12

**Phase 2 is complete. The disposition is FAIL for the deterministic baseline, and the structured
LLM pipeline is untested.** A completed phase is not a passing one: this records a real measured
result against the agreed bars, and the result is a failure with a clear, actionable cause.

Artifacts: freeze in `work/phase2/freeze-001/`, predictions and evaluation in
`work/phase2/run-001/`, labels in `work/phase2/evaluator/label-review-003/`.

## What was actually run

| Item | Value |
|---|---|
| Labels | 274 rows, one reviewer (AN03), audited: 0 errors, 0 normalizations, no conflicting event groups |
| Gold events | 262 distinct; 95 publish, 42 reserve, 134 reject, 3 review |
| Evidence | 276 records, 275 with hashed excerpts |
| Freeze | Labels, evidence and split manifest hashed before any run; predictions hashed before the evaluator read a label |
| Engine | **Deterministic baseline only.** No model provider is configured. |

## Results against the agreed bars

| Cohort | Gold publish-worthy | Selected | Precision (bar 90%) | Recall (bar 85%) | Must-not-miss (bar 100%) |
|---|---|---|---|---|---|
| Natural feed — holdout | 21 | 4 | **75%** | **14.3%** | **1 of 2** |
| Natural feed — calibration | 57 | 12 | 83% | 17.5% | 6 of 6 |
| Challenge | 10 | 6 | 50% | 30% | 1 of 3 |

Clustering was clean: **zero false merges** across all three partitions, with 7 false splits in
calibration and 1 each in holdout and challenge. Review-required rate was 17.0% / 3.6% / 16.7%,
inside the proposed 20% ceiling.

**The natural-feed holdout is evaluable** — 21 publish-worthy events clears the 20 minimum — and it
fails precision, recall and must-not-miss. **The challenge cohort is inconclusive on sample size**:
10 publish-worthy events is half the minimum, so its numbers describe a probe set too small to
carry a robustness claim.

## Why recall collapsed, and what it means

Of the 78 publish-worthy events the baseline did not select, **45 scored no relevance at all** —
the engine found no qualifying connection to anything monitored. The reason codes are dominated by
`weak_transmission` (64), `ambiguous_identity` (52), `below_materiality` (47) and `no_relevance`
(45).

The cause is visible in the gold set's composition: of 95 publish-worthy articles, **51 come from
Alternative Credit Investor and 21 from Commercial Observer** — third-party reporting about private
credit and property lending, mostly naming managers that are *not* on the 13-entity watchlist. The
analyst published them on **sector relevance**. The baseline fires almost entirely on **watchlist
entity match**.

That is a specification-level gap, not a tuning gap. The deterministic floor was built to resolve
named entities; the editorial standard in use is broader. Two candidate fixes, and they are
genuinely different:

1. **Semantic relevance** — the structured classifier stage, which was built for exactly this and
   has never been run. This is the experiment's actual hypothesis.
2. **Broader deterministic sector rules** — make Level B sector matching sufficient without an
   entity, which would raise recall and probably cost precision.

Nothing here distinguishes between them, because only the floor was measured.

## What this disposition does and does not authorize

It **does** close Phase 2: the corpus, freeze, run and per-cohort evaluation exist, with counts,
denominators and unresolved cases recorded.

It **does not** satisfy the Phase 3 entry condition as written, which requires a disposition
supporting a small ingestion pilot. A 14% recall floor does not support a claim that public
sources feed a useful daily selection.

## Limits that travel with every number above

- **One reviewer, no adjudication.** No second labeller, so inter-analyst agreement is unmeasured
  and the 80% agreement trigger in the protocol was never tested.
- **Two publications supply most of the corpus.** 192 of 276 records come from ACI and Commercial
  Observer, so these figures largely describe those two sections, and the cohort leans toward
  commercial property lending rather than the corporate private credit the watchlist centres on.
- **Cohorts overlap.** 60 of 91 challenge probes are linked natural-feed records, so the two
  results are not independent.
- **Evidence is excerpts.** Up to 800 characters per article, not full text; 117 records are gated
  ledes. The classifier saw less than a human reader would.
- **The challenge cohort is undersized.** Half the required positive supply.
- **No LLM was run.** Every number above is the deterministic floor.
