# Natural-feed collection policy — proposal, 2026-09-11

Status: **draft for analyst approval. Collection has not started and must not start before this is
approved.** A feed assembled after seeing model results is not a natural feed, so the roster, the
window and the completeness rule are fixed here first and changed only by a recorded amendment.

This governs the natural-feed cohort only. Challenge records are curated separately under
[phase-2-experiment.md](phase-2-experiment.md) and never enter this roster.

## Why this exists before any collecting

The existing 20-article starter batch was hand-picked for calibration. It cannot retroactively
become a census: its prevalence of publish-worthy events reflects how it was chosen, not what the
public feed actually produces. Estimating natural-feed precision and recall needs records captured
under a rule written in advance.

## Proposed roster

Collection in Phase 2 is **manual**. Building collectors is Phase 3 work and stays gated.

| Tier | Source | Basis |
|---|---|---|
| Manager newsrooms | The official domains already verified for the 13 watchlist entries in [entity-research.md](entity-research.md) and [config/sources.json](../config/sources.json) | Verified 2026-09-10 as entity-mapping evidence. The exact newsroom/press-index path on each domain is **not yet verified** and must be confirmed and recorded before collection. |
| Regulator / filings | SEC public filing search for the tracked issuers and vehicles | Primary records, and the counterweight to PR-heavy manager pages. Exact query and coverage must be recorded per run. |
| Independent public reporting | To be named by the analyst | Public sources only. No Bloomberg, 9fin, LCD, Octus or any paid data. |

Open items the analyst must settle before approval:

1. Which independent public outlets are in scope, and whether any are excluded on access terms.
2. Whether PAG is collected at all this cycle: its current site access was blocked during Phase 1
   research and the limitation is unresolved.
3. Whether HSBC AM's UK-hosted pages count as US-emphasis supply or as European supply.

## Window

- 30 consecutive calendar days, ending on the last completed news day before collection begins.
- The **latest five completed news days are reserved for the holdout**; earlier days are
  calibration. The cutoff date is recorded in the split manifest before any inference.
- If natural-feed publish-worthy supply falls short of 20 distinct events, the window is extended
  **forward in time under this recorded rule**, never topped up with challenge positives and never
  resized after model results are seen.

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

## How to run it once approved

```bash
python -m tools.corpus packet work/phase2/natural-feed/evidence.jsonl work/phase2/packets/nf-001
python -m tools.corpus split work/phase2/natural-feed/evidence.jsonl 2026-10-06 work/phase2/split-001.json --gold-groups work/phase2/evaluator/gold-groups.json
```

The split command reads gold groups and is a custodian command; its output to the pipeline is
article IDs and a partition name only.

## What this policy does not do

It does not authorize collectors, scheduling, or any Phase 3 work. It does not estimate how many
publish-worthy events the feed will yield — that is the measurement. A thin result is an honest
finding about public supply, and the response is to narrow the demo's claim, not to add weak
stories or paid data.
