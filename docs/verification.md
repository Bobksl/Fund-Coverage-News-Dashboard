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

## Revised full-batch source review — 2026-09-11

- Re-ran the existing evaluator audit on the analyst's revised submission: 20 complete unique article records, 20 distinct event IDs and no structural errors after formatting-only normalization. Revision changes are recorded by article ID in private evaluator review-002. Prior submitted bytes remain untouched.
- Opened every original article source and checked the relevant core event/role passages. Located supplementary official/SEC evidence for details missing from the original release; per-record references/limitations are in private source-review.json. This is source support review, not a frozen corpus or blind prediction test.
- Three earlier adjudication corrections verified. Two calibration taxonomy/rubric disagreements remain documented without changing the analyst's labels. All current event groups are singletons, so duplicate-consolidation recall is untestable on this batch.
- Updated the final handover document and Phase 2 readiness disposition to remove stale blank-label state. No code behavior changed in this review turn; JSON/ID/hash/link checks and the existing spec validator were used. No model-performance metric or Phase 3 promotion is claimed.

## Phase 2 engineering slice — 2026-09-11

Scope: the local pipeline implementation in [phase-2-engineering.md](phase-2-engineering.md).
Engineering completion is recorded separately from empirical readiness; no inference ran.

- RED: each new module's tests failed on `ModuleNotFoundError` before the module existed; the
  suite then passed after implementation. Test count grew from 7 to 119.
- `python -m unittest discover -s tests -v`: 119 tests pass, covering the evidence/decision
  contract, the inference allowlist and nested-leakage refusal, baseline entity resolution,
  gates/bands/ranking/ablation, classifier retry and replay, conservative grouping, runner
  idempotence and overwrite refusal, evaluator counting and freeze enforcement, corpus splits and
  sufficiency, plus end-to-end wiring.
- `python tools/validate_spec.py`: unchanged — seven JSON files, 30 entities, 23 sources, eight
  sectors, 11 themes, 15 event types, 18 hypothetical cases, zero errors. No config, threshold,
  ontology or scoring weight was changed by this work.
- `git diff --check`: clean. Tests write only to an ignored directory under `work/`, matching the
  earlier sandbox temporary-directory workaround, and clean up after themselves.
- Defects found and fixed during the slice, each with a regression test: `"CLO"` matched inside
  `"closes"` (event phrases now match whole tokens); a parent brand matched inside a longer vehicle
  name and was double-counted as a second subject (ER05 precedence, parent kept as propagated);
  two unresolved articles merged into one invented event through a publisher fallback in the
  predicted parties; a null total on an ambiguous cluster violated the contract's sum rule; and a
  tagged sector propagated up to ten themes, which is now reported as unassigned candidates.
- A synthetic six-article demo ran through the documented command: six articles in, six with an
  outcome, five predicted events, one duplicate collapsed, one bare-namesake case routed to review,
  zero invalid decisions, zero silent drops.
- Not established: no model call, no real-article benchmark, no cohort, no holdout, no precision,
  recall, clustering, identity, bilingual, usefulness, cost or latency result. Synthetic fixtures
  are wiring evidence, never classifier performance.

## Phase 2 engineering slice, part two — 2026-09-11

Closes the remaining implementation tickets: bilingual drafting, stability reruns, provider
usage/latency capture and the custodian command line. Still no inference and no empirical result.

- RED then GREEN for each addition; the suite grew from 119 to 148 tests and passes.
- `python tools/validate_spec.py`: unchanged, zero errors. No config, threshold, ontology or
  scoring weight was touched.
- Drafting: shortlist-only, refuses any other recommendation. Checks claim references, unsupported
  figures, cross-language quantity parity, currency parity, party retention and dropped or added
  uncertainty. Verified that `$7.3 billion` and `73亿` normalize to the same value, so a correct
  translation is not reported as a defect and a mistranslated `37亿` is.
- Stability: refuses any partition not named calibration and refuses a single run. A deterministic
  engine reports a 1.0 stable share; a deliberately flaky stub is detected and routed to review
  rather than averaged.
- Classifier: bounded-retry loop extracted and shared with drafting. Provider-reported token counts
  and measured latency are recorded; `cost_basis` stays null because no rate card exists.
- Custodian command line exercised end to end in tests: packet, split, freeze, then evaluate.
  Appending one byte to a frozen predictions file makes the evaluator refuse, as intended.
- One test assertion was wrong and was corrected, not the code: a quantity mistranslated in one
  place surfaces as an added figure rather than a missing one, because the correct figure still
  appeared in the headline. Both directions are now covered.
- Not established: still no model call, no cohort, no holdout, no precision, recall, clustering,
  identity, bilingual-sample, usefulness, cost or latency result on real articles.
