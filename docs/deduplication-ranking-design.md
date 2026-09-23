# Accepted deduplication and ranking design
23 September 2026. User accepted the design and authorized implementation and public GitHub PDF publication. This document specifies the requested algorithms; actual implementation scope and remaining limitations are recorded in news-events-contract.md and news-pipeline-verification.md. Do not treat the entire design as already delivered.

## Objective and invariants
One event in the all-dates result list, with all its source coverage retained; useful, explainable ordering of events, including within the same priority class.
Preserve existing UI and behavior: Today, Earlier/Later, individual date navigation, manager/sector filtering, EN/ZH and saved language choice, summaries, geography tags, original source links, unreviewed badges, status/error/empty states, mobile layout and automatic refresh. Add controls rather than replace them.
Assumptions: keep Python standard library and static public/ frontend; no database, embeddings or additional model provider; proposed ordinal rules are editorial policy, not calibrated truth.
All 16 source cards in the eight identical-normalized-headline groups remain stored. Their eight groupings are reviewed migration candidates, not permission to merge any future same-headline pair blindly.

## Data additions and ownership
Existing card IDs and per-day records remain stable. Add a versioned event index, not a destructive rewrite of historical articles.
- Event: event_id, member_card_ids, event_kind, resolved_subject/vehicle, object/counterparty, reporting_period, event_date when evidenced, first_seen_at, last_material_update_at, canonical facts with evidence references, representative_card_id, priority fields and merge log.
- Membership: article ID, source URL/publisher, source publication timestamp, duplicate versus material_update versus correction, supporting evidence, assignment rule/version.
- Ranking: priority, severity, time_sensitivity, linkage, evidence_status/strength, reason_en/zh, evidence_refs, ranking_version. Missing means unknown; never fabricate a zero score.
Allocate event_id once and persist it; do not derive it from mutable summary/amount/tag text. Corrections preserve ID and audit log; merge/split corrections retain redirects/mappings.
Codex owns proposed tools/news_events.py, tools/news_priority.py, fetch/summarize/site_data integration and corresponding tests. Claude owns public/app.js, public/index.html, report assets/navigation and UI verification. Agree additive contract before either lane writes against it.

## Deduplication: five stages
1. Same source record
   Preserve original URL and separately normalize only known tracking parameters/fragments; do not strip identifying query parameters. Resolve Google redirects only through accessible supported public responses. An unresolved URL stays unresolved.
   Same canonical URL plus same content hash is a repeat. Same URL with changed facts is an update/correction candidate, not automatically discarded. Existing known-ID short-circuit must be adjusted to permit evidenced revisions.

2. Exact headline candidate
   Normalize Unicode, case, whitespace and typographic quotation/dash differences; remove a publisher suffix only when established as such. Preserve numbers, decimal points, currency, percentages, negation and quarter/year.
   Prefer original source headline; historical generated English headlines can nominate candidates but do not establish identity alone.
   Confirm same subject/vehicle, event action, period and compatible supported facts. For headline-only generic cases without a vehicle/period anchor, do not auto-merge: exact title is necessary candidate evidence but insufficient proof.
   Scan entire retained 90-day archive, not only the current refresh. Numeric changes, different funds or repeated quarterly headlines block automatic merging unless source evidence establishes a correction/update to the same event.

3. Near-duplicate event candidate
   Use normalized resolved subject + event kind + object/counterparty + reporting period/explicit event date. Require at least one discriminating anchor beyond manager and event kind.
   Proposed discovery window: seven calendar days around the event's existing coverage; an explicit matching period/deal identifier can link older coverage across the retained window. The seven-day value nominates candidates; it is not proof or a financial assumption.
   Compare title tokens as a cheap retrieval aid, never as sole merge authority. Validate each proposed member against the event's canonical facts, not just against any member: no transitive similarity chains.
   Matching amount alone is insufficient; $585m versus $590m is a possible rounded amount, not an automatic tolerance rule. Missing evidence is not agreement.
   Ambiguous groups stay separate until reviewed. Do not introduce one model call for every article pair.

4. Preserve meaningful changes
   Supporting repetition -> attach source, no new card in all-dates, no recency/priority bump.
   New evidenced terms, outcome, default, closure or redemption figure -> material update linked to the event, retain old version/date and show Updated.
   Conflicting amounts/outcomes -> flag unresolved conflict; do not average numbers or silently prefer the latest.
   Distinct transaction or reporting period -> separate event. Multi-story roundup -> split into source-backed event records only when facts permit, otherwise leave unmerged/review; never use it to bridge unrelated stories.

5. Present and persist
   One card per event in all-dates, representative summary plus expandable Sources (N), source dates and original links. Choose an already approved, fact-complete summary first; otherwise strongest directly supporting evidence, not latest timestamp. Never turn a reviewed source into a reviewed merged summary automatically.
   In a single-date view group only coverage available on that day, preserving date navigation and earlier facts. A later repeat remains discoverable on its original day as Further coverage; do not inject future updates into historical summaries.
   Global all-dates selection shows the latest evidenced event version once, dated by material update rather than last syndicated mention.
   Filter by verified event tags/parent relations, not union of every noisy model tag. All raw source cards remain accessible through coverage expansion.
   Keep existing raw article counts; add visible unique-event counts. Show '8 events · 16 articles' when applicable; counts must reconcile separately.
   Persist decisions across scheduled runs, test idempotence, and generate migration before/after mapping for rollback. Failed grouping leaves raw cards available.

## Eight exact-headline groups from the 10–23 September snapshot
| Event headline | Dates | Source card IDs |
|---|---|---|
| Apollo private credit fund redemption requests ease in third quarter | Sep 23 | 8d1b134a37a1, 8d1ecbaa14b3 |
| Blue Owl Credit Income amends credit facility, raises $1.3b | Sep 23 | c87e8c1c89f1, 1b2ada6a138a |
| Australia's corporate regulator calls out poor practices in private credit | Sep 22 | e1ef992333f2, 25ad3e7e022e |
| Apollo Provides $585 Million Financing to The Executive Centre | Sep 16/18 | d5bc3cf66452, d1ffa08664f4 |
| US CLO Issuance Slips to $43.8B in August | Sep 17 | 95851197cebd, e0525b7757c6 |
| KKR Doubles Private Debt Deals to $80 Billion as AI Spending Explodes | Sep 17 | 9286b5f69eb9, 222098ffd1b2 |
| Private credit default rate rises to 6.3% in 12 months through August | Sep 16 | 48b80ce93160, abc27e2be1d7 |
| BlackRock private credit fund redemption requests ease in Q3 | Sep 11/13 | 3b1975c239ae, 2cf21a512c1a |

The snapshot's normalization was a broad audit screen. Production normalization is deliberately narrower. Review vehicle/period/source evidence for these candidates before freezing the migration map. Target if all confirmed: 16 display cards become eight event cards, zero source records lost. This does not imply all remaining cards are unique.

## Ranking: fact extraction, decision tree, ordered tie-breakers
One existing structured AI call extracts event facts, scope, timing, entity roles and supporting spans alongside bilingual brief text. The model does not assign arbitrary points or decide its own final rank.
Python validates enum/claim references, applies frozen rules and stores the explanation. Every decisive claim needs supplied evidence. Headline-only records normally remain Needs review unless the supplied source evidence sufficiently establishes the precise event. No claim to have read a full article when only a headline was supplied.

### Priority decision tree
- Urgent: sufficiently evidenced critical adverse effect already occurring, or a material event with an explicit decision/effective deadline within seven days. Examples: payment default, actual withdrawal suspension, material enforcement restriction, severe verified impairment. Routine redemption limits are not automatically a new crisis; changes and context matter.
- Important: evidenced substantial change to credit risk, terms, liquidity, capital formation, strategy or manager franchise, without the urgent condition. Both favorable and adverse changes qualify. Size relative to the affected entity matters; absolute dollars alone do not decide.
- Useful: evidenced, relevant incremental information with bounded consequence and no urgent/important condition.
- Needs review: insufficient evidence, unresolved entity/period, disputed facts or unassessable materiality. It is an assessment status rather than 'least important'. New ineligible candidates follow the filtering rules; this release does not silently delete already published borderline cards.

Needs-review handling: include a visible review count/filter. Credible specific potential critical triggers with unresolved evidence appear in an additive 'Potential urgent item — needs verification' notice, linked to the card and sorted by receipt time. They do not receive a confirmed Urgent badge. Ordinary review items follow assessed events under Priority; Newest still includes all. Distinguish existing human review_status (reviewed/unreviewed) from evidence/priority assessment: an AI-assessed event remains unreviewed.

### Within each class: lexicographic order, first differing field wins
| Field | Proposed descending order | Evidence requirement |
|---|---|---|
| Severity / consequence | Critical, substantial, bounded | Critical = payment/access to capital, severe impairment or systemic strategy disruption; substantial = demonstrated meaningful economics/franchise change; bounded = incremental change. Cite entity-relative magnitude or concrete qualitative effect. |
| Time sensitivity | Effective/decision within 48h, within 7 days, monitor/no deadline | Explicit deadline/effective date or current time-sensitive event. A headline's 'urgent' language is not evidence. Ongoing facts without a decision deadline are not perpetually within 48h. |
| Relevance | Direct monitored vehicle/relevant manager business, direct monitored-sector effect, evidenced indirect transmission | Resolve actual role. Parent mention, equity sponsorship or commentary alone does not create direct credit relevance. |
| Evidence strength | Directly substantiated authoritative record, accessible attributed reputable reporting | Exact source supports exact claim; issuer material is not automatically authoritative on independent risk assessment. Ten syndicated copies do not strengthen evidence. |
| Recency and stability | Latest material update first; then stable event_id ascending | Use actual source/event timestamp; where unavailable use explicitly marked first-observed timestamp. Republishing is not a material update. |

Priority class precedes all fields above. Severity precedes relevance, so broad critical sector stress can outrank a modest directly monitored-manager item. No weighted sum, learned model, random ordering or number-of-sources bonus. Source count is navigation only.
Implementation example (illustrative Python style, enums mapped to ascending ordinal codes):
    def priority_key(event):
        return (
            CLASS_ORDER[event["priority"]],
            SEVERITY_ORDER[event["severity"]],
            TIME_ORDER[event["time_sensitivity"]],
            LINKAGE_ORDER[event["linkage"]],
            EVIDENCE_ORDER[event["evidence_strength"]],
            -event["material_update_epoch"],
            event["event_id"],
        )
Mappings and decision rules are versioned config. Validate missing/unknown required values into Needs review before sorting; do not silently default unknowns into a confirmed tier.
Compute time buckets at refresh using an explicit as_of timestamp and show that timestamp; a later no-new-news refresh still updates deadline buckets. Priority describes importance at last assessment, not a claim that a months-old event needs action today. The all-dates view exposes event date; a resolved gate/cured default is a material update and is reassessed. Never infer resolution merely because time passed.
Choosing a manager/sector filters the set but does not secretly change priority values. Newest orders unique events by last material-update timestamp; language switching never changes rank. Geographic quotas do not alter event importance.

### Hypothetical within-Urgent examples
1. Two critical direct-vehicle events: vote/decision due tomorrow outranks an otherwise comparable action due in five days.
2. Two critical, equally time-sensitive events: direct monitored-vehicle event precedes a comparable sector read-through.
3. Same severity, timing and relevance: a substantiated filing precedes equally relevant reporting supported only by a secondary excerpt.
4. All substantive factors tied: newer material update first; identical timestamps settle by stable event ID.
5. Substantial direct-manager news cannot displace a critical sector disruption solely because its manager is on the watchlist.

## Implementation and verification
Existing stack: Python standard library, pytest tests, static HTML/JavaScript. No new framework required.
Commands:
- Focused planned tests: python -m pytest tests/test_news_events.py tests/test_news_priority.py tests/test_fetch_news.py tests/test_site_data.py tests/test_summarize.py -q
- Repository regression: python -m pytest -q
- Local UI: python -m http.server 8000 --directory public
- Whitespace: git diff --check
Do not run a live paid refresh as a test. Use temporary directories and fake model/source responses; no tests writing repository public/.
Test the eight frozen pairs; same-run and cross-run duplicates; canonical tracking URLs; same URL with correction; different vehicles/periods/amounts/negation; generic identical headlines; material updates; contradictory reporting; roundups and transitive merge traps; source retention; safe undo; repeated runs.
Test each ranking tier and tie-breaker separately, unsupported urgent extraction, missing values, overdue/updated deadlines, potential-risk review visibility, stable replay, duplicate/source-count invariance and bilingual rank parity.
Browser baseline checklist covers every existing feature listed above plus All dates/Priority/Newest/Sources/report viewer. Additive optional event index: if unavailable or invalid, fall back visibly to existing raw cards/date browsing.
For editorial validation, use separate examples to define rules and a blind set to evaluate them. Report exact ordering disagreements and retained ambiguities. No ranking accuracy percentage from a few handpicked cases.
Always retain source records, existing IDs, public-site functionality and rollback mapping. Public report PDF publication is authorized. Keep credentials out of artifacts. Exact remaining API budget and Chinese chart translation scope remain open; no paid calls in this design task.

## Delivery estimate
Dedup exact/history grouping and regression: about 2–3 technical hours inside the accepted 5–7-hour pipeline slice. Priority extraction/rules, near-duplicate handling and integration occupy the remainder, contingent on evidence availability. Ambiguous near duplicates can remain flagged without delaying exact-pair repair. UI/report lanes continue as planned. No claim that these features are implemented yet.
