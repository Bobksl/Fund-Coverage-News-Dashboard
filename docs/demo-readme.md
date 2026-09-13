# Demo — how to run it, and what it honestly shows

> Current route (2026-09-13): use the [manager demo guide](manager-demo-guide.md)
> for the existing human-reviewed bilingual card and the explanation of manual
> updates. [Phase 7 is closed for demo scope](phase-7-closeout.md), and
> [Phase 8 plans repeatable updates](phase-8-plan.md). The Phase 4 account below
> is historical and describes a separate baseline demo; its claims that no live
> model or human review has occurred are superseded by Phase 5/6 completion.


Updated 2026-09-12 for Phase 4. No model provider has produced a live classification or drafting
run yet (see `docs/phase-4-plan.md` for what is authorized and missing), so this demo still shows
**mechanics, not performance.** Every card on screen is a real deterministic-baseline shortlist
candidate from the frozen corpus — not published news, not analyst-approved, and not evidence
that the system works. The measured baseline result is a **FAIL** against the agreed bars
(natural-feed holdout: 75% precision vs. a 90% bar, 14.3% recall vs. an 85% bar, 1 of 2
must-not-miss). See `docs/phase-2-disposition.md` for the full picture.

## Run it

```bash
python -m tools.export_demo
```

This regenerates `work/phase2/demo-feed/` (via `tools.build_demo_feed`, ignored by git) from the
already-evaluated `work/phase2/run-001` predictions and the frozen evidence, then copies only
`site/index.html`, `site/app.js` and that feed's JSON into an isolated `work/demo-export/`
directory (also ignored by git). **Serving the repository root is no longer the documented path**
— it would expose `work/`, evaluator files and this repo's `.git`. Serve only the exported
directory, bound to localhost:

```bash
python -m http.server 8642 --bind 127.0.0.1 --directory work/demo-export
```

Open `http://127.0.0.1:8642/index.html`. Pass `--no-rebuild` to `tools.export_demo` to export the
existing feed without regenerating it.

## What it demonstrates

- **Collected corpus → contract-valid decisions**: cards are built from real
  `tools.runner` output (`work/phase2/run-001/*/predictions.jsonl`), not fabricated data.
- **Day-specific editions, not a partition-wide top-10**: the daily capacity target (6-10, no
  forced minimum) is applied per Asia/Hong_Kong calendar day
  (`tools.scoring.select_editions_by_day`), so one busy day cannot exhaust the capacity a later
  quiet day would otherwise get. The independent challenge partition never appears in this
  calendar — see `work/demo-export/data/challenge-diagnostic.json` for those probe-only
  candidates, kept visibly separate.
- **Date navigation, honest empty/today/error states**: the page opens on today's actual
  Asia/Hong_Kong date; if no edition exists for today (true throughout this historical corpus,
  which ends before "today"), it says so explicitly and offers an explicit "Jump to latest
  historical edition" shortcut rather than silently substituting an older day. Prev/Next/date
  dropdown all stay in sync, and a slow or out-of-order fetch can never overwrite what is
  currently on screen (each render carries a request token).
- **Safe rendering of untrusted evidence text**: headlines, summaries and source titles are set
  via `textContent`/DOM nodes, never `innerHTML`; source links are allowlisted to `http`/`https`
  before becoming a real anchor, so a hostile or malformed title/URL in captured evidence renders
  as inert text instead of executing or linking anywhere unsafe.
- **Bilingual card mechanics, honestly incomplete**: `tools/drafting.py` produces the EN/ZH card
  with grounding and parity checks, but it also requires an injected model provider. Since none
  is configured, every card shows its English fields (built directly from decision data: parties,
  event type, eligibility reason) and a Chinese block that states plainly it was never generated,
  rather than a bilingual card fabricated to look finished. The EN/ZH toggle in the UI is wired
  and falls back to this disclosure when no Chinese content exists.
- **Analyst review boundary preserved**: every card's status is
  `baseline_shortlist_pending_review`. Nothing in this repo sets `publication.status` to
  `approved` or `published` — the data contract in `docs/decision-record.md` reserves that for a
  recorded human review, which never happened here. `tools/approval_ledger.py` is the minimal
  local CSV mechanism for recording that review when one does happen, tied to the exact
  event/revision/content hash so a later edit invalidates a prior approval.

## What it does not demonstrate

- Selection quality. The baseline's recall floor (14.3%) means most of what an analyst would
  actually publish is missing from this feed — see "Why recall collapsed" in
  `docs/phase-2-disposition.md`.
- The structured LLM classifier or the real bilingual drafter. Both are built and unit-tested,
  and the classifier prompt now carries the full manager ontology and scoring definitions (Phase
  4 finding 1), but neither has run against real evidence. Running them needs a provider/model
  authorization and credential, tracked in `docs/phase-4-plan.md` slice 4B.

## Loose ends resolved or recorded this pass

1. **Vitabiotics date.** Not applied. The record (`article_id`
   `e0f8d0fc-e619-5649-85cb-950a8c028ce9`) sits inside the hashed, frozen evidence file
   `work/phase2/freeze-001/evidence.jsonl` that the Phase 2 FAIL disposition was measured
   against. Editing it now would silently change the input behind an already-reported result.
   The date ("London – July 24, 2026", readable in the article body) stays a decision for the
   next freeze, not a same-freeze cleanup.
2. **BasePoint Asset Recovery rationale.** Corrected. `work/phase2/challenge/challenge-registry.jsonl`
   is evaluator-only metadata outside the frozen hash set (`freeze-record.json` only hashes
   `evidence.jsonl`, the labels file and the split manifest), so the overclaim was fixed in place:
   the record no longer calls the Connecticut filer "unrelated" and now states the unverified
   BasePoint Capital LLC / Neuberger officer connection the probe is actually testing.
3. **PAG's Cordina article.** No action needed — already correctly recorded as the one
   `metadata_only` record out of 276 in `docs/phase-2-collection-status.md`.
