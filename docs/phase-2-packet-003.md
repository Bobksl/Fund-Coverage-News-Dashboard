# Analyst packet 003 — combined cohorts, 2026-09-12

**274 articles, all to be labeled.** Sampling was considered and declined. The packet is
`work/phase2/analyst-review-003/`, ignored by Git.

## What to do

1. Open `articles.md`. It lists each article's opaque ID, title, publisher, date and original link.
2. Read the original source before judging. Do not label from the title.
3. Fill the blank columns in `analyst-labels.csv`, one row per article. The columns and their
   meanings are unchanged from the starter batch: see [analyst labeling](analyst-labeling.md).

Nothing about the format is new. The only differences from the starter batch are scale and that
this packet mixes two cohorts you are not told apart.

## What this packet deliberately does not tell you

It carries article ID, title, publisher, date and link. It does not carry cohort membership,
challenge category, selection rationale, any model output or any suggested grouping. 91 of these
records were curated as deliberate probes — namesakes, look-alike headlines, routine activity
dressed as news — and which ones they are stays hidden. Knowing would stop your label being an
independent judgement, which is the only thing that makes the evaluation worth running.

**For whoever briefs the reviewer:** do not mention the natural-feed collection window
(2026-08-12 to 2026-09-10). Every independent challenge record falls outside it, so a reviewer who
knows the window could identify them from their dates.

## Two practical things before you start

**Roughly 40% of the packet is behind a subscription.** 109 records come from Alternative Credit
Investor, whose articles are gated. Where you cannot read the source, set `evidence_access` to
`inaccessible` or `partial` and use `review` for the decision. Do not infer a decision from the
headline, and do not reconstruct the article from search snippets. An unlabelable record is a
finding about evidence availability, and it will be reported as one.

**Budget the time honestly.** At a couple of minutes per article including opening the source,
274 records is the better part of a working day. Much of it is fast — recurring house commentary
and routine announcements resolve quickly — but the identity and clustering cases deserve real
attention, and those are exactly the ones the experiment is built to measure.

## Event grouping matters more than usual here

Several events in this packet appear more than once: the same announcement issued by two managers,
a press release and the filing that discloses it, an issuer release and independent coverage of it.
Reuse one `event_group_id` across every article describing the same event, and judge publication at
event level so a duplicate source does not become an unrelated negative. Distinct deals that share
a lender and a headline shape are **different** events and need different IDs.

## What was left out, and why

| Article | Reason |
|---|---|
| Blue Owl Zurich office (blueowl.com) | Quarantined. It is the identical canonical article you already labeled in the starter batch, so a fresh label would not be independent. Its existing label carries over; the link between the two IDs is recorded in `work/phase2/natural-feed/starter-batch-overlaps.json`. |
| Bain Capital Vitabiotics | No established publication date. Phase 1 recorded conflicting dates and the index card shows none, so it is excluded from the dated packet rather than given a guessed date. It stays in the operational slice and is reported separately. |

Two of the 91 challenge probes are therefore not labelable in this packet. Both are recorded rather
than quietly dropped.

## What happens after you return the file

1. The submitted bytes are copied and hashed unchanged, then audited for structure, coverage and
   enum validity. Your decisions are never edited to fit.
2. Labels and evidence are frozen together, with the split manifest, before any inference runs.
3. One frozen run, then evaluation joins predictions to your labels — never the other way round.
4. Natural-feed and challenge results are reported separately, with the overlap between them
   disclosed, and a written pass, fail or inconclusive disposition follows.

Only that disposition opens Phase 3.
