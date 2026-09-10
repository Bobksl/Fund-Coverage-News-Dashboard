# Phase 1 verification

Date: 2026-09-10. Scope: local specification and static configuration consistency.

## Completed checks

- `python tools/validate_spec.py`: seven JSON files, 13 watchlist entries, 30 entities/platforms, 23 evidence sources, eight sectors, eleven themes, fifteen event types and eighteen hypothetical cases; zero reported errors.
- Checks cover duplicate JSON keys/IDs, non-finite JSON values, config versions, required entity fields, evidence/rule/entity references, typed parent edges and absence of cycles, domain formatting, sector/theme references, six score weights totalling 100, contiguous publication bands and arithmetic/anchor consistency for scored examples.
- Initial static review caught H04's 78-point score incorrectly labelled priority. Corrected the expected label to ordinary shortlist; no weight or threshold was changed to force the example through.
- Checked 19 deliverable files for trailing whitespace, all 20 local Markdown links for existing targets, and the Python checker's syntax: no errors. Git whitespace checks also passed.
- Reviewed specific-vintage handling, adviser versus investor roles, OTF parent attribution, NB conditions, GP-led secondaries versus GP stakes, evidence-first gates, geography separation and override precedence against the supplied brief.
- Public primary-source research is recorded by URL and verification date; source-text access limitations are explicit. PAG current-site access and the broad Neuberger renaming claim remain flagged. Bayview/BasePoint mandate intent remains an analyst question.

## What these checks do not establish

No real-article benchmark, automated entity resolver, scoring engine, ingestion job, model integration, browser UI, translation QA, production build or deployment was run. Hypothetical cases demonstrate intended decisions and arithmetic only; they are not passing classifier tests. The static checker is not a full formal schema validator and does not verify source truth or semantic entity resolution.

The referenced conversation returned five exchanges but three replies were truncated at 20,000 characters. Browser retrieval failed to recover the rest. The detailed current handover supplies the implementation scope; reconcile any subsequently supplied missing conversation text before freezing Phase 2. Full-history review is therefore a documented limitation, not a completed check.

No relevant workspace memory entry was found. The requested I Have ADHD plugin had no available callable tools. The using-agent-skills supplemental definition-of-done reference was absent from its skill directory/search; scope-appropriate verification is reported explicitly here. No unrelated quantitative research session was modified.

See [Phase 2 experiment](phase-2-experiment.md) for the actual empirical readiness bar. Specification readiness does not imply analyst sign-off, accurate story selection or approval for unattended publication.
