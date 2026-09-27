# Analyst review guide and ranking handback — 27 September 2026

Use this guide for the current 249-card archive. The page shows 128 events: 9 Important, 106 Useful and 13 Needs review. The 32 excluded events remain in the event index for audit and identity continuity.

## What the badge means

“Auto-selected · not yet reviewed” is read from the **display card's original** `review_status`. It does not say whether the whole event's grouping, relevance or priority has since been checked. A card can still show that badge after a source-backed event review. The priority label is a separate assessment; “Needs review” means there is insufficient validated evidence for a confirmed class. Do not infer either approval or lack of approval of an entire event from the badge alone.

## Review one event

1. On **News**, choose a date or **All dates**. Use Manager and Sub-sector to narrow the list. Open **Read original** and, if shown, expand **Sources (n)** and inspect each source separately. Use the headline, date and publisher to identify the event in your notes; the website does not currently expose event IDs.
2. Establish the underlying **subject, action/object and period** from the source itself. Record the source's publication date separately from the page's archive date. A stale republication is not a new event. A digest with several unrelated items is not one event.
3. Compare suspected duplicates. Mark **same event** only if the subject, action and period agree. Mark **update** only for a genuinely new material development with evidence; repeat coverage or a reaction stays coverage/reaction and does not move the event's material-update time. Mark related background, methods explainers and other actions as **related**, not members. When uncertain, keep events separate and flag the question.
4. Decide **include / exclude / unresolved** for coverage relevance. If included, record the proposed class (Urgent, Important, Useful, Needs review) and why it matters to a tracked manager, vehicle or sector. For a confirmed class, identify short source passages that support the severity, linkage, any current adverse state or resolution, and any deadline. A headline, search snippet or inaccessible/paywalled page alone is not enough to confirm priority. Do not bypass a paywall or claim an unread article omits something.
5. Return the template below to the maintainer. An analyst decision is a proposal until the maintainer checks the source, freezes the exact card IDs and hashes, applies the reviewed overlay or hash-bound backfill, regenerates `events.json`, and verifies source preservation and ranking. Do not edit the public day files or paste article bodies into `public/`.

```text
Display headline / archive date:
Publisher and original URL:
Source publication date and where it appears:
Subject + action/object + period:
Other headline(s) to compare:
Relationship: same event / material update / related / separate / uncertain
Why (including any conflicting subject, action, period or figure):
Coverage: include / exclude / unresolved; reason:
Priority: Urgent / Important / Useful / Needs review; reason:
Evidence: short exact supporting passage(s), source URL, section or location:
Uncertainty or access limit:
Analyst name and review date:
```

For an event with several sources, state which source supports the proposed priority. A primary-source label requires the maintainer to verify the issuer, regulator or filing domain independently; it cannot be granted by a model or by a quoted claim. Keep any working excerpts in the private/ignored review workspace. The public projection should contain only bounded summaries and evidence metadata.

## How Priority sorts events now

The default **Sort: Priority** uses the pipeline's saved ordinal rank. It compares these fields **in order**, stopping at the first difference:

1. Class: Urgent, Important, Useful, Needs review.
2. Severity: critical, substantial, bounded, unknown.
3. Routine: non-routine before routine. Routine demotion is honoured only for verified primary sources.
4. Time sensitivity: deadline within 48 hours, within 7 days, then monitor.
5. Linkage: direct tracked exposure, sector, indirect, unknown.
6. Evidence strength: verified primary, reported, unknown.
7. Newer **last material update** first, then event ID for a deterministic tie.

Thus, among Useful events, a bounded direct event precedes a bounded sector event when earlier fields tie. A verified primary item may precede a newer reported item when all earlier fields tie. Within Needs review, the unknown evidence fields usually tie, so the order is largely the material-time proxy. A “Potential urgent” flag is a review cue, not a confirmed class or an extra sort tier. The **Sort: Newest** control uses time instead. Date views have ranks assessed at that day's end; All dates uses the export's global ranks. Filtering does not rescore events.

**Limitation:** this is a consistent triage order, not a calibrated estimate of loss, fund exposure or investment importance. The coarse fields create large ties among the 106 Useful events, and the first differing field can place an older, directly linked/primary item ahead of a newer reported sector item. Manual review of relative order has not been demonstrated by the code or labels alone. Do not describe rank 10 as quantitatively more important than rank 11.

## Action plan for the 23:59 HKT deadline

1. **Today:** share this guide with the analyst. Triage the 13 Needs review events first for inaccessible evidence or potential urgent risk. Record unresolved items as unresolved; do not promote on a headline or search summary.
2. **If analyst time remains:** compare the 9 Important events and a bounded sample of Useful pairs: top versus bottom, direct versus sector, primary versus reported, and older versus newer. For each disputed pair, write the source-backed reason and whether a field label is wrong or the ranking rule itself is unsuitable. Keep the pairwise decisions outside `public/` until checked.
3. **Before publication:** fix a demonstrably wrong field or grouping only with source evidence, hash-bound review and regression checks. Otherwise keep the current deterministic order and disclose the limitation above. A new ranking formula needs a version bump and an analyst-checked replay; a few disputed examples are not enough to silently retune it tonight.

A public **group/approve** button is a separate project: this static GitHub Pages site has no authenticated write path or review audit trail. An on-page button must not silently alter grouping or priority. A later version could prepare a prefilled review draft for an authenticated maintainer to validate and commit, while preserving the source and hash checks.
