# Demo — how to run it, and what it honestly shows

No model provider was available before the deadline (`docs/phase-2-disposition.md`), so this
demo shows Step 2's narrowed claim: **mechanics, not performance.** Every card on screen is a
real deterministic-baseline shortlist candidate from the frozen corpus — not published news, not
analyst-approved, and not evidence that the system works. The measured baseline result is a
**FAIL** against the agreed bars (natural-feed holdout: 75% precision vs. a 90% bar, 14.3% recall
vs. an 85% bar, 1 of 2 must-not-miss). See `docs/phase-2-disposition.md` for the full picture.

## Run it

```bash
python -m tools.build_demo_feed
```

Regenerates `work/phase2/demo-feed/` (ignored by git) from the already-evaluated
`work/phase2/run-001` predictions and the frozen evidence. Then serve the repo root over HTTP —
opening `site/index.html` directly will fail on the `fetch()` calls under `file://`:

```bash
python -m http.server 8642
```

Open `http://localhost:8642/site/`.

## What it demonstrates

- **Collected corpus → contract-valid decisions**: cards are built from real
  `tools.runner` output (`work/phase2/run-001/*/predictions.jsonl`), not fabricated data.
- **Date navigation, empty and stale states**: the calendar spans the full collection window
  (2026-08-12 → 2026-09-10, extended backward for two older independent challenge probes);
  most days are legitimately empty — 22 shortlisted events out of 274 decisions is the real
  shape of the baseline's output, not a display bug.
- **Bilingual card mechanics, honestly incomplete**: `tools/drafting.py` produces the EN/ZH card
  with grounding and parity checks, but it also requires an injected model provider. Since none
  is configured, every card shows its English fields (built directly from decision data: parties,
  event type, eligibility reason) and a Chinese block that states plainly it was never generated,
  rather than a bilingual card fabricated to look finished.
- **Analyst review boundary preserved**: every card's status is
  `baseline_shortlist_pending_review`. Nothing in this repo sets `publication.status` to
  `approved` or `published` — the data contract in `docs/decision-record.md` reserves that for a
  recorded human review, which never happened here.

## What it does not demonstrate

- Selection quality. The baseline's recall floor (14.3%) means most of what an analyst would
  actually publish is missing from this feed — see "Why recall collapsed" in
  `docs/phase-2-disposition.md`.
- The structured LLM classifier or the real bilingual drafter. Both are built and unit-tested but
  have never run against real evidence; running them is Step 1 in `docs/phase-2-experiment.md`'s
  successor and needs a provider credential plus about an hour.

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
