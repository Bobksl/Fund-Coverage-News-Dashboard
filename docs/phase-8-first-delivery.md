# Phase 8 first delivery — repeatable manual updates

2026-09-13. Implements the first delivery of [the Phase 8 plan](phase-8-plan.md). The optional
second delivery (scheduled source checks) was not started, and no scheduler is installed.
Task breakdown and checkpoint evidence: [tasks/phase-8-tasks.md](../tasks/phase-8-tasks.md).

## Dispositions

- phase8_first_delivery = **passed_for_zero_spend_replay_demo**
- spending_approval = **disapproved** (user decision, 2026-09-13). Paid classification and paid
  drafting are recorded below as current limitations of the demo, not pending work.
- new_approved_card_acceptance = **open** (needs paid calls and a real review; not authorized)
- reviewed_demo_ready = passed_for_exactly_one_card (unchanged; the Phase 6 card)
- automated_selection_readiness = **inconclusive_pending_fresh_temporal_validation** (unchanged;
  engineering tests and demo acceptance never promote it)

Scoring weights, config and the frozen Phase 2/6/7 artifacts are unchanged. Everything Phase 8
writes lives under git-ignored `work/phase8/`.

## How an update works

Three things are separate, and the page shows each one on its own:

1. **Source check** — an operator supplies evidence (`intake`). It records a source-check time
   and outcome. It never changes the published edition.
2. **Publication** — only after a named reviewer approved an exact draft revision does
   `publish` build a new isolated edition and swap the served pointer. A failure keeps the last
   good edition.
3. **Browser reload** — **Reload published edition** re-reads the published pointer. It does not
   check sources, collect news or run a model.

## Operator runbook

All commands run from the repository root. None of them call a model unless `classify` is given
explicit spending-cap flags, and that is not authorized.

```bash
python -m tools.manual_update intake path/to/batch.json
```

The batch names `source_id`, `tier` and `publisher`, and lists items with `url`, `title`,
publication date fields, `source_kind`, the permitted captured `text` and `capture_mode`.
Identical items are duplicates, changed text is reported as changed, and each attempt is logged.

```bash
python -m tools.manual_update build-queue --reuse-store work/phase2/live-runs/calib-smoke-deepseek-flash-v3/raw-outputs --ledger phase6=work/phase2/phase6-review/approval-ledger.csv
```

Replays stored classifier responses for byte-identical inputs only, then groups, scores and
explains every candidate. Anything else waits as `awaiting_classification`.

```bash
python -m tools.manual_update draft --claims EVENT_ID=path/to/claims.json --reuse-store work/phase2/phase6-review/raw-outputs
```

Replays a stored bilingual draft for shortlisted events. Without a stored draft for the exact
event, evidence and claims, the event waits and any older draft file is removed.

```bash
python -m tools.manual_update show-draft --event-id EVENT_ID
```

```bash
python -m tools.manual_update review --event-id EVENT_ID --reviewer-id NAME --status approved
```

Run `review` only as the named human who read the `show-draft` output. It binds the decision to
the exact (event_id, revision, content_hash).

```bash
python -m tools.manual_update publish --id NEW_ID --kind reviewed_update --ledger work/phase8/approval-ledger.csv
```

Serve the published site and the separate operator page on localhost only:

```bash
python -m http.server 8644 --bind 127.0.0.1 --directory work/phase8/site
```

```bash
python -m http.server 8646 --bind 127.0.0.1 --directory work/phase8/operator
```

## Acceptance checks

| Plan check | Result | Evidence |
|---|---|---|
| Manual trigger creates a traceable pending candidate; no automatic approval | Pass | `intake` + `build-queue`: logged attempts, candidates `pending_review`; no code path approves (`tests/test_manual_update.py`) |
| Repeated identical input creates no duplicate cards or unnecessary calls | Pass | Resubmitting 10 items gave 10 duplicates, 0 new, same replay run; stored inputs are never re-sent (tests) |
| Edited, rejected or unapproved content cannot enter the edition | Pass | Edited draft, rejected draft and unapproved card each fail to publish and keep the last edition (tests) |
| Source-check failure, exhausted budget and offline execution keep the last good edition with distinct statuses | Pass | Separate verification site showed failed check, cap stop, refused publish, and stale (no successful check within 24 h) |
| UI distinguishes historical sample, no news, stale data and failed refresh | Pass | Distinct notices verified in a real browser |
| One end-to-end manual update in a real browser: source, explanation, EN/ZH, timestamps, reload | Pass, replay only | See below |

**End-to-end run (zero spend).** In a fresh `work/phase8/workspace`, 10 real frozen articles were
supplied as evidence. Nine replayed stored v3 classifier responses and reproduced v3's 8 events
exactly; one stayed `awaiting_classification`. The stored Phase 6 draft replayed from the Phase 8
workspace with the same input and content hashes, so Bob's Phase 6 approval of that exact hash
applied. Publication `manual-2026-09-13-replay` replaced `hist-2026-09-04-phase6`. A page loaded
before the update showed, after **Reload published edition**: the new edition, source check
16:53 HKT with 10 new items, publication 16:53 HKT, article date 2026-09-04, and the EN and ZH card
with its source link. The operator page showed the explanation, draft state and exact-approval
state. The published card is byte-identical to the Phase 6 card: this proves the workflow, not
new coverage.

## Current limitations

- **No paid model calls (budget disapproved).** New evidence that has no stored response stays
  `awaiting_classification`, and a shortlisted event without a stored draft stays
  `awaiting_drafting`. The demo therefore cannot produce a genuinely new card.
- **Only byte-identical inputs replay.** A changed article text, prompt, config, claims or setting
  changes the input hash, and nothing is reused.
- **The paid `classify` path is untested against the live provider.** It is exercised only with an
  injected stand-in. The live provider reports request settings the v3 replay profile does not
  declare, so the command refuses a live call under that profile before any spend record exists.
- **One approved card.** The published demo edition republishes the Phase 6 card and is labelled
  a historical sample, not today's news.
- **Explanations live on the local operator page**, not on the published card. Component reasons
  are untrusted model output; gates, totals and bands are deterministic.
- **Selection quality is not established.** The nine smoke articles were category-selected, not
  representative; precision and recall are unknown.
- **Manual only.** No scheduler, no automatic publication and no fixed update frequency. Stale is
  judged as no successful source check in 24 hours, which also covers an offline host.
- **Single ledger per publish.** Cards approved in different ledgers cannot share one edition yet.
- **Local files.** The workspace is OneDrive-synced; Phase 8 writes retry briefly on transient
  file locks. Both pages are served on 127.0.0.1 only.
