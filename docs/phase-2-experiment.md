# Phase 2 — a fixed real-article editorial experiment

Status: Phase 2 authorized on 2026-09-11; protocol amended before implementation. No empirical result yet. Phase 1's hypothetical cases are specification examples only.

Scope: monitoring-only for every entity in Phase 2. The user confirmed US Bayview at bayview.com and the specialty-finance BasePoint at basepointgroup.com. No holdings inventory is needed. Confirmed-held overrides are disabled in this experiment; critical monitored events still require urgent review.

## Exact first experiment

Start with approximately **120 real public article records** across a recent 30-calendar-day period, with an approximately **80/40 calibration/holdout** split. These are planning counts, not quotas or permission to dilute the test. Keep two independently reported cohorts:

- **Natural feed:** all records discovered under a predeclared source roster, query/filter policy and consecutive date windows, before any editorial eligibility decision. Preserve irrelevant items, duplicates and access failures. Record source outages and pagination limits. This estimates performance on that specific discovery feed, not the entire public web.
- **Challenge set:** deliberately selected hard negatives, namesakes, near-duplicates, critical risk cases and other coverage probes. Preserve selection rationale in evaluator-only metadata. Older examples may be used with their actual dates. This estimates robustness on a constructed set, not natural prevalence.

Never label targeted search results or handpicked relevant articles as a natural feed. Never pool the cohorts into a headline precision, recall or pass decision. Report cohort and split separately. An article discovered naturally stays natural; a matching challenge record is linked rather than counted twice. Shared event lineages across cohorts require evaluator-side deduplication or separate disclosure, not double-counted evidence.

Build each evaluable holdout cohort around **at least 20 distinct analyst-publish-worthy events**, not merely A/B/C-eligible events and not the system's selected count. Eligible-but-reserve/reject cases remain negatives for publication precision/recall. Retain a meaningful negative sample (target at least 15 distinct non-publish-worthy events in the challenge holdout). Natural-feed negatives must retain their discovered prevalence; do not rebalance them. The independent label custodian verifies these counts before freezing. If natural-feed publish-worthy supply is insufficient, extend its consecutive window under a recorded rule before inference; do not top it up with challenge positives. If a cohort is still too small, report insufficient sample, not pass. The final total may exceed 120 for this reason.

**Temporal holdout where feasible:** freeze a publication-date cutoff, place earlier evidence in calibration and later evidence in holdout. Start by reserving the latest five completed news days; use earlier days in the 30-day frame for calibration. Extend the later natural window prospectively if the analyst-positive count is inadequate. Date-only or unknown-date cases get explicit precision/exception records. The label custodian prevents duplicates/updates of the same event from crossing partitions. A lineage spanning the cutoff is quarantined from the headline holdout evaluation (or reserved wholly for holdout with the earlier calibration articles removed); never move a later article into calibration and claim strict temporal separation. For sparse/older challenge cases where chronological separation is infeasible, use an event-disjoint challenge split and disclose that it is non-temporal. Do not claim it measures forward generalization.

Freeze a split manifest and its exceptions before holdout inference. Neither model outcomes nor system-selected counts may drive holdout composition. Do not fabricate articles, dates, labels or balanced availability.

Challenge coverage requirements overlap rather than sum to 120. These must not become natural-feed inclusion filters:

- All 13 watchlist entries represented where public evidence exists; document missing public coverage explicitly.
- All eight sectors, with strong emphasis on private credit/software/CLO/mortgage and at least some PE/VC/real-estate transmission.
- Seek US and European publish-worthy examples plus at least five APAC/Global/Other challenge events. Eligibility alone does not satisfy the holdout's analyst-positive minimum. Curated regional balance is for testing, not a measurement of news supply.
- At least 15 manager-independent B/C examples, including both justified and unjustified macro/AI stories.
- At least 25 hard negatives: routine mega-manager PE activity, awards, wrong entities, sponsor-vs-lender, generic macro, irrelevant banking and GP-led-secondary-vs-GP-stakes confusion.
- At least 10 multi-article event groups, two distinct deals with deceptively similar headlines, and at least five material updates/corrections.
- At least ten identity challenge records involving OTF/OTF II, NB, PAG, Bayview, BasePoint, Guggenheim and HSBC.
- At least eight critical-risk events or independently verified challenge cases, with allegation/proposal distinctions. All exposure status is monitored, never confirmed-held.
- Include inaccessible/snippet-only and contradictory-source cases in a separate operational challenge slice if they would crowd out the required scored holdout. Report them separately, never pretend they are complete evidence.

## Labels before model judgements

An alternatives analyst independently labels relevance, A/B/C, materiality tier, event identity, entity roles, publish/reserve/reject/review, must-not-miss status and a short rationale. **Human labels are frozen before model inference**, including calibration inference. The review packet exposes only article identifiers, original titles, publishers, source dates and links (or unmodified source evidence where permitted). It exposes no model scores, recommendations, A/B/C suggestions, entity-role predictions, challenge categories or proposed event groups. A second analyst reviews at least 30 cases covering all critical cases, borders and a random subset. If only one analyst is available, relabel a shuffled subset after a gap and disclose that weaker independence. Model output never becomes ground truth by default.

Preserve disagreements and adjudication. Resolve ontology interpretation on calibration records only. If analysts agree on fewer than 80% of initial publish/reject labels, clarify the rubric before treating model accuracy as meaningful. That 80% is a proposed process trigger, not measured performance.

### Hidden ground truth and clustering

Analyst event-group IDs, publish labels, reasons, must-not-miss flags, split-balancing decisions and challenge-selection rationale are **evaluator-only ground truth**. Keep them in a separate local labels file. The pipeline receives only article IDs and source evidence, with no analyst event IDs or preassembled gold event packets. It must propose its own event grouping from evidence. An input allowlist strips evaluator metadata from every baseline/model/drafting input. Plain article IDs must not encode labels, cohorts or event groups.

The independent custodian may use gold groups to construct leakage-safe splits; that does not authorize passing the groups to the classifier, clustering code or ranking. A runner manifest contains only article IDs and the requested partition membership. For holdout, ambiguous clusters remain pipeline outputs/abstentions until predictions are frozen. Analyst corrections are post-evaluation revisions, never retroactively credited as model clustering success. Calibration labels may inform explicit rule revisions after a calibration run, but never become per-article inference features.

Freeze evidence, separate analyst labels, split manifest, configs, prompt/model identifiers and evaluation criteria before holdout inference. Save predictions before the evaluator reads gold labels. The evaluator alone joins predicted clusters to gold groups and measures false splits, false merges and missed events. Treat known historical benchmark labels as potential model familiarity; the small holdout is directional evidence, not statistical proof of universal accuracy.

## Compare three approaches

1. **Deterministic baseline:** exact/contextual entity matching, event/risk phrases and transparent positive/negative rules. Preserve uncertain cases for review. This establishes how much semantic reasoning adds.
2. **Simple structured pipeline:** one classification call supplying evidence-linked eligibility, proposed event identity, transmission and score anchors; Python groups from predicted information and validates/sums/ranks. Ambiguous clusters remain review-required in frozen predictions; analyst corrections are measured separately.
3. **Ranking ablation:** same eligible set, rank using critical status then anchored materiality/transmission and direct fit, without the six-component total. This tests whether 100-point scoring earns its complexity.

Keep model and evidence identical when comparing ranking methods. On calibration only, rerun 20 difficult cases three times to measure inclusion/entity/score-band stability; route materially unstable cases to review. Do not introduce a multi-agent system as the benchmark's default comparator.

Draft English/Chinese cards for **20 eligible events** covering numerical BDC results, CLO terms, macro inference, adverse claims and direct vehicle news. Record all fact/translation corrections. One structured drafting call may generate both languages sequentially; split it only if quality improves on calibration evidence.

## Proposed acceptance criteria before automated ingestion

Apply separately to natural-feed holdout and challenge holdout, not calibration. Count analyst event groups for recall and predicted selected cards for precision, with one-to-one event matching so a duplicate card cannot create an extra correct selection. False merges cannot receive credit for every gold event they contain. Report counts, abstentions, false merges/splits and sample uncertainty alongside rates. No pooled readiness score.

| Criterion | Proposed bar |
|---|---|
| Selection precision | ≥90% of selected cards match distinct analyst-publish-worthy events; report selected-card denominator and uncertainty. Holdout construction uses gold publish-worthy counts, never model-selected counts. Zero selections gives undefined precision and cannot pass. |
| Important-event recall | ≥85% of analyst-publish-worthy distinct events selected; review abstentions count as unselected until disposition, so the system cannot pass by abstaining on everything. |
| Must-not-miss events | 100% surfaced to publication shortlist or urgent review; also report how many actually published and why any remain unresolved. Zero silently suppressed critical cases. |
| Identity/role | ≥95% correct scored entity-role assignments; zero OTF/OTF-II, namesake, sponsor/lender or wrong-manager errors in selected cards. |
| Event deduplication | Zero duplicate selected cards and zero distinct material events wrongly merged in the known duplicate/confusable groups. |
| Factual grounding | Zero unsupported material claims/numbers or misattributed losses/holdings in the 20-card bilingual sample. Every substantive claim traceable. |
| Chinese parity | Zero material entity, amount, currency, unit, attribution, negation or uncertainty changes across the sample; all identified material defects corrected before delivery. |
| Audit completeness | 100% of candidates have an outcome, reason, evidence availability and version metadata; rejected/review/failed/capacity decisions separately visible. |
| Operational reliability | Invalid or failed outputs are surfaced; zero silent drops. Proposed ≤20% review-required rate on evaluable holdout, reported alongside correctness. |
| Usefulness / efficiency | Analyst median usefulness ≥4/5 for selected cards. Proposed ≤20 minutes review per ten-card edition, with actual timing recorded. Record measured model tokens/cost/latency; no unverified price claim. |

High challenge-set precision does not imply natural-feed precision. For each cohort report its period, sources, sampling/temporal exceptions, article/event counts, analyst publish-worthy prevalence, all metrics and unresolved cases. Natural-feed reporting also includes candidate volume, accessible evidence share, analyst publish-worthy events and US/Europe supply without quotas. Challenge reporting includes failure categories and targeted coverage; it cannot repair a failed or undersized natural-feed result. Save a separate manually collected list of analyst-important events missed by discovery; filtering recall remains conditional on the collected universe.

## Disposition

Meet the natural-feed holdout bars on adequate analyst-positive supply, meet the challenge robustness bars without material critical/attribution defects, and demonstrate useful manual editions → consider a small ingestion pilot. An undersized cohort remains inconclusive. Failure → diagnose identity, evidence, relevance, ranking, dedupe or drafting; revise on calibration data and evaluate a fresh holdout. Do not repeatedly tune on the same holdout.

No requirement to deliver six stories every day or hit exactly 20% Europe. If public sources cannot support a useful feed, narrow the demo's claim and scope instead of adding weak stories or paid data against the brief. Analyst review remains in the MVP after passing; Phase 2 does not authorize unattended publication.

## Implementation tickets

1. Curate source manifest and labels privately under work/; verify evidence access, event groups and split. No collector yet.
2. Add a small Python runner and decision validator using decision-record.md. Verify parsing, zero silent drops and replays on saved outputs with focused unittest tests.
3. Add structured classifier adapter with one provider; validate bounded retry/failure handling and preserve raw outputs. Use no production database.
4. Implement event grouping, deterministic scoring/ranking and CSV review export; test wrong-entity, duplicate, threshold and geography cases.
5. Add a shortlist-only drafting call and evaluate the 20 bilingual cards. Run the frozen experiment and issue a disposition with counts and errors.

Each ticket must preserve the original labels and versions. Estimated cost/time is measured in this phase rather than promised from the previous conversation.

### Started on 2026-09-11

The first local article-only review packet contains 20 public-source links and blank human label fields. It is an exploratory calibration intake batch, not the 120-record experiment or an evaluable holdout. Its hand-selected sources cannot estimate natural-feed prevalence. No labels, event groups, predictions or empirical metrics were produced. See [Phase 2 status](phase-2-status.md) for the packet and remaining dependencies.
