# Natural-feed collection — run 1 status, 2026-09-11/12

Cohort: `natural_feed`. Window **2026-08-12 → 2026-09-10** inclusive, holdout cutoff **2026-09-04**,
frozen in `work/phase2/natural-feed/collection-manifest.json` before the first entry was recorded.
The manifest hashes [the collection policy](natural-feed-policy.md), so a later policy edit is
detectable rather than silent.

Collection is manual browsing under the policy. No collector was built: `tools/collection.py`
contains no HTTP client and only normalizes what a person observed. The Phase 3 gate stays closed.

## What was collected

**150 evidence records**, zero duplicate article IDs, 115 calibration / 35 holdout.
Records live in ignored `work/phase2/natural-feed/evidence.jsonl`; nothing entered Git.

| Source | In-window records | Note |
|---|---|---|
| aci_news | 109 | Pages 1–8; page 8 crosses the window start. Gated publication: every record is `access_status: unavailable`, `evidence_scope: metadata_only`. |
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

30 further entries were seen and excluded as outside the window, with their dates recorded.

## Gaps, all logged rather than worked around

| Source | Reason | Detail |
|---|---|---|
| commercial_observer_finance | `index_dates_unavailable` | **Blocking decision.** The Finance index publishes no per-entry date, and article URLs carry year/month only, so the window cannot be applied at index level. Article pages *do* carry exact `published_time`. Resolving the source needs roughly 150–250 article retrievals, or a dated roster amendment dropping it this cycle. Nothing was recorded and no date was guessed. |
| sec_edgar | `roster_pending` | CIK list and form scope not yet frozen, so no retrieval was made. No CIK inferred from a similar name. |
| neuberger_newsroom | `article_links_unavailable` | The pre-collection check said the listing was empty; **that was wrong** — entries render below the media-contacts block. But the index exposes no per-article link and clicking does not navigate. Two in-window items are known by title and date and remain uncollectable. One of them is independently covered by ACI on 08-19, so the event is not wholly lost. |
| bayview_site | `no_index_published` | No newsroom in public navigation. No route was invented. Bayview items can still arrive through other fixed sources. |
| aci_news | `article_inaccessible` | Contributed 109 records, but from the public index only; readability per article is unestablished. |

## Two findings that change the cohort's shape

**The feed is dominated by one publication.** ACI supplies 109 of 150 records, and HSBC AM's house
commentary supplies 13 more. The thirteen watchlist managers together contribute 28. Any
natural-feed precision or recall figure will largely describe ACI's news section, and that must be
stated wherever the number appears.

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
labels that do not exist. 35 holdout records is an article count, not an event count, and it is not
evidence that the ≥20 publish-worthy-event minimum will be met. If the holdout falls short, the
policy extends the window forward in whole five-weekday blocks; it never recycles holdout into
calibration and never resizes after model results.

## Reproduce

```bash
python -m tools.build_natural_feed
```

Rebuilds `evidence.jsonl` and `intake-report.json` from the per-source observation files in
`work/phase2/natural-feed/observations/`. Deterministic: article IDs are UUID5 of the canonical
URL, so re-running produces identical bytes.
