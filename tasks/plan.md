# Dashboard extension and accuracy plan — updated 25 September 2026

Status: event grouping, All dates, sorting and approved EN/ZH reports deployed; release evidence is docs/release-2026-09-24.md. Pilot pass 2 structurally validated; all 15 cases endorsed by the user. Current disposition: work/analyst-review/priority-pilot-2026-09-24/PASS2_DISPOSITION.md; pass-1 findings remain historical. No review labels imported into production. Historical priority backfill and editorial acceptance remain open.
Target: **Sunday 27 September 2026, Hong Kong time**, extended by the user. Estimates are focused working hours, not a promise of perfect accuracy. The dated Friday schedule below is historical; the following revision supersedes it.

## 25 September execution update — usage-conscious handover

All 15 pilot cases are now endorsed. Pass 2 has 2 Important, 10 Useful and 3 excluded cases. Preferred order: 13, 11, 14, 08, 03, 10, 07, 05, 15, 09, 02, 06. CASE 11 PAG linkage is accepted only as attributed reported indirect context; ASIC action remains sector-level. Full grouping and evidence adjudication is in the local PASS2_DISPOSITION.md; not every proposed cluster is an approved identical-event merge.

Recommended allocation, pending the user's choice: Claude Code owns implementation and PDF work; GPT-6 Sol at medium reasoning handles one bounded independent review and repair verification. GPT-5.6 Sol is an alternative for a reproducible regression, not assumed cheaper. Reserve the current higher-capability session for genuine policy conflicts. Do not run duplicate full-codebase reviews across models. No model switch or agent dispatch has occurred.

| Day | Work / owner | Estimated focused time |
|---|---|---:|
| Friday 25 | Source manifest, correction provenance and conservative grouping/novelty migration — Claude | 3–4 h |
| Friday–Saturday | Evidence retrieval, date/summary/relevance fixes and regression tests — Claude | 4–6 h |
| Saturday | Real inline EN/ZH PDF rendering, separate frontend commit — Claude | 2–4 h |
| Saturday | Freeze candidate; separate ranking/summary and filtering audits — Claude prepares, user labels, Sol reviews | 2–3 h technical + 1–2 h user |
| Sunday 27 | Independent diff/evidence review, bounded fixes, browser checks and one-integrator deployment | 2–3 h |

Total 13–20 technical hours; these replace rather than add to earlier estimates. If capacity is lower, timebox broad source acquisition and full-history backfill. Minimum release: validated known corrections/groups, no recency bumps from repeats, safe unknown-evidence states, actual inline reports, and explicit acceptance results. Do not tune on held-out labels or promise perfect filtering accuracy.

Merged and deployed 25 September (PR #3, merge cc22423): accuracy lane (grouping/novelty overlay v2, 214 -> 172 events; evidence retrieval; brief-v3-evidence), inline EN/ZH reports with PDF.js, and source tiers (SEC EDGAR for 13 registrants, Fed/SEC/ECB/BoE/ESMA, ASIC sitemap, GlobeNewswire/PR Newswire, best-effort GDELT). Live site verified serving events-v2 (222 cards, 172 events) and the PDF.js viewer. Evidence: docs/accuracy-handback-2026-09-25.md, docs/source-tiers.md.

26 September acceptance (frozen candidate 0dff5a1; local RESULTS.md): Part A false inclusions 2/20, summary factual errors 8/20 (7/19 without leaked A17), grouping errors 7/20 (6/19); Part B false inclusions 3/10, false exclusions 1/15; Part C 0 misses of 5 (one a day late). User policy decision: relevance covers all tracked-manager and sector matches, not only market-level news, so A09, A12 and F22 are acceptable inclusions (remaining false inclusions under this policy: F23 roundup; F11 equity stake undecided). Fixes on branch claude/acceptance-fixes: archive-wide grouping sweep (177 -> 153 events), display-time hiding of unread-article claims, regulatory-proposal keywords, roundup prompt, SEC div-only text extraction. These were tuned on the packet's findings, so the packet is no longer blind for those aspects.

Critical path to the Sunday minimum release: the only unmet item is explicit acceptance results. They depend on the user labelling work/analyst-review/acceptance-2026-09-25/ (candidate frozen at 0dff5a1; labels scored against it, never used to tune it). Then: first scheduled refresh with the new tiers (Monday 28 September 08:00 HKT) is checked for feed failures, GDELT success, SEC items and spend; phone check of inline reports. Paid-call budget is still unestablished; excerpts and filings make briefs longer under the same call caps.

Ready-to-copy handover: docs/handover-claude-sunday-accuracy.md. Existing Reports prompt: docs/handover-claude-inline-pdf.md. Grouping/novelty must precede timing tie-breaks; correcting novelty alone does not resolve every endorsed within-Useful preference. Preserve Important status of underlying events when repeated coverage arrives.

## Sunday revision: prioritize evidence and filtering accuracy (24 September baseline)

- Thursday: finish draft validation and obtain human endorsement/corrections for CASE 06–15. Separate factual evidence checks from subjective relevance/order. Completed structural checks and source spot checks are documented in the local report. User time: roughly 30–60 minutes for the remaining cases if sources are accessible.
- Friday: Codex addresses source-evidence acquisition and date provenance, then targeted relevance/summary failure modes. Estimate 5–7 technical hours, contingent on accessible sources. Preserve unknowns and blocked sources. Pilot cases are development data. Do not tune severity labels merely to fit ranks. Keep the legacy failed calibration recorded.
- Saturday: freeze the candidate policy before examining new labels. Prepare a separate 20-event ranking/summary acceptance packet with no overlapping underlying stories, plus a 20–30-candidate filtering audit spanning accepted and rejected items and independent source-discovery checks. Estimate 3–5 technical hours plus 1–2 analyst hours. These are bounded audits, not population accuracy guarantees. Record sampling method and stratification; do not report a combined precision percentage from an artificially balanced sample. If historical rejected evidence is missing, disclose the gap and use prospective evidence rather than claim historical recall.
- PDF lane after the remaining review: Claude receives docs/handover-claude-inline-pdf.md; implement/verify actual inline English and Chinese report rendering, preserving secondary Open/Download controls and existing UI. Estimate 2–4 technical hours. Codex integrates; no parallel ownership of pipeline files.
- Sunday: resolve documented disagreements, run regression and browser checks, and deliver exact included/excluded/uncertain/missed counts with limitations and rollback. Estimate 2–3 technical hours. Acceptance must separately cover relevance, summary facts, deduplication, priority ordering and evidence completeness. No unsupported urgent labels; no known critical miss left unreported. If a check fails, retain its failure rather than lower the criterion after seeing results.

Immediate sequencing: evidence recovery and source fidelity before historical priority publication. No extra paid historical rerun is authorized by a deadline extension alone; retain existing spend caps and establish the remaining budget before additional model runs. The current request is validation/comparison and schedule revision; no production filtering change is made by this review.

## Recommendation
Ship an all-dates view, explainable editorial priority sorting with urgent event deduplication, and English/Chinese PDFs hosted in the existing public GitHub repository. The user explicitly authorized public PDF publication on 23 September; no authentication or private-host dependency remains. Keep the current static site and single structured model call. Preserve every existing feature and UI control except explicitly requested changes. Do not make full historical classifier recalibration the Friday dependency.

## Verified starting point
Read the Codex task "Build News Dashboard" (01a08b60-1cde-71c1-99b1-9a094a3f0817) and the linked ChatGPT conversation (6aa25386-6e9c-83ec-bc1a-079ff85968ba).
Remote index fetched 23 September: 182 cards across 34 dates, 12 August–23 September. Local data stops 13 September; reconcile remote before edits, preserving the untracked .claude directory.
Live path is public/, tools/fetch_news.py, tools/summarize.py and tools/site_data.py. Archived research pipeline is not the deployed classifier.
Remote status records a successful scheduled refresh on 23 September, 28 feeds successful, 13 added and 11 model rejected. Workflow configuration targets weekday 08:00/16:00 HKT; this does not prove every historical scheduled run succeeded.
Current cards have no relevance score. Frontend filters a single selected day; backend orders by published_at.
Original baseline holdout result: 75% precision, 14.3% recall and 1/2 critical events. This was deterministic filtering; it is not a measured result for the current brief-v1 DeepSeek pipeline.

## Quick quality validation
Scope: all 113 saved cards dated 10–23 September (13 nonempty dates). Checked structure, headline/content patterns and code; selected source checks only. No audited recall or full factual accuracy claim.
- 110 auto_fetch/unreviewed, 3 analyst_labeled/reviewed. All have nonempty EN/ZH headline and summary fields; translation accuracy is not established by field presence.
- Eight normalized-identical-headline groups (16 cards). Same-event near duplicates are more numerous: Apollo redemptions, KKR Akrapoint, Blue Owl financing and Fitch defaults recur.
- 55/113 summaries contain a basic thin-evidence phrase pattern. This is a triage count, not 55 proven factual errors.
- 100/113 source URLs are Google News redirects, not canonical underlying article URLs.
- 23 September has 25 cards, 17 September 17; the original 6–10 unique-event editorial objective is not enforced.
- CIFC 17 September: cards 460530fb1372 and c5bdabf2be3f cover the same ACI article. One asserts no further details were disclosed; the other includes manager size and lower-middle-market scope. Original page was opened. Prefer "not available in the supplied excerpt" or omit filler; never make claims about unread full articles.
- Vehicle error: 3cb3dac78660 describes Blue Owl Technology Income Corp. but is tagged otf (Technology Finance). Blue Owl product materials distinguish these vehicles. Also ensure parent manager filtering includes appropriate child vehicles without conflating them.
- Review candidates: Datavant minority equity stake (6e521167dacd), routine stock coverage initiation (bce4f32145d7), and generic executive commentary. Saved evidence does not establish their credit materiality; treat as suspected editorial false positives pending source review.
- Root causes: dedupe compares incoming titles within a run, stored history only by URL ID; same event can return from another source/run. Keyword "minority stake" satisfies credit context. Broad event keywords such as CEO/million do not establish economic materiality. Model relevance reason is discarded by make_card. Current simplified demo rules differ from the richer editorial rulebook; record this explicitly, do not claim full rulebook compliance.
- Rejected IDs alone cannot reconstruct a false-negative denominator. Save future candidate evidence/decisions privately; assess source coverage and missed events separately.

## Ordered delivery slices
### 1. Freeze examples and priority contract — 1.5–2 hours
Owner: Codex review with analyst. Dependencies: none.
Choose 12–15 distinct events for analyst Important/Useful/Low priority examples and 20 separate recent events for blind checking. Include sector-only news, direct manager news, critical risk, duplicates, thin evidence and equity-only involvement.
Acceptance: define materiality relative to affected entity; A/B/C are eligibility categories, not automatic priority order; score does not rescue insufficient evidence.
Verification: analyst reviews examples before prompt/rule freeze. Resolve discrepancy between demo filtering and original rulebook for this release.
Likely files: config priority definitions, docs/site-data-contract.md, plan/checklist.

### 2. Priority computation and focused quality fixes — 5–7 hours
Owner: Codex implementation; Claude independent review. Dependencies: slice 1.
Split into three checkpoints of roughly two hours: evidence/entity metadata; event grouping and priority computation; saved-output/fixture regression.
Use proposed Urgent / Important / Useful priorities with Needs review as an orthogonal evidence status, one short reason and ranking version. Python derives class and lexicographic ordering from validated evidence-linked facts: class, severity, time sensitivity, relevance, evidence strength, latest material update, stable event ID. Potential critical unresolved reports get a visibly unverified review alert. Exact rules and within-class examples are in docs/deduplication-ranking-design.md. No six-component score is computed in this release.
Extend the existing structured brief only if needed; Python validates and orders. No extra autonomous research agents per article.
Persist canonical source, event key, publication versus first-seen date and ranking inputs. Conservatively combine corroborating reports across runs; preserve material updates and all source links. Fix OTIC/OTF distinction and parent filter propagation.
Backfill existing 182-card archive from reusable evidence/cache; bound any new calls and do not invent scores from headline-only inputs. Keep unscorable cards visible with evidence limits.
Verification: deterministic sorting, supported urgent placement, no false event merges, parent/vehicle distinctions, unknown fields, EN/ZH parity, retry/call cap and compatibility with existing cards. No public-data writes during tests.

### 3. All-dates browsing and sorting UI — 2–3 hours
Owner: Claude Code. Dependencies: agreed metadata contract; can proceed using fixtures while slice 2 builds.
One global list across all retained dates; manager and sector filters intersect and persist when date mode changes. Keep Today/specific date modes.
Add Priority/Newest sort, date per card, result count, priority reason and evidence indicator. Priority sort must order globally rather than reset in daily groups.
At current volume, cached loading of all 34 day files is adequate; show partial-load failures explicitly. Small rendering chunks acceptable without forcing date navigation.
Verification: raw article and unique-event counts reconcile separately; oldest/latest dates remain accessible; combinations of filters, race conditions, missing day files, mobile/keyboard and both languages pass. Existing Today, Earlier/Later, date selection, language persistence, manager/sector tags, source links, review badges and status messages remain. Latest sort remains a reliable fallback.
Likely files: public/app.js, public/index.html, focused UI fixtures/checks.

### 4. Bilingual report route — 3–5 technical hours plus 4–7 analyst hours
Owner: analyst translation/content; Claude viewer/navigation/layout.
Document inventory: approximately 7,752 words, 39 tables, 46 media assets and exhibit labels through 58. Read content only; no full layout/fact audit.
The user has explicitly authorized uploading the report PDF to GitHub while keeping the repository public. Publish final EN/ZH PDFs under public/reports/ with a Reports entry, language choice, embedded PDF where supported and open/download fallback. Preserve source attribution and report content; no authentication work is required.
Preserve all figures, source citations, approximation caveats, table structure and exhibit references. AI drafts narrative translation only in an approved environment; analyst reviews terminology, numbers and charts. Existing English chart labels can remain only with an explicit partial-translation label and analyst acceptance; full bilingual chart redraw would add approximately 6–12 hours.
Verification: PDF page/layout comparison, no missing exhibits/tables, numeric parity, source notes, correct version/date, publicly working viewer/open/download links.
Open decisions: Simplified versus Traditional Chinese; whether chart labels must all be translated. Default proposal is Simplified, matching the existing dashboard.

### 5. Acceptance and release — 2–3 hours
Owner: Codex integration/review; user/manager editorial sign-off. Dependencies: slices 2–4.
Run focused regressions plus repository tests and real-browser checks; simulate refresh with fake model responses and temporary data directory. Compare before/after output on frozen examples.
Proposed product acceptance (agree before judging): no critical event below routine stories in the blind set, no unsupported urgent labels, and analyst accepts at least 8 of top 10 distinct events. Report exact counts/disagreements; small-sample acceptance is not calibration proof.
Confirm existing automated refresh and every existing UI feature still work, additive priority metadata is compatible, deployed report PDFs match the approved versions, and rollback restores prior data/UI. Group source cards without deleting their underlying records.
If ranking check fails, release all-dates/report access with Newest and analyst-pinned priorities; do not advertise validated automatic importance.

## Schedule and effort
Wednesday 23 September: examples/contract and quality triage; analyst starts translation.
Thursday 24 September: ranking/dedupe and UI in parallel; report preparation in parallel.
Friday 25 September morning: blind check, browser/regression testing, content approval and release. Reserve afternoon for fixes.
Base technical effort: 13.5–20 hours, roughly 1.5–2 working days elapsed with two coordinated coding lanes. Analyst effort: about 5–9 hours including translation, ranking review and final check. Fully Chinese chart redraw is additional. Public PDF authorization removes the private-host/authentication dependency. Inside the 5–7-hour ranking/quality slice, allocate approximately 2–3 hours to exact/cross-run duplicate grouping and its regression checks; do not add that estimate twice. Re-estimate if evidence recovery for ambiguous event groups exceeds the timebox.
Exact currency cap is not established in this turn. Confirm remaining cap before paid calls; run a small token measurement and extrapolate with retry allowance, enforce a dollar/token ledger and call cap, cache by evidence/prompt/model/version. No automatic historical full-model rerun.

## Composite score decision
The original six-component composite is not used, publicly or privately, in this release. Use the explicit decision tree and ordered tie-breakers in docs/deduplication-ranking-design.md instead. The historical failure does not isolate score weights as its cause; rejecting reuse for this deadline is a product/design choice, not proof that every weighted scoring method fails.
The baseline failed largely because sector-relevant events never passed entity-centric filtering. Tuning score weights cannot recover unseen events. Preserve the old FAIL and original labels. Any future recalibration uses separate new held-out labels after tuning, includes rejected/source-missed candidates and reports precision, recall and ranking separately.

## AI use architecture
User/manager: priority examples, translation approval, report audience, final acceptance.
Codex: editorial contract, scoring/data pipeline, integration and release evidence.
Claude Code: frontend and report navigation with mocked agreed data; independently reviews Codex ranking changes.
Production: feeds -> deterministic discovery filter -> one structured brief -> evidence/entity validation -> event grouping -> deterministic priority order -> static JSON -> dashboard.
Report: supplied document -> translation draft -> analyst review -> EN/ZH PDFs in public/reports/ -> public viewer/open/download links.
Single integrator; file ownership split; neither agent overwrites the other's work. Preserve all existing features and UI controls. Public PDF publication is already authorized; do not ask for that permission again.

## Evidence links
- https://github.com/Bobksl/Fund-Coverage-News-Dashboard/blob/main/public/data/index.json
- https://github.com/Bobksl/Fund-Coverage-News-Dashboard/blob/main/public/data/2026-09-23.json
- https://github.com/Bobksl/Fund-Coverage-News-Dashboard/blob/main/public/data/2026-09-17.json
- https://github.com/Bobksl/Fund-Coverage-News-Dashboard/blob/main/tools/fetch_news.py
- https://github.com/Bobksl/Fund-Coverage-News-Dashboard/blob/main/tools/summarize.py
- https://github.com/Bobksl/Fund-Coverage-News-Dashboard/blob/main/docs/phase-2-disposition.md
- https://alternativecreditinvestor.com/2026/09/17/cifc-launches-direct-lending-strategy-on-icapital/
- https://www.blueowlproducts.com/our-products
