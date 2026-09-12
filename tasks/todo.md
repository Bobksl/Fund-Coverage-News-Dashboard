# Handover checklist

- [x] Architecture review: compare original stages and infrastructure; verify scope against handover.
- [x] Entity specification: all 13 watchlist entries resolve or have a documented review flag; verify evidence and relationship direction.
- [x] Sector/theme/taxonomy specification: eight sectors and all approved themes; validate event/sector references.
- [x] Editorial specification: gate precedence, scoring anchors, overrides, duplicates and geography; examine positive/negative pairs.
- [x] Verification: parse all configs, validate IDs and examples, inspect diff and report limitations.
- [x] Phase 2 start: amend four experiment controls; confirm Bayview/BasePoint and monitoring-only scope; create initial 20-article link packet with blank analyst labels.
- [x] Verify packet metadata allowlist, blank labels, stable output under gold-label changes, and overwrite protection.
- [x] Receive 20 completed analyst labels; preserve original bytes and audit formatting, coverage, enums and event-group consistency with synthetic regression tests.
- [ ] Resolve submitted-label adjudication items and capture source evidence before gold freeze. Do not infer or alter analyst decisions automatically.
- [x] Verify three analyst corrections; review all 20 source articles and locate supplementary primary evidence; preserve revised labels and update Claude handover.
- [ ] Resolve remaining calibration taxonomy/rubric disagreements and freeze the actual evidence payload; a source-link review is not a model-input freeze or Phase 2 pass.
- [ ] Phase 2 remaining: broaden corpus, obtain independent human labels, freeze evidence/labels/split, implement and compare baseline and LLM, apply separate cohort acceptance criteria. No model inference before label freeze.
- [x] Phase 2 engineering: implement the local baseline, classifier adapter, decision validation,
      predicted grouping, scoring/ranking, saved-output replay, evaluator and corpus tooling with
      synthetic tests. Engineering only; establishes no empirical result. See docs/phase-2-engineering.md.
- [x] Phase 2 engineering, part two: shortlist-only bilingual drafting with parity QA, calibration
      stability reruns, provider usage/latency capture and the custodian command line. All experiment
      implementation tickets are now built; still no inference and no empirical result.
- [x] Collection decisions recorded in docs/natural-feed-policy.md and the window/roster frozen.
- [x] Natural-feed collection run 1: 150 records from 12 sources, window 2026-08-12..2026-09-10,
      cutoff 2026-09-04. Five gaps logged. See docs/phase-2-collection-status.md.
- [x] Commercial Observer resolved by retrieval: 83 in-window records with exact timestamps, via the
      site's public REST API. Landing page is not an archive; Finance channel enumerated instead.
- [ ] Freeze the SEC CIK and form roster, then collect that tier.
- [ ] Curate the challenge set, then build one combined blinded analyst packet across both cohorts.
- [ ] Analyst input required before any inference: resolve the two calibration disagreements, obtain
      second-reviewer labels, and capture the permitted evidence payload for joint label/evidence freeze.
- [ ] Phase 3 ingestion pilot: blocked at the entry gate on 2026-09-11; see docs/phase-3-entry-gate.md.
      Do not start collectors before the Phase 2 disposition exists.
- [x] SEC CIK/form roster frozen: 11 verified issuers, 4 unresolved, 9 forms in scope.
- [x] SEC tier collected: 12 in-scope records from 43 filings across 11 CIKs.
- [x] Challenge curation: 91 records, every coverage minimum met. 60 are linked natural-feed
      records and 31 are independent; the overlap must be disclosed with any challenge figure.
- [ ] Capture permitted evidence text for both cohorts and hash it for the joint freeze.
- [ ] Build the combined blinded packet once the challenge cohort is adequate.
