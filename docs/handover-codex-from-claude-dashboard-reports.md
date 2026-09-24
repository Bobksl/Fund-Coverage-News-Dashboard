# Handover to Codex: dashboard and report lane complete (24 September 2026)

Reply to [handover-claude-dashboard-extension.md](handover-claude-dashboard-extension.md). Details: [dashboard-events-and-reports.md](dashboard-events-and-reports.md).

## Git state
- **Branch:** `codex/news-events-priority`. It is local only: not pushed, not deployed. The live site is unchanged.
- **Commits on top of your `abaf58c`:**
  - `861c94f`: event-grouped dashboard, All dates, Priority/Newest sort, Reports tab, English PDF, browser tests and docs.
  - `ea47d16`: doc note on the Chinese draft.
  - `9581f1b`: analyst-approved Chinese PDF v1, wired into the Reports tab.
  - `e59b017`: Chinese PDF v2 (blank page 17 removed; v1 deleted from `public/reports/`, kept in history). All "Translation pending" wording removed.
  - A final commit adds this file.
- **Your files:** none edited. `tools/`, `config/`, pipeline tests and all of `public/data/` (including `events.json`) are untouched. The untracked `.claude/` belongs to the user and was not modified.

## What changed
**`public/app.js`, `public/index.html`:**
- **Grouping:**
  - `data/events.json` is optional and consumed as generated; the frontend has no grouping or scoring logic of its own.
  - A single date uses `date_views[date]`: its representative, display tags and rank.
  - All dates uses the global representative, tags and `priority_rank`.
  - **Sources (N)** lists every member article with headline, publisher, time, link and summary. The review badge and region come from the representative card.
- **Coverage labels:** Further coverage (`further_coverage`) is a button that opens the date the event was first reported. Source updated (`updated`) is labelled "not verified as a material change".
- **Fallback:** a missing or malformed index, or one whose membership doesn't match the loaded day files, shows every raw article with a one-line notice. Articles not in the index always appear as their own cards.
- **All dates mode:**
  - Earlier/Later stay visible but are disabled; Today works from either mode.
  - Day files load four at a time, each fetched once and cached.
  - Failed dates are named with Retry, and the list says it is not the full archive.
- **Filters and sort:**
  - Manager and sub-sector filters intersect and persist.
  - Priority sort uses rank, lowest first, with unranked cards last. Newest sort uses `last_material_update_at` in All dates, and publication or observation time on a single date.
  - Language never changes the order.
- **Labels and counts:**
  - Bilingual priority label and reason on each card. `potential_urgent` shows as "Potential urgent item — needs verification", never as Urgent.
  - When all listed events are Needs review, a note explains the legacy archive.
  - Counts read "E events · A articles", filtered and total.
- **Reports tab (`#reports`):**
  - English | 中文 picker with an inline `<object>` viewer and Open/Download buttons always visible.
  - It defaults to the page language.
  - Only languages with an approved file are offered, with no placeholder wording.
- **Unchanged:** all existing controls and behaviour, `textContent`-only rendering and the http(s) link check.

**`public/reports/`:**
- **`junson-private-credit-report-2026q3-en-v2.pdf`** (SHA-256 `84e9a89bb7f27dc6f1cb316b810dcecb46d6ab89f7799e71bc9b725e15a0ab0c`):
  - A faithful Word export of `Junson_Private_Credit_Report_2026Q3_EN_v2.docx`: 21 pages, 58 exhibits, 46 images and 58 source notes.
  - Every numeric token from the source is present.
- **`junson-private-credit-report-2026q3-zh-v2.pdf`** (SHA-256 `4f8e456ab7dd821a0cc7283bd38aceb3b334dfacd1936d3f6edae96cccf5d106`):
  - Simplified Chinese, 21 pages, analyst-approved including terminology.
  - Page-by-page text is identical to the approved v1, minus v1's blank page 17.
  - All 58 exhibits and 46 images are present, and every numeric token is present.
- **Kept as in the English by analyst decision:** English chart labels (redrawing deferred), the Exhibit 9 red draft note and the "internal research use only" footer.
- **Chinese source** (git-ignored, local): `work/report-zh-draft/`, holding `zh_*.json`, `build_zh.py` (which includes the page-break fix) and `REVIEW_NOTES.md`.

**`tests/test_dashboard_ui.py`:** 15 Playwright tests in real headless Chromium against a local server for `public/`. Failure modes use request interception, and priority fixtures are synthetic and never written to `public/data/`.

## Verification
- **Full suite:** `python -m pytest -q` gives 396 passed and 14 subtests passed (your 381 plus 15). `ruff` on the test file and `git diff --check` pass.
- **Real archive in the browser:**
  - All 34 dates match the date-view representatives in rank order with correct counts, and every article link is reachable.
  - Apollo Executive Centre (16/18 Sep) and BlackRock (11/13 Sep) link back to their first date. All six same-day pairs expand to both sources.
  - All dates shows 174 unique events and 182 articles, all 182 source URLs, and exactly eight Sources (2) groups.
  - All 126 manager × sub-sector combinations give the expected counts.
  - Newest order, keeping the order in ZH, language persistence, Today, keyboard use and 375 px mobile width all pass.
- **Mocked failure cases:**
  - A 404 or malformed `events.json` falls back to raw articles.
  - An unmapped article shows as a singleton.
  - A stale index falls back with a notice.
  - A failed day is named, and Retry recovers it.
  - Rapid date switching keeps the last choice.
- **Synthetic priorities:** Urgent > Important (tie by rank) > Useful > Needs review. Potential-urgent notices appear; a single date uses its own ranks.
- **Reports:** both PDFs are served and the view picks the right file per language. With no Chinese file, only English is offered and no pending wording appears.
- **Counts:** 182 articles and 174 events before and after, with 8 two-article groups. No source disappeared. All 174 events are Needs review; no labels were invented.

## Requests to Codex
1. **No contract change is needed.**
2. **Integrate and deploy** after your release checks, keeping any newer scheduled data on `main` (single integrator; no force push).
3. **After deployment,** open the Reports tab in a desktop browser with a PDF viewer and confirm both PDFs embed. Headless Chromium could only confirm the Open/Download fallback.
4. **`tasks/todo.md`:** mark item 3 (All dates, sort, UI) done, and item 4 (reports) done with the Chinese version published.
5. **Still with you:** historical priority assessment and source/evidence backfill, independent review, and analyst ranking acceptance. Legacy events stay Needs review until then.

## Open item
The analyst is doing a full review of the Chinese report on the afternoon of 24 September. Claude applies any corrections in `work/report-zh-draft/`; the result is published as `…-zh-v3.pdf` with `REPORTS` in `public/app.js` updated to match. Until then, v2 is the approved version.
