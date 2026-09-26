# Claude handover — remaining work after 26 September 2026

Copy everything below the line as the prompt. Wait for the ChatGPT final review (`docs/handover-chatgpt-final-review.md`) first, if it is running, and fix its blocker findings before anything below.

---

You are continuing work on the Fund Coverage News Dashboard (repo `Bobksl/Fund-Coverage-News-Dashboard`; live site https://bobksl.github.io/Fund-Coverage-News-Dashboard/). Read `tasks/plan.md`, `tasks/todo.md`, `docs/news-events-contract.md` and `docs/source-tiers.md` first. The user reads with ADHD: lead with the next action, number steps, keep lists short.

## Rules that still apply

- Work on a branch from fresh `origin/main`. Scheduled refreshes commit data to main twice each weekday (08:00 and 16:00 HKT). Never force-push. The user merges PRs; `gh` is not installed, so give a prefilled compare link.
- Never rewrite day files (`public/data/YYYY-MM-DD.json`). Grouping changes go in `config/news_event_groups.json` with card hashes; re-brief results go in `public/data/backfill.json`. Regenerate `events.json` only with `python -m tools.news_events --data-dir public/data`, and check that every card is in exactly one event and every earlier event ID still resolves.
- Tests never write `public/data`. Before each commit: `python -m pytest -q` (check the exit code, not just the tail), `ruff` on changed files, `git diff --check`. Write failing tests first for fixes.
- Paid calls use `deepseek-flash` (about 0.004 CNY per brief). The user's balance is small (about 5 CNY at last report); say the expected cost before any run of more than 50 calls. SEC requests read the contact from the `SEC_CONTACT_EMAIL` env or secret; never put the email in the repo.
- Relevance policy (user decision): include all tracked-manager and sector matches. Routine primary-source filings rank below non-routine items of the same severity. The six-component score stays rejected.
- Manual workflow runs must use **Branch: main**. A run from another branch commits to that branch and cannot deploy.

## Open items, in order

1. **Refresh health check (next weekday, 08:00 HKT run).** Read `public/data/status.json` and the new cards:
   - feed failures and whether any SEC, regulator or wire item arrived
   - evidence level of new cards (excerpt vs headline-only)
   - whether any new card was flagged `routine`
   - model calls

   Report in five lines.
2. **Google-News-only events (95 Needs review, mostly these).** GDELT refused both networks, so it is unusable. Count for a week how many Important-looking stories arrive only through Google News; the user will then decide on Brave Search API (about 1,000 free searches a month, credit card required, storage terms to confirm). If the user supplies a key, add a Brave resolver next to the GDELT one in `tools/backfill.py` (same 60% title-match gate and paywall skip) and optionally in the refresh.
3. **Ranking decisions still open (need the user):**
   - pilot preferences 03 > 05 > 02, and the C08 sector explainer above direct-manager Useful items
   - F11: does an equity stake (Apollo in ONEOK) count?
   - whether non-routine filings should stay above press-reported launches

   Write each as a one-line contract before changing `tools/news_priority.py`.
4. **Tags on older cards.** The backfill updates summaries but not manager tags, so a private-equity exit (Apollo/Kelvion) and an equity stake still show as direct manager news. Proposal: store the brief's `gp_roles` in `backfill.json` and let `display_gps` drop managers the re-brief marked as mentions. Additive; needs a test and the user's OK.
5. **Source gaps (`docs/source-tiers.md`):**
   - NAIC and FCA: no usable feed; consider a small page reader that follows robots.txt, as done for ASIC.
   - Business Wire: opaque feed codes; skip unless a code is found.
   - 10-Q/10-K: use SEC's structured-data API for NAV per share and net investment income moves; needs a NAV-move threshold from the user.
   - Paid press: revisit after two weeks of counts.
6. **Known content issues:**
   - A15 (Jefferies) repeats its source's "$4bn at first close" lead sentence; decide with the user whether to add a reviewed summary correction (an additive overlay; none exists yet).
   - The Chinese report v3, if the analyst sends corrections: add the file and update `REPORTS` in `public/app.js`, keeping v2 until approved.
7. **Housekeeping.** Refresh the stale text in `tasks/todo.md` items 1, 2b and 5. Delete merged remote branches only if the user asks.

## Done already (do not redo)

- Grouping sweep (177 → 153 events at the time).
- Hidden unread-article claims, and inline PDF.js reports (phone check passed).
- Source tiers: SEC EDGAR for 13 registrants; Fed, SEC, ECB, BoE and ESMA feeds; ASIC sitemap; GlobeNewswire and PR Newswire.
- Backfill of 86 older cards with readable sources (74 verified).
- Routine ranking.
- Acceptance packet scored (results in `tasks/plan.md`).
