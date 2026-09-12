# Natural-feed collection — run 1 status, 2026-09-11/12 (updated after the Commercial Observer resolution)

Cohort: `natural_feed`. Window **2026-08-12 → 2026-09-10** inclusive, holdout cutoff **2026-09-04**,
frozen in `work/phase2/natural-feed/collection-manifest.json` before the first entry was recorded.
The manifest hashes [the collection policy](natural-feed-policy.md), so a later policy edit is
detectable rather than silent.

Collection is hand-driven browsing under the policy — page reads, and for one source the site's own
public API, all from an ordinary browser session. No collector was built: `tools/collection.py`
contains no HTTP client and only normalizes what was observed. The Phase 3 gate stays closed.

## What was collected

**245 evidence records**, zero duplicate article IDs, 189 calibration / 56 holdout.
Records live in ignored `work/phase2/natural-feed/evidence.jsonl`; nothing entered Git.

| Source | In-window records | Note |
|---|---|---|
| aci_news | 109 | Pages 1–8; page 8 crosses the window start. Gated publication: every record is `access_status: unavailable`, `evidence_scope: metadata_only`. |
| commercial_observer_finance | 83 | Resolved by retrieval (see below). Exact timestamps, `datetime` precision. |
| sec_edgar | 12 | Collected against the frozen roster. 43 filings returned across 11 CIKs; 12 in scope. |
| hsbc_am_news | 13 | Mostly house commentary (Investment Weekly/Monthly), one press release. |
| kkr_media | 10 | All regions and strategies. No KKR release falls between 09-04 and 09-10. |
| apollo_press | 4 | |
| bain_capital_news | 3 | Includes one In the News item; originating publisher recorded as With Intelligence. |
| blue_owl_ir | 3 | Carries a Barclays release the corporate index does not. |
| blue_owl_news | 2 | |
| cifc_news | 2 | |
| otf_press | 1 | The only vehicle-level record: $150m private placement, 09-04, holdout. |
| pag_media | 1 | Media center readable; the Phase 1 block did not recur. |
| pretium_press | 1 | 09-10, holdout. |
| guggenheim_investments_news | 1 | |
| basepoint_news | 0 | **Observed zero, not a gap.** Index enumerated in full; latest entry is 2026-07-30. |

36 further entries were seen and excluded as outside the window, with their dates recorded.

## Gaps, all logged rather than worked around

| Source | Reason | Detail |
|---|---|---|
| commercial_observer_finance | `pagination_truncated` | **Resolved by retrieval, not dropped.** 83 in-window records with exact timestamps. Recorded limit: the landing page is not a chronological archive, so the Finance channel was enumerated instead — see below. |
| sec_edgar | `roster_pending` | Roster frozen and tier collected (12 records). Remaining gap is roster-level: pretium, pag and the Bain Capital manager have no verified CIK, so their filings are outside this cohort by construction. |
| neuberger_newsroom | `article_links_unavailable` | The pre-collection check said the listing was empty; **that was wrong** — entries render below the media-contacts block. But the index exposes no per-article link and clicking does not navigate. Two in-window items are known by title and date and remain uncollectable. One of them is independently covered by ACI on 08-19, so the event is not wholly lost. |
| bayview_site | `no_index_published` | No newsroom in public navigation. No route was invented. Bayview items can still arrive through other fixed sources. |
| aci_news | `article_inaccessible` | Contributed 109 records, but from the public index only; readability per article is unestablished. |

## How Commercial Observer was resolved

Instructed to resolve the dates by retrieval rather than drop the source. Two things changed from
the original plan, both recorded rather than absorbed:

**Transport.** The plan was 150–250 individual article page loads. Commercial Observer publishes its
own WordPress REST API, which returns the same posts with exact `published_time` in a handful of
requests. It is more accurate than parsing a rendered date and far gentler on the source, so it was
used instead. No account, no subscription, nothing bypassed. This changes the transport, not the
census boundary.

**Boundary.** The `/finance/` landing page turned out not to be a chronological archive at all:
`/finance/page/N/` returns the same 20 items for every N, so it cannot be paginated across a 30-day
window. The Finance channel category is its chronological equivalent and was enumerated instead.
Of the 20 items on the landing page, **17 are in the Finance channel**; the 3 that are not are
leasing and site-purchase stories carrying a different taxonomy. That difference is recorded here
rather than silently absorbed, because it means "the Finance section" and "the Finance channel" are
not quite the same set, and the cohort follows the channel.

Window filtering uses the publication local date (site timezone −04:00, verified as a constant
four-hour offset between `date` and `date_gmt` on every record). Records carry
`access_status: accessible`; evidence scope stays `metadata_only` until article text is captured
and hashed.

## SEC roster, frozen 2026-09-12

`work/phase2/natural-feed/sec-roster.json`, hashed alongside the collection policy. Frozen before
the first SEC retrieval, as the policy requires.

**11 issuers verified.** Five from SEC's own `company_tickers.json` (Blue Owl `0001823945`, OTF
`0001747777`, KKR `0001404912`, Apollo `0001858681`, Bain Capital Specialty Finance `0001655050`);
six by exact registrant legal name in EDGAR company search (Neuberger Berman Group `0001465109`,
Bayview Asset Management `0001767366`, CIFC Asset Management `0001665568`, BasePoint Group
`0002150855`, Guggenheim Partners Investment Management `0001425852`, HSBC Global Asset Management
(UK) `0001580862`). OTF's CIK independently matches the archive path in Phase 1 evidence S04.

**4 unresolved, recorded as gaps rather than guessed:**

- **Pretium** — no registrant matches the manager name. Only Pretium *fund* entities file, and the
  policy forbids expanding a manager to its funds.
- **PAG** — the only plausible match is Pacific Alliance Group Ltd (Cayman, `0001684210`), reachable
  only by inferring from PAG's historical name. Refused on that basis.
- **Bain Capital manager** — the tracked BDC is covered; the manager/credit entity did not resolve
  to one verified registrant.
- **Blue Owl credit platform** — files through the parent and the tracked vehicle, both covered.

Namesake traps avoided and recorded: EDGAR also holds BasePoint Analytics LLC (CA) and BasePoint
Asset Recovery LLC (CT), unrelated to the watchlist platform. Guggenheim Investments is a brand
spanning several affiliates, so covering GPIM is a stated scope limit, not full coverage.

**Form scope.** Included: 8-K, 10-K, 10-Q, 424B2/B3/B5, N-2, SC 13D and SC 13D/A. Excluded with
reasons: 13F-HR, SC 13G and 13G/A, Form 4, N-PX (position and insider disclosure, not events) and
Form D — the last because private-offering notices are filed by the very fund entities this roster
deliberately excludes, so including it would pull the fund universe in by the back door. Neuberger's
EDGAR output was checked and is dominated by the excluded forms, so a thin SEC yield for pure
managers is expected rather than surprising.

Filing date is the public-availability date and is not the event date; a filing disclosing an
earlier event keeps its own filing date and `event_date` stays null unless the document establishes
one.

### SEC tier result, collected 2026-09-12

43 filings across the 11 CIKs, **12 in scope**, all from five issuers: Blue Owl 3, OTF 4, KKR 2,
Apollo 2, BasePoint 1. Bayview, Neuberger, Guggenheim and HSBC AM returned only N-PX, 13F and 13G
filings — every one excluded by scope. BCSF and CIFC filed nothing in the window.

That is the prediction recorded at freeze time coming true: for pure asset managers EDGAR yields
position and proxy disclosure, not events. The tier's value is concentrated in the issuers and
vehicles, and OTF's 09-04 8-K corroborates the press release already collected from its own
newsroom.

**One amendment, recorded in `sec-roster-amendments.json`.** The frozen scope was written with
EDGAR form codes (`SC 13D`), but EDGAR's company-search table renders the same form as
`SCHEDULE 13D`. Matching the frozen strings literally would have silently dropped BasePoint
Group's 2026-08-18 SCHEDULE 13D — a control-stake filing squarely inside the intended scope. Form
matching now normalizes the two spellings, which corrects how the scope was written down without
widening, narrowing or reinterpreting it. One record affected.

Titles on SEC records are constructed filing descriptors, not headlines: EDGAR filings have no
headline and none was invented.

## Two findings that change the cohort's shape

**The feed is dominated by two publications.** ACI supplies 109 records and Commercial Observer 83,
so 192 of 233 come from the two independent outlets. HSBC AM's house commentary supplies 13 more.
The thirteen watchlist managers together contribute 28. Any natural-feed precision or recall figure
will largely describe those two sections, and that must be stated wherever the number appears.
Commercial Observer is also a commercial-real-estate-finance section, so the cohort now leans
further toward property lending than toward the corporate private credit the watchlist centres on.

**A starter-batch lineage is already inside the window.** Blue Owl's 09-02 Zurich release is the
same canonical URL as a starter-batch article the analyst has already labeled, and ACI's 09-02
piece covers the same event. The two IDs and the link are recorded in
`work/phase2/natural-feed/starter-batch-overlaps.json`. These must be quarantined from blind
re-labeling: the analyst has seen this story, so a fresh label on it is not independent.

## Why no analyst packet was built

The policy requires natural-feed and challenge records to reach the analyst in **one** opaquely
ordered packet so cohort membership stays hidden. No challenge records exist yet, so a packet built
now would be entirely natural feed and would disclose exactly what blinding is meant to prevent.
Packet generation waits for challenge curation.

## Holdout sufficiency

Not yet assessable. Sufficiency counts distinct analyst-**publish-worthy** events, which requires
labels that do not exist. A holdout article count is not an event count, and it is not evidence
that the ≥20 publish-worthy-event minimum will be met. If the holdout falls short, the
policy extends the window forward in whole five-weekday blocks; it never recycles holdout into
calibration and never resizes after model results. 55 holdout records is a larger article base than
before the Commercial Observer resolution, but it is still only an article count.

## Reproduce

```bash
python -m tools.build_natural_feed
```

Rebuilds `evidence.jsonl` and `intake-report.json` from the per-source observation files in
`work/phase2/natural-feed/observations/`. Deterministic: article IDs are UUID5 of the canonical
URL, so re-running produces identical bytes.
