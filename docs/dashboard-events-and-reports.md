# Dashboard: event grouping, All dates, priority sort and Reports

Frontend lane of the 25 September extension (handover: [handover-claude-dashboard-extension.md](handover-claude-dashboard-extension.md)).
Files: `public/app.js`, `public/index.html`, `public/reports/`, `tests/test_dashboard_ui.py`. No pipeline or data file changed.

## Behaviour
- **Events.** The page loads `data/events.json` alongside the existing files, if it is there. It never groups or scores articles itself.
  - **One date:** each event appears once, using that date's `date_views[date]`: its representative, display tags and rank.
  - **All dates:** each event appears once, using the global representative, `display_gps`/`display_sectors` and `priority_rank`.
  - **Sources (N):** lists every member article with headline, publisher, time, link and summary.
  - **Kept from the card shown:** the review badge and region come from the representative raw card.
- **Further coverage** (`further_coverage`) is a button. It opens the date the event was first reported.
- **Source updated** (`updated`) is labelled "not verified as a material change".
- **Fallback.** If `events.json` is missing or malformed, or its membership does not match the loaded articles, every raw article is shown on its own with a one-line notice. An article that is not in the index always appears as its own card.
- **All dates mode:**
  - The **All dates** button and the "All dates" entry in the date menu both switch to it. Earlier/Later stay visible but are disabled; they work again once a date is chosen. Today works from either mode.
  - Day files are fetched four at a time, and each day is cached and fetched once. A progress line shows while loading.
  - If some days fail, a warning names them, says the list is not the full archive, and offers Retry.
- **Filters.** Manager and sub-sector filters intersect, and they persist across date and mode changes.
- **Sort: Priority / Newest.**
  - **Priority** uses the pipeline's rank, lowest first. It uses the date view's rank on a single date and the global rank in All dates. Articles without a rank come last.
  - **Newest** uses `last_material_update_at` in All dates. On a single date it uses the representative's `published_at`, then `observed_at`, then the date.
  - Neither order reads any text, so changing language never reorders cards.
- **Priority labels.** Urgent, Important, Useful and Needs review are each shown with their reason, in EN and ZH. `potential_urgent` shows as "Potential urgent item — needs verification" and is never shown as Urgent.
- **Legacy archive note.** When every listed event is Needs review, a note explains that the older archive has no assessed priorities. This is the case for all 174 current events.
- **Counts.** With grouping on, the count reads "E events · A articles", or "e of E events · a of A articles" when filtered. Without grouping, the original item counts are kept.
- **Reports tab (`#reports`).**
  - The report shows inline in an `<object>` PDF viewer. **Open PDF** and **Download PDF** are always visible, and browsers without a PDF viewer show a fallback message.
  - The report language follows the page language until the reader picks one.
  - English and Chinese PDFs are both published. If a report has no approved file for a language, that option reads "Translation pending" and the English original is shown with a notice.
- **Unchanged:** Today, Earlier/Later, the date menu, language persistence, status line, fallback-to-latest notice, loading/error/empty states, textContent-only rendering and the http(s) link check.

## Verification (24 September, local server)
`python -m pytest -q tests/test_dashboard_ui.py` runs real headless Chromium through Playwright against a local server for `public/`. Failure cases use request interception, and nothing is written to `public/data/`. Result: **15 passed**.

**Real archive:**
- **Every date (34):** the cards match the date-view representatives in rank order, and the count matches. Every raw article's link is reachable from a card or its Sources list.
- **Cross-date pairs:** Apollo Executive Centre (16/18 Sep) and BlackRock (11/13 Sep) show Further coverage, and the button returns to the first date.
- **Same-day pairs:** all six expand to both members' headlines and summaries.
- **All dates:** 174 cards and 174 unique IDs, in global rank order. The count reads 174 events · 182 articles · 34 dates. All 182 source URLs are present, and there are exactly eight Sources (2) groups.
- **Filters:** all 126 manager × sub-sector combinations match the counts expected from `events.json`, and both selections survive Today and a mode switch.
- **Newest and language:** Newest order matches `last_material_update_at`. Switching to ZH keeps the order, and the language persists across a reload.
- **Today** works from All dates. Tab and Enter operate the All dates button and the Sources disclosure. At 375 px there is no horizontal scroll.

**Mocked failures:**
- A 404 or malformed `events.json` gives the raw fallback: 25 cards on 23 Sep and 182 in All dates.
- An unmapped synthetic card appears on its own (24 events · 26 articles).
- A stale index (a grouped member removed from a day) gives the raw fallback with a notice.
- If one day returns 500, the warning names it, the scope reads 33 dates and Retry recovers the full list.
- On a rapid date switch with a delayed response, the view stays on the last choice.

**SYNTHETIC priorities** (fixture defined in the test and served only through interception):
- All-dates order is Urgent > Important = Important (tie kept by rank) > Useful > Needs review > Needs review.
- Potential-urgent notices appear on the Urgent card and on one Needs review card, and Needs review is never labelled Useful.
- A single date uses its own ranks, which differ from the global order. Newest and a language switch keep the expected order.

**Full suite:** `python -m pytest -q` gives 396 passed and 14 subtests passed (Codex's 381 plus these 15). Lint and whitespace: `python -m ruff check tests/test_dashboard_ui.py` and `git diff --check` pass.

## English report PDF
`public/reports/junson-private-credit-report-2026q3-en-v2.pdf`, SHA-256 `84e9a89bb7f27dc6f1cb316b810dcecb46d6ab89f7799e71bc9b725e15a0ab0c`.

**How it was made:** a read-only copy of `Junson_Private_Credit_Report_2026Q3_EN_v2.docx` was exported with Microsoft Word 16 (`ExportAsFixedFormat`). Headings become bookmarks, structure tags are kept, and document properties are left out.

**Source inventory:** 7,746 words, 39 tables, 46 PNG images, no tracked changes, comments or hidden text.

**Checks:**
- The PDF has 21 A4 pages.
- All 58 exhibit captions are present, and all 46 images are embedded.
- All 58 "Source:" notes are present.
- All 458 distinct numeric tokens in the source text appear in the PDF text.
- Every page was rendered and inspected. No table or figure is clipped or overflows the margins.

**For the author** (left unchanged so the PDF stays faithful to the source):
- The Exhibit 9 caption ends with a red draft note, "add ICE BofA US HY YTW to this exhibit". The chart already shows that series.
- Page breaks separate some captions from their charts: Exhibit 9 (pp. 3→4), Exhibits 14/15 (5→6), 34/35 (12→13) and 58 (20→21).
- Every page footer reads "For internal research use only". Publishing publicly was authorized for this assignment.

## Chinese report PDF (approved)
`public/reports/junson-private-credit-report-2026q3-zh-v1.pdf` (Simplified Chinese).

**How it was made:**
- An AI draft was translated from the English source and rebuilt in the original layout.
- It passed per-segment number checks: every number in each English segment appears in its Chinese segment.
- On 24 September the analyst reviewed it and approved it, including the terminology. The analyst exported this PDF and added `files.zh` in `public/app.js`.

**Checks on the published file:**
- 22 A4 pages, with all 58 exhibits and all 46 images.
- Every numeric token in the English source appears in the PDF text.
- No personal document metadata.
- The file is byte-identical to the reviewed draft preview.

**Kept as in the English, by analyst decision:**
- The chart images keep their English labels (option A below; redrawing is deferred).
- The Exhibit 9 draft note and the "internal research use only" footer are also left unchanged.

**Pending:** the analyst's full review on the afternoon of 24 September may produce corrections. Those should be applied to the draft source in `work/report-zh-draft/` (`zh_*.json`, then `build_zh.py`), exported again, and published under a new version number (`…-zh-v2.pdf`), not by overwriting v1.

### Chart labels inside images
All 46 images contain English text: titles, legends, axis labels, category names and data callouts. They are images, so the text cannot be translated in the DOCX. 45 are charts for Exhibits 1–7, 9–15, 17–29, 32–35, 39–40, 43–44 and 49–58; the 46th is the Exhibit 31 maturity-wall chart inside a layout table. Exhibits 8, 16, 30, 36–38, 41–42 and 45–48 are Word tables and are translated with the text.

| Group | Exhibits | English text in the images |
|---|---|---|
| Market size and flows | 1–7 | Channel/series legends (Institutional, Retail, Insurance estimate, NAV, Dry powder, Refi/Non-refi, Syndicated loans, Private credit), holder pie labels, US$ axes |
| Returns and spreads | 9–11 | Series legends (Lincoln senior debt, Morningstar LSTA Single B, ICE BofA HY YTW), EBITDA cohort labels, endpoint callouts |
| Terms, defaults, recoveries | 12–15, 17–21 | Segment labels (Lower/Core/Upper MM), provider legends, sector names (19 Fitch sectors in Ex. 19; 10 in Ex. 21) |
| Leverage and coverage | 22–25 | Rating band labels, series legends, point annotations |
| BDC health | 26–29, 31 | Series legends, maturity-wall legend and sidebar heading |
| Fund holdings | 32–35, 39–40, 43–44 | Portfolio type, geography, currency, bank, GICS sub-industry and sector labels, project names |
| Competitor analysis | 49–58 | Fund, cohort and quartile labels, and 30+ manager names in the Ex. 55 scatter |

**Options:**
- **A — Bilingual captions (recommended for Friday).** Translate the captions and notes and add one note: "图表内标签为英文原文". No extra technical effort beyond the text translation, plus about 0.5 hour of analyst check.
- **B — Full label translation.** Redraw all 46 charts with Chinese labels. This needs the original chart data or scripts, because the DOCX holds only PNGs. The plan estimates about 6–12 extra hours; add analyst review of every redrawn chart. Without the original chart sources, the charts must be rebuilt from the digitised values, and the estimate should be redone before starting.

## Remaining work
- **Analyst's full Chinese review (24 September afternoon):** any corrections become `…-zh-v2.pdf` plus an update to `REPORTS` in `public/app.js`.
- **Chart labels:** redrawing them in Chinese is deferred by analyst decision.
- **Historical priority and source backfill (Codex's lane):** all legacy events stay Needs review until evidence is recovered.
- **Before release:** after deployment, check the PDF inline in a desktop browser with a PDF viewer. Headless Chromium has no viewer, so only the Open/Download fallback was verified.
