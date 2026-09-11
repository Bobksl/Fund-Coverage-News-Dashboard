# Phase 2 starter-batch disposition — 2026-09-11

**Batch review complete; Phase 2 empirical evaluation incomplete.** This distinction is essential: auditing human labels against public sources is not running the filtering prototype against hidden ground truth.

## What was completed

The analyst's three corrections were verified in the submitted file. The revised sheet passes required-field, enum, coverage, duplicate-ID and event-group consistency checks after formatting-only normalization. Original and revised submissions remain preserved separately; article IDs anchor revision comparisons because the analyst renumbered some event groups.

All 20 original article URLs were opened and relevant event/role passages checked. Additional primary evidence was located for final bond terms, borrower financing details, manager credit AUM and hybrid-strategy classification. Detailed per-article findings and evidence links remain privately in `work/phase2/evaluator/label-review-002/source-review.json` and `review.md`. The normalized copy and `audit.json` are in that directory. These are evaluator artifacts, never pipeline inputs.

No publication decision was silently changed. A relevance-level taxonomy disagreement and a reserve/materiality rubric disagreement are recorded for calibration; do not manufacture agreement by changing the labels to match the numerical score. Historical review-001 findings are superseded where explicitly corrected.

## Readiness assessment

| Requirement | Current finding |
|---|---|
| Submitted-label structure | Pass for all 20 records after logged formatting normalization. |
| Original evidence and label preservation | Submitted bytes copied and hashed; prior versions preserved. This is not an evidence/model-input freeze. |
| Core source review | Completed for all 20; supplemental primary references recorded. Capture the exact permitted evidence and reconfirm label scope before freeze. |
| Independent human labels | One reviewer supplied labels; no second-review or repeat-review record is present. |
| Natural-feed holdout | Not constructed. Handpicked calibration records cannot estimate natural-feed prevalence. |
| Challenge holdout | Not constructed; positive supply is below the protocol minimum. |
| Temporal isolation | No frozen split; related earnings milestones need lineage isolation even after event IDs are separated. |
| Deduplication coverage | All current event groups are singletons; same-event duplicate consolidation cannot be assessed. |
| Actual model/pipeline evaluation | Not run. No precision, recall, stability, ranking-ablation, cost or latency result exists. |
| Bilingual QA and analyst usefulness | Not run. |
| Phase 3 entry | Not established under the agreed protocol. |

## Exact next work

1. Implement the already specified local baseline/classifier adapter, decision validator, grouping/scoring/ranking and evaluator with synthetic tests. This engineering work need not wait for a full holdout; benchmark inference still requires label/evidence freeze.
2. Expand the corpus under separate natural-feed and challenge policies, with sufficient publish-worthy events and duplicate/manager-independent/critical-risk coverage. Reuse the approved article-only labeling process. Do not tune sampling to observed model performance.
3. Reconcile remaining calibration taxonomy interpretations; archive the source evidence, define availability cutoffs and freeze labels/evidence/config/prompt/model/splits. Keep gold groups and analyst reasons hidden from fresh model contexts.
4. Run the specified comparisons and bilingual/analyst QA. Report each cohort separately and issue a pass, fail or inconclusive disposition based on actual results.

The [Claude Phase 3 handover](handover-claude-phase-3.md) has been updated to this state. It remains ready to use after the Phase 2 exit evidence exists; it does not authorize calling this review an empirical pass or adding infrastructure early.
