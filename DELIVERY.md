# Fund Coverage News Dashboard — delivery note

Junson Capital · Alternative Investment team · 2026-09-13

## 1. Live page

**https://bobksl.github.io/Fund-Coverage-News-Dashboard/**

The page opens on today's date (Hong Kong time). Earlier days are available from the date menu or the
previous/next buttons. The **EN | 中文** switch in the top-right corner changes the whole page. Each
item is a short summary with a link to the original article, followed by small-print GP, sub-sector
and region tags. It can be filtered by manager or sub-sector.

At delivery the page holds 80 items across 24 days, from 12 Aug to 13 Sep 2026.

## 2. Source code

Repository: https://github.com/Bobksl/Fund-Coverage-News-Dashboard

| Path | Role |
|---|---|
| `public/` | The website itself (static HTML/JS plus JSON data), published by GitHub Pages |
| `tools/fetch_news.py` | Scheduled refresh: fetch feeds, apply the keyword rule, write new cards |
| `tools/summarize.py` | DeepSeek call that writes the English/Chinese summary and picks tags |
| `tools/site_data.py` | Validates cards and maintains the per-day files, index and 90-day window |
| `tools/build_site.py` | One-off backfill of the analyst-reviewed history |
| `config/filter_rules.json` | Everything tunable: managers, sub-sectors, keywords, feeds, schedule |
| `.github/workflows/refresh.yml` | The schedule and deployment |

## 3. How the dashboard updates

**Automatic, twice every weekday: 08:00 and 16:00 Hong Kong time.** A GitHub Actions job (it runs
on GitHub's servers, so no one's computer needs to be on) does the following:

1. Fetches the news feeds listed in section 4.
2. Drops anything already on the page, and repeat headlines of the same story, then applies the
   relevance rule.
3. Asks DeepSeek to write the English and Chinese summary and choose tags, and to reject items that
   are clearly not investment-relevant.
4. Saves the new items under their publication date (Hong Kong time), removes days older than 90
   days, commits the data to the repository and republishes the site.

Other triggers: anyone with repository access can press **Run workflow** for an immediate refresh,
and any manual change to `public/` republishes the site. Readers simply reload the page to see the
latest version.
The header shows when the last successful refresh happened and flags a failed one. A failed refresh
never removes what is already published.

**Reviewed vs. auto-selected.** The history from 12 Aug to 10 Sep 2026 was selected by an analyst
(274 articles read, 95 marked publish-worthy, 72 events published after merging duplicate coverage
and dropping five items that fit no tracked sub-sector). It is shown as reviewed. Items added by the
refresh are published immediately and carry a small "Auto-selected · not yet reviewed" badge.

**First refresh, 13 Sep 2026.**
- All 28 feeds responded and returned 215 recent items, 138 of them unique.
- 20 items matched the rule. DeepSeek rejected 12 (for example crypto "private credit" products
  and repeat coverage of one BlackRock story) and published 8.
- The 20 briefs used about 21k tokens, well under ¥1.

## 4a. News filtering logic

**What counts as relevant.** An item belongs on the page if it could reasonably change an investor's
view of (1) a tracked manager or vehicle, (2) the expected risk or return of a tracked strategy,
(3) deployment, fundraising, liquidity, valuation or exit conditions, or (4) the financing and
competitive environment around the portfolio. Because our exposure to the multi-strategy managers is
their credit business, each manager is defined by its credit scope. For example, Guggenheim
Investments counts and Guggenheim Securities advisory work does not; HSBC Asset Management counts and
HSBC group banking does not; a routine KKR private-equity buyout does not count.

**Sources.**
- *Scheduled refresh:* 26 Google News searches, one for each of the 13 managers and 13 covering
  the 8 sub-sectors. They use the US edition, plus a UK edition for European private credit, CLOs,
  direct lending and HSBC AM. Two publisher feeds are added: Alternative Credit Investor and
  Commercial Observer. Google News is only used to discover articles; every card links to the
  original publisher.
- *Reviewed history:* the managers' own newsrooms (Blue Owl, OTF, Pretium, KKR, PAG, CIFC, BasePoint,
  Neuberger, Apollo, Bain Capital, Guggenheim Investments, HSBC AM), SEC EDGAR filings for the tracked
  issuers, Alternative Credit Investor and Commercial Observer's finance section.

**The rule** (in `config/filter_rules.json`). Keep an item when all three conditions hold:

1. **Subject.** It names a tracked manager, or it matches a tracked sub-sector. Managers with large
   non-credit businesses (KKR, Apollo, Bain Capital, Guggenheim, Neuberger, PAG, Bayview) also need a
   credit word such as lending, loan, CLO, BDC or financing.
2. **Material event.** It describes one, such as fundraising or a close, a financing, an acquisition,
   results or NAV, a default or restructuring, a rating action, redemptions, regulatory action or a
   senior leadership change.
3. **Not noise.** It is not an award, podcast, webinar, sponsorship or similar.

DeepSeek then reads the item and can reject it as a second check. It also writes the summary
**using only the text supplied**, so a paywalled article with just a headline gets a short,
headline-level summary rather than invented detail.

Why a simple rule instead of a score. An earlier design ranked items with a six-part score (portfolio
relevance 30, materiality 25, transmission 20, actionability 10, source credibility 10, novelty 5)
and published items scoring above 70. It was over-engineered for the goal of a live tracking page. A
test against the analyst's labels also showed that a filter built mainly on manager-name matching
missed most relevant stories: it caught only 14% of them, with 75% precision. Most analyst-selected
stories were sector news about managers we do not track. The current rule therefore treats
sub-sector matches as equal to manager matches. The scoring design is kept as a documented next step
in `docs/editorial-rulebook.md`.

## 4b. Limitations and next steps

**What the current approach cannot cover well**
- **Paid sources.** No Bloomberg, WSJ, FT, PitchBook subscriber content, Creditflux, 9fin or
  Airfinance Journal. Coverage of paywalled stories is limited to what Google News and free feeds
  expose, so many auto-selected summaries are based on the headline only and are short.
- **Keyword-rule errors.** Ambiguous names (Apollo, PAG, Bayview) and fashionable phrases (crypto
  "private credit" tokens) let in unrelated stories. Stories that describe an event without the
  expected keywords can be missed. In the first refresh the AI check removed 12 of 20 matches, but
  the accuracy of the rule plus AI check has not been measured against analyst judgement.
- **Same event, several articles.** Coverage of one event from several outlets is merged only when
  the headlines are close. Reworded headlines can still produce two cards.
- **Uneven coverage.** Europe is searched separately, but the ~20% share is not enforced (0 of 8 in
  the first refresh). Aircraft leasing, GP stakes and CLOs have few dedicated free sources.
- **Unreviewed summaries.** Auto-selected items are AI-written and not checked by a person before
  they appear. The badge and the source link are the safeguards.
- **Schedule and sources.** GitHub can delay scheduled runs by some minutes. Google News links pass
  through a Google redirect. The reviewed history was labelled by one analyst.

**What I would add with more time**
1. A light review step: approve or hide buttons for an analyst, turning "unreviewed" into "reviewed".
2. Licensed trade feeds (Creditflux, 9fin, PitchBook, Airfinance Journal) and more European outlets.
3. A weekly accuracy check of the rule against reviewed items, tuning keywords from misses and false
   hits.
4. Grouping of articles about the same event into one card with multiple sources.
5. A minimum European share per week, filled from the UK-edition searches when available.
6. Re-introducing the composite score for ranking within a day, once there is budget to calibrate it.
7. A morning email or Teams digest of the day's top items.
