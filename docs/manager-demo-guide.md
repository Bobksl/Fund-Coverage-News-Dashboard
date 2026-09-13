# Manager demonstration

## Launch the Phase 8 demo

From the project directory, serve the published site and the separate operator page. Both bind to
127.0.0.1 only and already exist locally under git-ignored `work/phase8/`:

```powershell
python -m http.server 8644 --bind 127.0.0.1 --directory work/phase8/site
```

```powershell
python -m http.server 8646 --bind 127.0.0.1 --directory work/phase8/operator
```

Open http://127.0.0.1:8644/index.html (the published edition) and
http://127.0.0.1:8646/index.html (the operator review queue). On the published page choose
**Jump to latest historical edition**. The empty current-day view is intentional: this is a
historical sample, not today's news. If `work/phase8/` is missing, rebuild it with the runbook in
[Phase 8 first delivery](phase-8-first-delivery.md). No step there calls a model.

Fallback: the original Phase 6 export still serves the same card on its own:

```powershell
python -m http.server 8643 --bind 127.0.0.1 --directory work/phase2/phase6-review/reviewed-demo-export
```

Do not run the default `export_demo` command for this meeting; it builds a different,
baseline-candidate demonstration.

## Five-minute walkthrough

1. Explain the purpose: a monitored-manager and alternatives-sector editorial
   shortlist, with source-backed explanations and human publication approval.
2. Explain the filtering sequence: sufficient evidence → resolved entity and
   economic role → A/B/C relevance → new event and duplicate grouping → economic
   gates → deterministic score and daily capacity → human review → bilingual card.
3. A means direct monitored-entity involvement; B means direct sector read-through;
   C requires a specific economic transmission path. A manager name alone is not
   enough, and an untracked-manager story can still qualify under B or C.
4. Scores do not rescue failed relevance/evidence gates. Scores 80+ are priority
   shortlist, 70–79 ordinary shortlist; 60–69 reserve needs explicit analyst
   approval. The daily target is 6–10, without a forced minimum.
5. On the operator page, show why each candidate landed where it did: the one
   shortlisted card, six sent for review (each names the gate that needs a person),
   one suppressed (its failed gates), and one article awaiting classification.
   Nothing on that page is approved or published.
6. On the published page, show the **Update status** panel: last source check,
   last successful publication and article dates are separate facts, and update
   mode is manual. Show the Blue Owl financing card, its source and score; switch
   EN/ZH. This one card completed real classification, drafting and named human
   approval. Missing evidence or ambiguous judgments go to review, not invented facts.
7. Press **Reload published edition** and explain that it re-reads the published
   edition only; it does not check sources, collect news or run a model.

The rulebook is `docs/editorial-rulebook.md`; this script describes those rules,
not a claim that every model judgment follows them correctly.

## Answer: how does the dashboard update?

**It updates manually, through a repeatable workflow.** An operator supplies source
evidence, which records a source check. A queue build explains every candidate. A
shortlisted event gets a bilingual draft, a named person approves that exact draft
revision, and only then does the operator publish a new edition. A failed publish keeps
the last good edition. Reloading the page loads the published edition; it does not
search for news or run the model. There is no automatic schedule, so update frequency
is operator-driven.

Source checking, publication and browser refresh are three separate steps, and the page
shows them separately. The demonstrated update republished the existing approved card
through this workflow at zero model spend; it did not add a new card.

**Possible next step (not started):** check approved sources at 08:00 and 16:00 Hong Kong
time on weekdays, plus operator-triggered checks. Those checks would only fill the review
queue; publication would still wait for human approval. The schedule is proposed, not
installed or running.

## State the limitations plainly

One reviewed card demonstrates the workflow, not coverage or scaled accuracy.
No budget is approved for model calls, so new articles cannot be classified or drafted:
they wait in the queue, and a genuinely new approved card is not possible in this demo.
Only exactly identical inputs reuse earlier stored model output.
The nine-article smoke was category-selected, not representative. Full historical
model comparison was cancelled for the demo deadline; precision/recall are not
established. Historical baseline performance failed its bars. Model judgments can
be wrong, sources incomplete and news stale; multilingual quality and throughput
are not established. No live ingestion, scheduler or automatic publication is running.
