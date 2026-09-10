# Phase 2 — a fixed real-article editorial experiment

Status: recommended next experiment; not executed. Phase 1's hypothetical cases are specification examples only.

## Exact first experiment

Curate **120 real public article records**, grouped into events, across a recent 30-calendar-day period. Select a period ending before the experiment freezes. Include a contiguous five-news-day slice to observe real supply, then add difficult public examples from the rest of the period. Record actual dates, URLs, evidence availability and sampling reason. If critical examples are absent, add separately reported older challenge cases; do not relabel them recent.

Use **80 records for calibration and 40 for a held-out test**, grouped by underlying event and story lineage so duplicates/updates never cross the split. Target at least 20 eligible distinct events and 15 ineligible distinct events in the holdout, leaving room for five duplicate articles. If the curated set cannot support those counts, enlarge it before freezing and report the actual split. Do not fabricate articles, dates, labels or balanced availability.

Coverage requirements overlap rather than sum to 120:

- All 13 watchlist entries represented where public evidence exists; document missing public coverage explicitly.
- All eight sectors, with strong emphasis on private credit/software/CLO/mortgage and at least some PE/VC/real-estate transmission.
- At least 20 eligible US events and 10 eligible European events across the complete sample, plus at least five APAC/Global/Other challenge events. Curated regional balance is for testing, not a measurement of news supply.
- At least 15 manager-independent B/C examples, including both justified and unjustified macro/AI stories.
- At least 25 hard negatives: routine mega-manager PE activity, awards, wrong entities, sponsor-vs-lender, generic macro, irrelevant banking and GP-led-secondary-vs-GP-stakes confusion.
- At least 10 multi-article event groups, two distinct deals with deceptively similar headlines, and at least five material updates/corrections.
- At least ten identity challenge records involving OTF/OTF II, NB, PAG, Bayview, BasePoint, Guggenheim and HSBC.
- At least eight critical-risk events or independently verified challenge cases, with allegation/proposal distinctions. Unknown holdings stay unknown.
- Include inaccessible/snippet-only and contradictory-source cases in a separate operational challenge slice if they would crowd out the required scored holdout. Report them separately, never pretend they are complete evidence.

## Labels before model judgements

An alternatives analyst independently labels relevance, A/B/C, materiality tier, event identity, entity roles, publish/reserve/reject/review, must-not-miss status and a short rationale **before seeing model scores**. A second analyst reviews at least 30 cases covering all critical cases, borders and a random subset. If only one analyst is available, relabel a shuffled subset after a gap and disclose that weaker independence. Model output never becomes ground truth by default.

Preserve disagreements and adjudication. Resolve ontology interpretation on calibration records only. If analysts agree on fewer than 80% of initial publish/reject labels, clarify the rubric before treating model accuracy as meaningful. That 80% is a proposed process trigger, not measured performance.

Freeze evidence, labels, event-group split, configs, prompt/model identifiers and evaluation criteria before holdout inference. Treat known historical benchmark labels as potential model familiarity; the small holdout is directional evidence, not statistical proof of universal accuracy.

## Compare three approaches

1. **Deterministic baseline:** exact/contextual entity matching, event/risk phrases and transparent positive/negative rules. Preserve uncertain cases for review. This establishes how much semantic reasoning adds.
2. **Simple structured pipeline:** one classification call supplying evidence-linked eligibility, event identity, transmission and score anchors; Python validates/sums/ranks; analyst resolves ambiguous clusters.
3. **Ranking ablation:** same eligible set, rank using critical status then anchored materiality/transmission and direct fit, without the six-component total. This tests whether 100-point scoring earns its complexity.

Keep model and evidence identical when comparing ranking methods. On calibration only, rerun 20 difficult cases three times to measure inclusion/entity/score-band stability; route materially unstable cases to review. Do not introduce a multi-agent system as the benchmark's default comparator.

Draft English/Chinese cards for **20 eligible events** covering numerical BDC results, CLO terms, macro inference, adverse claims and direct vehicle news. Record all fact/translation corrections. One structured drafting call may generate both languages sequentially; split it only if quality improves on calibration evidence.

## Proposed acceptance criteria before automated ingestion

Apply to the untouched holdout, not the calibration sample. Count unique events for editorial metrics; count article records for extraction/resolution diagnostics. Report numerator/denominator and unresolved cases alongside every rate.

| Criterion | Proposed bar |
|---|---|
| Selection precision | ≥90% of system-selected distinct events independently labelled publish-worthy; at least 20 selected events are required for this estimate, otherwise extend the frozen test with a new prespecified sample. |
| Important-event recall | ≥85% of analyst-publish-worthy distinct events selected; review abstentions count as unselected until disposition, so the system cannot pass by abstaining on everything. |
| Must-not-miss events | 100% surfaced to publication shortlist or urgent review; also report how many actually published and why any remain unresolved. Zero silently suppressed critical cases. |
| Identity/role | ≥95% correct scored entity-role assignments; zero OTF/OTF-II, namesake, sponsor/lender or wrong-manager errors in selected cards. |
| Event deduplication | Zero duplicate selected cards and zero distinct material events wrongly merged in the known duplicate/confusable groups. |
| Factual grounding | Zero unsupported material claims/numbers or misattributed losses/holdings in the 20-card bilingual sample. Every substantive claim traceable. |
| Chinese parity | Zero material entity, amount, currency, unit, attribution, negation or uncertainty changes across the sample; all identified material defects corrected before delivery. |
| Audit completeness | 100% of candidates have an outcome, reason, evidence availability and version metadata; rejected/review/failed/capacity decisions separately visible. |
| Operational reliability | Invalid or failed outputs are surfaced; zero silent drops. Proposed ≤20% review-required rate on evaluable holdout, reported alongside correctness. |
| Usefulness / efficiency | Analyst median usefulness ≥4/5 for selected cards. Proposed ≤20 minutes review per ten-card edition, with actual timing recorded. Record measured model tokens/cost/latency; no unverified price claim. |

High precision on a deliberately enriched test set does not imply live-stream precision. Use the contiguous five-day slice to report candidate volume, accessible evidence share, eligible events and US/Europe supply **without quotas**. Save a separate manually collected list of analyst-important events missed by candidate discovery; filtering recall is conditional on the collected universe, not all private-market news.

## Disposition

Pass the offline criteria and demonstrate a useful five-day manual edition → authorize consideration of a small ingestion pilot. Failure → diagnose whether identity, evidence, relevance, ranking, dedupe or drafting caused it; revise only on calibration data, version the change, and evaluate on a fresh holdout. Do not repeatedly tune on the same holdout.

No requirement to deliver six stories every day or hit exactly 20% Europe. If public sources cannot support a useful feed, narrow the demo's claim and scope instead of adding weak stories or paid data against the brief. Analyst review remains in the MVP after passing; Phase 2 does not authorize unattended publication.

## Implementation tickets for the next developer

1. Curate source manifest and labels privately under work/; verify evidence access, event groups and split. No collector yet.
2. Add a small Python runner and decision validator using decision-record.md. Verify parsing, zero silent drops and replays on saved outputs with focused unittest tests.
3. Add structured classifier adapter with one provider; validate bounded retry/failure handling and preserve raw outputs. Use no production database.
4. Implement event grouping, deterministic scoring/ranking and CSV review export; test wrong-entity, duplicate, threshold and geography cases.
5. Add a shortlist-only drafting call and evaluate the 20 bilingual cards. Run the frozen experiment and issue a disposition with counts and errors.

Each ticket must preserve the original labels and versions. Estimated cost/time is measured in this phase rather than promised from the previous conversation.
