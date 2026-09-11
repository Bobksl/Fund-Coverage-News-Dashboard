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

## Phase 2 packet slice — 2026-09-11

The preceding section is the historical Phase 1 verification record. Bayview/BasePoint intent is now confirmed and the initial Phase 2 packet is created; the benchmark remains unexecuted.

- RED: unittest discovery failed with ModuleNotFoundError before the packet builder existed.
- GREEN: two focused unittest methods pass, covering metadata allowlisting (including nested gold metadata), blank human labels, unchanged article bytes after hidden-label changes, overwrite refusal, duplicate IDs and unsafe URLs.
- A subsequent test run encountered Windows temporary-directory access/cleanup errors. Tests now use an isolated temporary directory under ignored workspace work/; rerun passed without changing application checks.
- The sandbox temporary-directory error recurred later even under work/. The final focused suite passed outside the sandbox with automatic approval, preserving every assertion. This is an execution-environment limitation, not a suppressed test failure.
- The existing specification validator still reports seven JSON files, 30 entities, 23 sources, eight sectors, 11 themes, 15 event types and 18 hypothetical cases with no errors.
- The generated local packet has 20 unique article IDs and 20 blank label rows. Input hash is recorded. This hash does not freeze the linked web content.
- Read-back caught a Windows CRLF/UTF-8 hash mismatch in packet 001. A regression assertion reproduced the failure; byte-exact JSONL writing fixed it. Packet 002 supersedes 001 with unchanged IDs; its on-disk hash is checked. No labels or predictions were present in either version.
- No model calls, human gold labels, event-group predictions, empirical metrics, automated ingestion or dashboard implementation were produced. The packet builder is not an implemented classifier or evaluation engine.

## Completed-label intake review — 2026-09-11

- Human labels have now been submitted for all 20 starter articles. Original bytes were copied and hashed privately; the submitted file was not modified. The copy is as-received evidence, not adjudicated gold.
- Added evaluator-only `tools/audit_labels.py` for required columns/values, article coverage, explicit date formats, enum checks, duplicate IDs and conflicting event publication labels. It produces no inference inputs and cannot declare gold freeze ready.
- Five synthetic audit tests first failed on the absent module, then passed after implementation. The full seven-test suite passed outside the sandbox under the same approved temporary-directory workaround. Synthetic tests are not classifier-performance evidence.
- Provisional normalization only trims outer whitespace, omits an entirely blank final row and records an explicit MM/DD/YYYY interpretation. No publication decision or event ID changed. Consistency issues are recorded in the private evaluator review and sent to the analyst; factual grounding was checked for the specific Zurich attribution only, not asserted for every submitted rationale.
- Phase 2 remains incomplete: adjudication, source-evidence capture, full cohort construction and the actual prototype/evaluation remain required. No inference or Phase 3 promotion occurred.
