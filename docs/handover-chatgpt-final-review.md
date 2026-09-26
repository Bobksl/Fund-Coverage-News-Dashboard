# ChatGPT handover — independent final review (26 September 2026)

Copy everything below the line as the prompt.

---

You are the independent reviewer for the Fund Coverage News Dashboard (public repo `Bobksl/Fund-Coverage-News-Dashboard`, live at https://bobksl.github.io/Fund-Coverage-News-Dashboard/). Five pull requests (#3–#7) were merged on 25–26 September without an independent review. Review them now. Do not change code; report findings.

## Scope

Diff `a20f460..main` (36 commits). Key files:

- `tools/news_events.py`, `config/news_event_groups.json`: event grouping, the reviewed overlay (survivor IDs, aliases, member roles, date corrections, relations), anchored-headline novelty, and the evidence backfill sidecar.
- `tools/news_priority.py`: evidence-quote validation, priority classes, the `routine` flag and the ranking order.
- `tools/fetch_news.py`, `tools/source_evidence.py`, `config/source_tiers.json`: the refresh; source tiers (SEC EDGAR, regulators, ASIC sitemap, wires, GDELT); bounded page retrieval.
- `tools/summarize.py`: the prompt (`brief-v3.2-evidence`), absence-claim stripping, role-tagged managers.
- `tools/backfill.py`, `public/data/backfill.json`: re-briefing of older cards.
- `public/app.js`, `public/index.html`, `public/vendor/pdfjs/`: display of updates and hidden absence claims; inline PDF.js reports.
- `.github/workflows/refresh.yml`: SEC contact secret; manual backfill option.
- Docs: `docs/accuracy-handback-2026-09-25.md`, `docs/source-tiers.md`, `docs/news-events-contract.md`, `tasks/plan.md`, `tasks/todo.md`.

## Check, in this order

1. **Source preservation.** Day files are never rewritten. Every card in `public/data/*.json` appears in exactly one event in `events.json`. Every earlier event ID resolves to a live event or an alias. Backfill entries apply only while the card hash matches.
2. **Evidence honesty.** No claim about an unread article reaches the page. Headline-only evidence never yields a confirmed priority. `evidence_strength: primary` is set only from a verified source domain, never by the model. No publisher text is stored in `public/`.
3. **Grouping correctness.** Sample the reviewed groups in `config/news_event_groups.json`: same subject, action and period? Are digests only related, never members? Are the date corrections justified by their stated evidence?
4. **Ranking.** Order: class, severity, routine (non-routine first), time sensitivity, linkage, evidence strength, then latest material update. `routine` is honoured only for primary sources. Does a repeat ever advance `last_material_update_at`?
5. **Security.** `tools/source_evidence.py`: public-IP check at every redirect hop, pinned connections, caps on size, redirects and time, no paywall bypass. Is the SEC contact email absent from the repo (it must come from the `SEC_CONTACT_EMAIL` secret)? PDF.js is 6.3.289 with `isEvalSupported: false`.
6. **Workflow.** Can a manual run from a non-main branch deploy? (It must not.) Does the backfill step block the commit or deploy? (It must not.) Any other way to spend money unexpectedly?
7. **Claims in the docs.** Do the numbers in `docs/accuracy-handback-2026-09-25.md`, `tasks/plan.md` and `tasks/todo.md` match the repository? Current live state: 249 cards, 172 events, 95 Needs review, 73 Useful, 4 Important, 84 cards updated from source.

## Known limits (do not report these as new findings)

- Google News links are not decoded. GDELT refused both the development network and GitHub runners, so Google-News-only events stay Needs review.
- The acceptance packet and analyst labels live in a local `work/` folder and are not in the repo. Their results are summarised in `tasks/plan.md`.
- A15's summary repeats a claim from its own source's lead sentence.
- Model: `deepseek-flash`, chosen over `deepseek-v4-pro` in a small side-by-side test.

## Output

A table: severity (blocker / should-fix / note), file:line, finding, concrete failure scenario, suggested fix. Then one paragraph: is it safe to keep running as is? Only report what you verified in the code or data; say which checks you could not run.
