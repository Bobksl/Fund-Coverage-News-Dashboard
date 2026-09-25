# Accuracy handback — 25 September 2026

Branch `claude/sunday-accuracy`, based on origin/main `a20f460`. Not pushed or deployed; one integrator merges. Backend accuracy only: no frontend file, report or PDF changed. The inline PDF lane (docs/handover-claude-inline-pdf.md) is untouched.

## Commits

| Commit | Scope |
|---|---|
| 8be740e | Reviewed overlay v2: survivor IDs + aliases, member roles, date corrections, relations, anchored archive-wide novelty; representative ignores absence filler; UI tests derive sizes from data |
| a850fff | Bounded source retrieval (tools/source_evidence.py) in refresh; prompt brief-v3-evidence; absence-claim stripping; role-tagged managers |
| bf5910f | Explicit regeneration of public/data/events.json after migration review (only data file changed) |
| adcc227 | Dry runs list rule-rejected items for prospective recall audits |
| 0dff5a1 | Contract documentation (additive) — **frozen candidate** |

Changed files: tools/news_events.py, tools/summarize.py, tools/fetch_news.py, tools/source_evidence.py (new), config/news_event_groups.json, public/data/events.json, docs/news-events-contract.md, tests/test_news_event_overlay.py (new), tests/test_source_evidence.py (new), tests/test_evidence_pipeline.py (new), tests/test_fetch_news.py, tests/test_dashboard_ui.py. tools/news_priority.py and tools/site_data.py unchanged.

## Archive before/after

| | Before (a20f460) | After (bf5910f) |
|---|---:|---:|
| Source cards | 222 | 222 (day files byte-identical) |
| Dates | 36 | 36 |
| Events | 214 | 172 |
| Reviewed groups / cards | 8 / 16 | 12 / 62 |
| Recorded aliases | 0 | 42 (all 214 earlier IDs resolve) |
| Related-event links | 0 | 3 relations |
| Publication-date corrections | 0 | 1 |
| Assessed priority | 1 Useful, 213 Needs review | 1 Useful, 171 Needs review |

Partition checked: every card in exactly one event; no earlier event split.

## Grouping manifest (decisions in config/news_event_groups.json)

| Survivor | Cards | Decision |
|---|---:|---|
| evt-reviewed-001 | 27 | Merge: Apollo Debt Solutions Q3 2026 tender (~14.7% requests, cap unchanged). 17 same-quarter items beyond the pilot list found by full-archive check. 4 share-price/commentary items are `reaction`. |
| evt-reviewed-002 | 8 | Merge: OCIC 22 Sep financing disclosure. Representative states $1bn notes and $4.2bn line; "$1.3b" is cumulative since 30 Jun. |
| evt-reviewed-003 | 3 | Merge: same ASIC sector-statement article under two headlines. |
| evt-a0f3329b83e8 | 2 | Merge: direct and Google-News links to one ACI Remara article (slug and 09:36:30 UTC match). |
| evt-reviewed-007 | 8 | Merge: Fitch 6.3% TTM-through-August release; whole prior membership kept. |
| evt-06b3269f6fce | 2 | Merge: Futu repost of Bloomberg 17 Sep default-measures explainer. |
| evt-f6e820e3975b | 2 | Merge: Tether release names "StableFund, a Tether-Fasanara Lending Fund" (one vehicle); $400m committed, $3bn target. |
| evt-b9177fe8e7f4 | 2 | Link KBRA rating as dated `update` of the OTF $400m 6.500% 2029 notes; its card's publication corrected 17 Sep (feed/observation) -> 18 Aug, event date 17 Aug (KBRA). |

Related, kept separate: Remara orders / ASIC statement / enforcement-warning coverage / Bathla collapse; Fitch release / methods explainer; Apollo Q3 tender / 24 Sep multi-cause share move / unanchored 13 Sep rehash. Unchanged reviewed pairs: 004, 005, 006, 008. Not merged: Blue Owl–Loparex trio (unanchored identical headlines; not reviewed in this pass).

PAG is not tagged on the Remara event; the reported PAG–Bathla link remains attributed indirect context only. The A$39.9bn secondary-article error appears in no archived card. The OCIC 23 Sep repayment is confirmed by a quoted 8-K sentence but has no archive source card, so no material update was published for it.

## Tests and checks

- Full pytest: 423 passed, 14 subtests, no skips (includes real Chromium UI tests) on the migrated archive.
- New failing-first tests: overlay/novelty (10), source retrieval (8), evidence pipeline (7), dry-run rejections (1). They cover idempotent replay, alias persistence across rebuilds, all-source partition, merged-group closure, no-future-leak day views, late-arriving repeats, real material updates at corrected time, stale-hash invalidation, SSRF/redirect/size/type/time limits and retrieval error recovery.
- Pre-existing UI test failure on main fixed (it assumed no assessed event; the scheduled refresh produced one).
- Ruff clean on all owned files (26 pre-existing findings remain in archived research modules). `git diff --check` clean. No test writes public/.

Browser (in-app Chromium, local static server): All dates shows 172 events · 222 articles · 36 dates, 12 multi-source groups; the Sources (27) disclosure opened with 27 links; 17 Sep view shows the KBRA card as "Further coverage · first reported Mon, 17 Aug 2026" and its link opens 17 Aug without the September card; 中文 + PAG filter shows 0 of 172; Newest order is monotone by material time with the Apollo event at its 22 Sep time; no console errors. PDFs were not exercised (not in this lane).

## Pilot replay (diagnostic, not accuracy)

Endorsed labels as assumptions; only identity and material times from the pipeline.

| | Order | Discordant pairs vs preferred (of 66) |
|---|---|---:|
| Before | 13 > 11 > 14 > 07 > 10 > 02 > 05 > 09 > 03 > 08 > 15 > 06 | 16 |
| After | 13 > 11 > 14 > 07 > 10 > 02 > 05 > 03 > 09 > 08 > 15 > 06 | 15 |
| Preferred | 13 > 11 > 14 > 08 > 03 > 10 > 07 > 05 > 15 > 09 > 02 > 06 | — |

Unresolved policy, not fitted: 03 > 05 > 02 and 03 above 10/07; C08 sector explainer above direct-manager Useful items. Both need a written decision-relevance contract before any rule change. The six-component score remains rejected.

## Acceptance packet (frozen before labels)

Local only: work/analyst-review/acceptance-2026-09-25/ (FREEZE.json with commit and file hashes). Results are pending user labels; denominators are fixed now:

| Measure | Denominator |
|---|---|
| Relevance / false inclusion (Part A) | 20 events |
| Summary factual errors, grouping errors, evidence abstentions (Part A) | 20 events |
| Order disagreements | included Part A events, pairwise |
| False inclusions (Part B) | 10 published items |
| False exclusions (Part B) | 15 rule-rejected items (8 no manager/sector, 5 no material event, 2 excluded keyword) |
| Missed events (Part C) | open-ended user discovery list |

Historical model rejections have no text: historical recall is unavailable and no overall accuracy is claimed.

## Operational change on merge

The scheduled refresh will request at most 30 publisher pages per run (10 s per hop, 3 redirects, 1 MB, 30 s total per page). Google News links are not decoded, so most items remain headline-only and Needs review. Excerpts can add up to ~2,500 characters per brief; model, provider and call caps are unchanged. The evidence cache lives in work/ and is not committed or deployed.

## Rollback

Revert on current main without resetting history or dropping newer data: `git revert 0dff5a1 adcc227 bf5910f a850fff 8be740e`, then `python -m tools.news_events --data-dir public/data` to rebuild events.json from retained day files, run tests, push normally. Old event IDs remain resolvable because the reverted code rebuilds from membership; no source card is deleted either way.

## Fresh-main reconciliation

If scheduled refreshes land first: `git fetch origin && git merge origin/main`. On conflict take origin's day files, index, status and seen. For events.json take origin's copy (`git checkout --theirs public/data/events.json`), then regenerate with `python -m tools.news_events --data-dir public/data` so aliases derive from the latest membership. Verify partition (every card once, every prior event ID live or aliased), run `python -m pytest -q`, commit the merge and push normally. New syndicated copies of a reviewed story join it automatically only when their source headline exactly matches a reviewed member's source headline with an anchor; other repeats need a reviewed overlay entry.
