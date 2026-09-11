# Phase 2 status — 2026-09-11

Started: protocol amendments, confirmed manager scope, and an initial analyst review packet. No model inference or performance evaluation has run.

Latest update: the analyst corrected all three initial consistency items. The revised 20-row sheet passes structural checks; all 20 article sources were reviewed and supplemental primary references recorded. The latest private snapshot/review is `work/phase2/evaluator/label-review-002/`; review-001 is historical. See [batch disposition](phase-2-batch-review.md) for remaining calibration disagreements and empirical prerequisites. Labels/source payloads are not jointly frozen and no inference has run. The [Claude Phase 3 handover](handover-claude-phase-3.md) is updated but conditional on actual evaluation evidence. Phase 2 is not marked complete.

## Completed

- Natural-feed and challenge-set reports and dispositions are separate.
- Temporal holdout is preferred; lineage overlap and non-temporal exceptions are explicit.
- Holdout sufficiency counts distinct analyst-publish-worthy events, not A/B/C eligibility. Proposed minimum: 20 per reported cohort; insufficient supply is inconclusive.
- Human labels freeze before inference. Analyst groups are evaluator-only. The pipeline must infer its own groups.
- US Bayview and specialty-finance BasePoint confirmed. All Phase 2 exposure is monitoring-only.
- Offline standard-library packet builder and focused leakage/overwrite/input tests added.
- Initial 20-link packet assembled from public Apollo, Blue Owl, Bain Capital and BasePoint pages opened on 2026-09-11. Source titles, dates and links only; a long title is visibly abbreviated. No assistant-written investment summaries or labels.

## Local analyst handoff

Open `work/phase2/analyst-review-002/articles.md`; enter human decisions in the adjacent `analyst-labels.csv`. See [label instructions](analyst-labeling.md). These local artifacts are intentionally ignored by Git. Keep completed labels on the evaluator side; future inference receives only explicitly allowlisted evidence fields. Packet 001 is superseded because Windows newline conversion invalidated its input checksum; packet 002 preserves the same article IDs and fixes serialization before any analyst labels or inference.

This is exploratory calibration intake, not the complete benchmark. It contains 20 articles, not 20 established publish-worthy events. No natural/challenge cohort or holdout assignment is implied by packet ordering. IDs are random UUIDs. Broader manager, sector, regulator, negative, duplicate and critical-event coverage remains to be curated without exposing selection rationale to the analyst.

The packet contains links, not frozen full text. Before benchmark freeze, record the exact source evidence viewed by the analyst, its retrieval time, access limitations and hash where storage is permitted. Reconfirm labels against that evidence if it changes; do not silently substitute newer text. The packet hash only identifies the title/link input bytes and cannot prove article-content immutability.

## Collection limitations and next work

Initial discovery was exploratory and cannot retroactively become a natural-feed census. A separate source roster, date window and completeness log must precede the natural-feed collection. Capture all records under that policy, including routine announcements, duplicates and access failures. Challenge selection remains separate and hidden from the review packet. Construct and freeze the holdout only after the independent custodian counts gold publish-worthy event groups.

Apollo and Blue Owl archive pages were accessible but pagination was not exhausted. Bain's archive displayed conflicting dates for one unused Vitabiotics item; it was not assigned a guessed date. BasePoint's older rated-note link returned a retrieval error and was not silently described as verified article evidence. The current batch makes no archive-completeness claim.

Human labels have now been supplied and revised. Next work is the planned local prototype implementation and corpus expansion, followed by evidence/label/split freeze and actual evaluation. Additional curation and synthetic-tested implementation can proceed independently, but model inference cannot precede the freeze. No provider adapter, classifier, event grouper, scoring runner or empirical evaluator is yet implemented. The architecture remains local Python and files.
