# Natural-feed collection policy — collection decision, 2026-09-11

Status: **Ready for manual Phase 2 collection under the decisions below**, answering the user's
2026-09-11 request to resolve the collection blockers. Collection has not started in this task.
This is a collection decision, not analyst approval of labels or an evaluation pass.
A feed assembled after seeing model results is not a natural feed, so the roster, the
window and the completeness rule are fixed here first and changed only by a recorded amendment.

This governs the natural-feed cohort only. Challenge records are curated separately under
[phase-2-experiment.md](phase-2-experiment.md) and never enter this roster.

## Why this exists before any collecting

The existing 20-article starter batch was hand-picked for calibration. It cannot retroactively
become a census: its prevalence of publish-worthy events reflects how it was chosen, not what the
public feed actually produces. Estimating natural-feed precision and recall needs records captured
under a rule written in advance.

## Fixed roster and collection decisions

Collection in Phase 2 is **manual**. Building collectors is Phase 3 work and stays gated.

| Tier | Source | Basis |
|---|---|---|
| Manager newsrooms | Exact indexes in the table below | Collect the specified index sections, all strategies and regions. Path verification does not certify complete pagination. |
| Regulator / filings | SEC public filing search for the tracked issuers and vehicles | Primary records, and the counterweight to PR-heavy manager pages. Exact query and coverage must be recorded per run. |
| Independent publications | [Alternative Credit Investor — News](https://alternativecreditinvestor.com/category/news/) and [Commercial Observer — Finance](https://commercialobserver.com/finance/) | Enumerate all dated article entries in these two sections and their pagination within the window. No article-level relevance filter. Use public evidence only; retain paywall/access failures. |

### Independent publication scope

Use the two sections above for this cycle. Their public indexes were readable on 2026-09-11;
ACI's index explicitly advertises subscription access, so this is not a claim that all articles
are free. The sections provide alternative-credit and commercial-property-financing supply
without enumerating an entire general-news service. This is a census of a **declared, bounded
source universe**, not a census of all financial news. Section selection is an ex-ante discovery
boundary, not an analyst publish/reject decision.

Only entries in the section's article listing belong to the census: exclude navigation, unrelated
trending widgets and advertisements. Keep sponsored/PR-derived articles if actually listed, with
their originating publisher and content type; an independent outlet's masthead does not make
every item independent reporting. Do not visit dedicated promoted-content or events sections.

Do not purchase subscriptions, create accounts or bypass access controls. Retain public titles,
URLs, dates and access status for gated entries; do not reconstruct missing text from search
snippets. Public primary corroboration may be attached under a consistent evidence-retrieval
rule applied before labeling, with its own provenance. Never present it as the inaccessible
article's text. Report evidence availability and unlabelable records alongside performance;
do not silently drop them or label them editorial rejects.

Reuters is permissible public corroboration when accessible, but not a third census index this
cycle. Business Wire and PR Newswire are distribution/evidence sources, not independent reporting.
Private Equity Wire is not in this cycle's roster (homepage returned 403 in this check).
No paid sources or new discovery providers are required to begin.

### Manager index verification and exact scope

Checked 2026-09-11 using public web page text and official navigation. `readable` means an index
with entries was observed; `partial` means the route is established but enumeration was not
available in the text response. Neither status establishes historical completeness. Record the
actual browser/access result, pagination and retrieval time during collection; cached search
results alone cannot establish a complete census.

| Watchlist entry | Exact index / entry point | Verification and collection scope |
|---|---|---|
| Blue Owl | [Corporate news](https://www.blueowl.com/news) and [IR press releases](https://ir.blueowl.com/Investors/news/default.aspx) | Corporate index readable; IR route verified but live text response omitted entries, while indexed text exposed a year listing. Collect both; retain cross-index discovery provenance without creating two records for the identical canonical article. |
| OTF | [Press releases](https://www.blueowltechnologyfinance.com/news/press-releases) | Readable; followed official investor navigation. Separate vehicle source, not an alias for the parent index. |
| Pretium | [Press releases](https://pretium.com/category/news/press-releases/) | Readable; linked from official News. Use this full archive, not the three-item preview in the parent News page. Media Mentions is outside this cycle's index scope. |
| KKR | [Media Center](https://media.kkr.com/) | Readable; Press Releases tab, All Releases, all dates/regions in window; exhaust Load More. Do not limit to Credit. KKR in the News tab is outside scope. |
| PAG | [Media center](https://www.pag.com/en/media-center/) | Readable; followed official homepage navigation. Include all English news entries, including awards and APAC transactions. Phase 1 blockage is historical, not an exclusion. |
| Bayview | [Official homepage](https://bayview.com/) | Homepage readable but no newsroom/index found in public navigation or targeted search. `needs_review: true` for newsroom path; no invented /news route. Manager remains monitored, but direct-newsroom enumeration is unavailable this cycle. Log a source-coverage gap, not zero news. Stories arriving through the fixed other sources remain eligible. |
| CIFC | [Perspectives / News](https://cifc.com/news) | Readable dated listing. Collect all listed categories, including commentary and appearances. |
| BasePoint | [Homepage — Latest News and Insights](https://basepointgroup.com/) | Readable dated news list. This homepage section is the verified entry point; no separate archive assumed. Follow listed article links; flag the limited history if no pagination covers the requested window. |
| NB / Neuberger | [Newsroom](https://www.nb.com/who-we-are/newsroom) | Route and heading verified; response said No Results Found despite known individual releases. `partial`: use ordinary browser public-region controls to enumerate, recording edition. If still empty, log an enumeration gap rather than asserting no releases. |
| Apollo | [Press Releases](https://www.apollo.com/insights-news/pressreleases) | Readable dated listing; all releases, no keyword/strategy filter. Exhaust year/pagination controls. |
| Bain Capital | [News](https://www.baincapital.com/news) | Readable; include Press Releases and In the News entries in the archive, all businesses/regions. Preserve originating-publisher distinctions for linked coverage. |
| Guggenheim | [Investments news](https://www.guggenheiminvestments.com/firm/news/) | Readable destination, reached from [Partners news](https://www.guggenheimpartners.com/firm/news). Partners page is a routing page, not an archive. Collect Investments news; Securities newsroom is outside this cycle's source scope. Securities-only coverage found elsewhere is still recorded and judged by the engine. |
| HSBC AM | [UK intermediary News and Insights](https://www.assetmanagement.hsbc.co.uk/en/intermediary/news-and-insights) | Readable dated listing with categories. Collect all listed articles, press releases and videos, no subject filter. Do not add generic HSBC Group banking news or duplicate country editions. |

If any index is blocked, make one ordinary-browser attempt and one later retry, then record the
gap and continue the remaining roster. No bypass, unrecorded replacement or open-web search
top-up. An unavailable index does not block all collection; material gaps do constrain the
eventual coverage/readiness claim. An alternate source/index requires a dated amendment before
its collection and cannot be silently blended into an already frozen cohort.

### HSBC AM and geography

Record the HSBC site edition as UK. **Do not assign event geography from the domain, publisher
headquarters, dateline or website language.** Assign economic geography from the affected
borrower/assets, investment mandate or market/policy jurisdiction. US lending described on
the UK site is US; European lending is Europe; a global strategy is global/mixed unless evidence
supports a narrower attribution; unresolved geography is unknown. Apply the same rule to all
sources. Keep publisher/site geography separate from event geography.

No geographic balancing is applied during collection or to the intrinsic score. The approximately
20% Europe preference is a later rolling selection constraint; a UK page does not fill that quota.

## Window

- 30 consecutive calendar days, ending on the last completed news day before collection begins.
- The **latest five completed news days are reserved for the holdout**; earlier days are
  calibration. The cutoff date is recorded in the split manifest before any inference.
- If the natural-feed **holdout** falls short of 20 distinct analyst-publish-worthy events, the window is extended
  **forward in time under this recorded rule**, never topped up with challenge positives and never
  resized after model results are seen.

Before collecting, write actual inclusive dates and a fixed calibration/holdout cutoff into the
run manifest. For a start on 2026-09-11 using completed calendar dates through 2026-09-10, the
30-day window is 2026-08-12 through 2026-09-10; the final five weekdays are September 4, 7, 8,
9 and 10. Here news days mean weekdays, including market holidays because news can still appear.
The holdout starts September 4 and also contains intervening weekend items. If collection begins
later, calculate dates from that actual start before collecting. Forward extensions append whole
days to holdout; do not move its starting cutoff or recycle holdout into calibration. Custodian
checks sufficiency after each complete five-weekday extension, without model results. Preserve
event-lineage separation and quarantine overlaps with the already reviewed starter batch;
different analyst event IDs do not by themselves establish different lineages.

## Completeness rule

Record every item the roster returns inside the window, before any editorial judgement:

- routine announcements, awards, marketing and obviously irrelevant items;
- duplicates and syndicated copies, with provenance preserved;
- corrections and updates, linked to what they supersede;
- items whose evidence is inaccessible or snippet-only, marked `unavailable` or `partial` with
  `evidence_scope` recorded honestly;
- pagination limits and source outages, logged as gaps rather than silently truncated.

No relevance, sector or watchlist filter is applied at collection time. Filtering is what the
pipeline is being measured on; applying it during collection would measure the analyst instead.

Undated items are recorded with `published_date_precision` of `month` or `unknown` and are excluded
from the headline split, as the tooling already enforces. No date is guessed. One Bain item was
handled this way during the starter batch and that precedent stands.

## What gets recorded per item

The evidence contract in [decision-record.md](decision-record.md), enforced by
`tools/records.py`: stable article ID, original and canonical URL, publisher and originating
publisher, discovery method, source kind, publication time with its true precision, event date,
first-seen and retrieval times, access status, evidence scope, and the hash of whatever text was
actually examined. Store permitted text or excerpts privately under ignored `work/`. No article
corpus enters Git.

## Cohort separation

Natural-feed records carry no selection rationale — `tools/corpus.py` refuses to register one.
Challenge records must declare a coverage category. Both cohorts are combined into a single
opaquely ordered analyst packet so the reviewer cannot tell which is which, and both are reported
separately in every result. An article discovered naturally stays natural; a matching challenge
record is linked, not counted twice.

## Run setup

```bash
python -m tools.corpus packet work/phase2/natural-feed/evidence.jsonl work/phase2/packets/nf-001
python -m tools.corpus split work/phase2/natural-feed/evidence.jsonl <FROZEN_CUTOFF_DATE> work/phase2/split-001.json --gold-groups work/phase2/evaluator/gold-groups.json
```

The split command reads gold groups and is a custodian command; its output to the pipeline is
article IDs and a partition name only.

Replace the cutoff placeholder from the manifest; it is not a literal runnable shell argument.
For SEC, freeze the exact issuer/vehicle CIK list and form/query scope before its first retrieval;
this is collection bookkeeping, not another investment-team decision. Use only independently
verified issuer identities and log unresolved ones as coverage gaps. Collection may begin with
the fixed manager/publication indexes while that SEC roster is recorded. No CIK inferred from a
similar name and no wildcard expansion to every fund of a manager.

## What this policy does not do

It does not authorize collectors, scheduling, or any Phase 3 work. It does not estimate how many
publish-worthy events the feed will yield — that is the measurement. A thin result is an honest
finding about public supply, and the response is to narrow the demo's claim, not to add weak
stories or paid data.
