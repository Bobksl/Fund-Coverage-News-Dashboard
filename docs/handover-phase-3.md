# Phase 3 handover — prepared 2026-09-12

Copy everything below the line into the new agent's first message.

---

You are taking over the **Fund Coverage News Dashboard** for Junson Capital's Alternative
Investment team. Act as a pragmatic senior Python engineer. This is an internal demo, not
production infrastructure.

**Workspace:** `C:\Users\user\OneDrive - The University of Hong Kong - Connect\桌面\Projects\Fund-Coverage-News-Dashboard`
**Branch:** `codex/phase-1-editorial-spec` (clean, 15 commits ahead of origin, nothing pushed)

**Hard deadline: the demo ships tomorrow night.** Prefer the shortest honest path to a working,
explainable output over completeness. Simplify anything that does not change what the demo shows.

## Read first, in this order

1. `docs/phase-2-disposition.md` — what was measured and what failed
2. `docs/phase-2-collection-status.md` — the corpus, its gaps and its skew
3. `docs/phase-2-engineering.md` — the modules and how to run them
4. `docs/decision-record.md` — the data contract every record obeys
5. `tasks/todo.md` — current checklist

## Where things actually stand

Phases 0–2 are **done**. Phase 2 closed with a **FAIL** disposition, which is a real result, not a
blocked step.

- **Corpus:** 276 evidence records under a frozen collection policy. 245 natural feed across 14
  sources, 31 independently curated challenge probes, 91 challenge probes in total counting linked
  records. 275 carry hashed text excerpts.
- **Labels:** 274 rows from one analyst, audited clean. 95 publish, 42 reserve, 134 reject,
  3 review, across 262 distinct event groups.
- **Freeze:** `work/phase2/freeze-001/` — labels, evidence and split manifest hashed before any run.
- **Measured result (deterministic baseline only):** natural-feed holdout 75% precision against a
  90% bar, **14.3% recall** against an 85% bar, 1 of 2 must-not-miss surfaced. Zero false merges.
  Challenge cohort inconclusive at 10 publish-worthy events, half the minimum.
- **The structured LLM classifier has never been run.** No model provider is configured. The
  adapter is built and tested; it needs credentials and about an hour.

**Why recall collapsed:** 45 of 78 missed publish-worthy events scored no relevance at all. The
analyst publishes on **sector relevance**; the baseline fires on **watchlist entity match**, and
most publish-worthy articles are trade-press reports about managers outside the 13-entity
watchlist. This is a specification gap, not a tuning gap.

## Do this, in this order

**Step 1 (highest value, ~1 hour). Run the structured classifier on the frozen split.**
Everything is built. Inject a provider into `tools/classifier.StructuredClassifier` and run the
same three partitions the baseline ran. This turns "untested" into a number and is the
experiment's actual hypothesis. If recall moves from 14% toward the 85% bar, the Phase 3 pilot
becomes defensible on evidence. If it does not, you have learned something more important than
anything the demo could show.

```bash
python -m unittest discover -s tests -v      # 219 tests, expect OK
python tools/validate_spec.py                # expect zero errors
```

The runner, evaluator and freeze enforcement are in `tools/runner.py`, `tools/evaluator.py`. The
scratch scripts that drove the baseline run are gone; rewrite the ~40 lines rather than hunting
for them. Predictions must be written and hashed **before** the evaluator sees a gold label — the
evaluator enforces this and will refuse otherwise.

**Step 2 (if Step 1 cannot happen — no provider, no time). Narrow the claim and demo the
mechanics.** A demo that honestly shows "collected corpus → contract-valid decisions → analyst
review → bilingual card" is worth more than a fabricated performance claim. Say plainly that
selection quality is unvalidated and that the measured floor missed most publish-worthy events.

**Step 3. The browser demo.** A local static HTML/JS page reading approved daily JSON: date
navigation, EN/Chinese cards, source links, empty and stale states. `tools/drafting.py` already
produces bilingual cards with grounding and parity checks. This is the most demo-visible work and
needs no new infrastructure.

## What NOT to do

- **Do not re-collect or re-curate.** The corpus is frozen and adequate. Re-running collection
  burns the deadline for nothing.
- **Do not build scheduled ingestion, a hosted database, auth or a Next.js app.** Out of scope.
- **Do not tune thresholds against the holdout.** If you revise rules, do it on calibration and
  say so.
- **Do not present the baseline's numbers as the system's performance.** They are the floor.
- **Do not pass analyst labels, rationales, event-group IDs or challenge categories into any
  inference input.** `tools/records.to_inference_input` enforces this; keep it that way.
- **Do not push to origin** without asking.

## Three loose ends, all small

1. **Vitabiotics date.** The article body reads "London – July 24, 2026"; the index card showed
   none, so the record was excluded from the packet as undated. Applying that date is a decision,
   not a cleanup.
2. **A challenge rationale overclaims.** BasePoint Asset Recovery LLC is described as an
   "unrelated Connecticut filer", but its Form D names an officer c/o BasePoint Capital LLC, which
   entity research lists as a watchlist BasePoint subsidiary. The probe is valid; the wording is
   not established.
3. **PAG's Cordina article** is the one record with no captured text — its page returns navigation
   even when rendered. One of 276, recorded as a disclosure.

## Standing constraints

Public sources only, no paid data, no paywall bypass. All 13 watchlist entities are
**monitoring-only** — never infer holdings. Preserve vehicle/parent and sponsor/lender/adviser
distinctions; OTF is not an alias for Blue Owl, and standalone NB, PAG, HSBC and Guggenheim
matches are unsafe without context. Analyst decisions stay evaluator-only. Keep evidence and
analyst data in ignored `work/`; nothing private enters Git.

Report honestly: if something fails, say so with the output. A thin or negative result is a
finding, not a problem to hide.
