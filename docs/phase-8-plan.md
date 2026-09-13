# Phase 8 — repeatable manual news updates

Status (2026-09-13): first delivery **complete for a zero-spend replay demo**; see
[Phase 8 first delivery](phase-8-first-delivery.md) for the runbook, acceptance evidence and
limitations. Spending approval was **disapproved** by the user: paid classification, paid drafting
and a genuinely new approved card are current limitations of the demo, not pending work. The
optional second delivery (scheduled source checks) has not started, and no scheduler is installed.
automated_selection_readiness remains inconclusive_pending_fresh_temporal_validation.

Follows the user-directed [Phase 7 demo closeout](phase-7-closeout.md). The immediate goal is a
useful analyst-operated demonstration with a clear update story, not automated readiness. The plan
text below is the original scope and is kept as written.

## First delivery: manual update workflow

1. Show source-check time, last successful publication time, article dates and
   update mode independently. Never show a page-load time as news freshness.
2. Add an operator action to process explicitly supplied source evidence into a
   pending review queue. Reuse existing collection, classification, grouping,
   drafting and approval components. Keep credentials and model calls off the page.
   New paid calls need a separately approved bounded budget.
3. Show why each candidate was shortlisted, suppressed or sent for review, with
   source references and rule/score explanations. Show the existing approved card
   as historical. Additional real cards require actual review, not demo labels
   that imitate approval.
4. Publish only exact approved revisions through the existing hash gate. Build a
   new isolated snapshot and replace the served edition only after success.
   On failure retain the last successful edition and show the failure/stale state.
5. Provide a browser **Reload published edition** action. It reloads approved data
   only; it neither collects news nor incurs model spend. Make that distinction
   explicit in its label and help text.

## Optional second delivery: scheduled source checks

Proposed schedule: 08:00 and 16:00 Asia/Hong_Kong, weekdays, with manual checks
available. Confirm source access, operator availability and budget before enabling.
The execution host must be running; missed/offline checks must be visible rather
than displayed as successful. No scheduler is installed by this plan.

Each source check captures permitted new evidence, deduplicates exact inputs and
queues candidates. Reuse exact stored model responses where valid. Avoid overlapping
runs with a lock and retain an attempt log. Each paid request uses a shared cap;
cap exhaustion stops processing and requests a new explicit decision.

Human approval, not the clock, triggers publication eligibility. A successful
export changes the published snapshot. Browser reload retrieves that snapshot;
optional polling for a changed publication version can follow later. No fixed
publication frequency is promised while review remains human-operated.

## Acceptance checks

- Manual trigger creates a traceable pending candidate; no automatic approval.
- Repeated identical input does not create duplicate cards or unnecessary calls.
- Edited/rejected/unapproved content cannot enter the reviewed edition.
- Source-check failure, exhausted budget and offline execution preserve the last
  good edition and report distinct statuses.
- UI distinguishes historical sample, no news, stale data and failed refresh.
- One end-to-end manual update is verified in a real browser, including source,
  explanation, EN/ZH, timestamps and subsequent reload.

Keep scoring weights and frozen Phase 7 artifacts unchanged. No full calibration,
fresh temporal benchmark, database build or automatic publication is required for
this delivery. Those remain separately scoped future work. Engineering tests and
demo acceptance never promote automated_selection_readiness to PASS.
