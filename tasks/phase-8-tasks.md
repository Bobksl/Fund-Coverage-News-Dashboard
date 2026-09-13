# Phase 8 first delivery — task breakdown

Spec: [docs/phase-8-plan.md](../docs/phase-8-plan.md). Second delivery (scheduled checks) is out of scope.

## Decisions (user, 2026-09-13)

- New supplied evidence with no exact stored model response is queued as
  `awaiting_classification`. Stored responses are reused at zero spend. Any new paid call
  requires an explicit cap through the existing `SpendLedger` flags. No fallback to the
  Phase 2 deterministic baseline.
- End-to-end browser acceptance for this delivery uses replay: the smoke articles re-supplied
  as evidence (stored responses, zero spend) plus the existing approved Blue Owl revision.
  The check for a genuinely new approved card stays open until a budget and a real review exist.

## Assumptions

- The operator action is a CLI. No credentials, model calls or approval controls on any page.
- Phase 8 state lives under git-ignored `work/phase8/`. Phase 6 artifacts are read, never modified.
- The published page shows approved cards only. Candidate explanations live on a separate
  local operator page and never inside a published edition.

## Slices

- [x] T1 Publication manifest (`publication.json`) and independent freshness display:
      source-check time/status, last successful publication time, article dates, update mode.
- [x] T6 Isolated edition build `editions/<publication_id>/` plus atomic pointer swap; failure keeps
      the last good edition and records a failed attempt.
- [x] T7 **Reload published edition** button (re-fetches the pointer; no collection, no model spend).
- [x] Checkpoint 1 (2026-09-13): publish mechanics verified with the existing approved card.
      `tools/publication.py` + `tests/test_publication.py` (10 tests; suite 402 passed). Served
      `work/phase8/site` (edition `hist-2026-09-04-phase6`, zero spend) in a real browser: EN/ZH card,
      source link, article date, historical + stale notices, unchanged reload. Separate
      `work/phase8/verify-site` showed distinct states for no new items, refused duplicate publish,
      budget stop, failed source check, edition swap on reload, and failed reload keeping the
      prior edition. Candidate explanations (plan item 3) are not yet shown; that is T3/T4.
- [x] T2 Operator intake CLI: supplied observations + text → evidence records; exact-input dedup;
      attempt log.
- [x] T3 Queue build: stored-response reuse, `awaiting_classification`, grouping/scoring, per-candidate
      explanation; distinct statuses for source failure and budget stop.
- [x] T4 Local operator queue page (shortlisted / suppressed / review / awaiting, with reasons).
- [x] Checkpoint 2 (2026-09-13): queue mechanics verified. `tools/manual_update.py`
      (`intake`, `classify`, `build-queue`), `site/operator/`, `tests/test_manual_update.py`
      (16 tests; suite 418 passed). Replay run in `work/phase8/verify-workspace`: 9 frozen smoke
      articles + 1 real frozen article with no stored response were supplied as evidence; 9 replayed
      from calib-smoke-deepseek-flash-v3 at zero spend, 1 `awaiting_classification`. The 8 queue events
      have identical ids, recommendations, scores, levels and gates to v3. Identical resubmission:
      10 duplicates, 0 new, same run reused. Operator page (`work/phase8/operator`, port 8646) verified
      in a browser: sections and counts, reasons, score-only bands, gates/components table, sources,
      Phase 6 ledger history labelled as not an approval, awaiting reason, queue reload, no console
      errors. Fixed during verification: a review item's retained `shortlisted` code claimed every
      gate passed.
- Known limitation: the paid `classify` path is exercised only with an injected provider in tests.
  `DeepSeekProvider` reports request settings (thinking, reasoning effort, top_p, system prompt hash,
  and others) that the v3 replay profile does not declare, so the CLI refuses a live call under the
  default profile before creating any spend ledger. A live run needs its own declared profile, and
  its stored responses will then replay only under that profile, not beside v3 replays in one queue.
  Decide this together with any budget approval.
- [ ] T5 Draft (stored/capped only) and ledger review for shortlisted events.
- [ ] T8 End-to-end replay verification in a real browser; docs.
- Checkpoint 3: delivery acceptance; new-card check recorded as open.

Unchanged: scoring weights, frozen Phase 7 artifacts, `automated_selection_readiness`.
