# Source tiers — 25 September 2026

Branch `claude/primary-sources` (on top of `claude/sunday-accuracy`). Config: `config/source_tiers.json`. Code: `tools/fetch_news.py` (feeds, EDGAR and GDELT parsing, pacing, ordering), `tools/source_evidence.py` (SEC contact header, filing document choice, cover-page trimming).

## What the refresh reads now

| Tier (editorial rulebook) | Implemented | Not yet |
|---|---|---|
| Primary: SEC EDGAR / public BDC filings | 13 registrants' own EDGAR feeds (OCIC, OTIC, OBDC, OTF, OWL, ADS, MFIC, APO, K-FIT, FSK, KKR, BCSF, Lincoln Bain TCF). Forms: 8-K, 8-K/A, SC TO-I(/A), 424B2, 424B5, 13D(/A). | 10-Q/10-K (main documents exceed the 1 MB cap); 424B3 sticker supplements excluded as noise. |
| Primary: regulators | Fed, SEC press releases, ECB, Bank of England, ESMA official RSS; ASIC media releases from its official sitemap. A regulator release needs a manager or sector match but not an event keyword (the release is itself the action). | FCA (403 to automated clients), NAIC (no official feed found). |
| Primary: GP / borrower IR, rating agencies | — | No open feeds; KBRA/Fitch releases arrive through Business Wire and news. |
| Secondary: wires, reputable press | Alternative Credit Investor and Commercial Observer RSS; GlobeNewswire keyword feeds ("private credit", "business development company"); PR Newswire financial-services feed (latest 20 only); bounded page retrieval. Wire items carry `source_origin: wire` (issuer-origin, never marked primary) and still need the keyword rule. | Business Wire (opaque feed codes, 403 to automated clients). |
| Discovery | 26 Google News queries (headline-only: links are not decoded); GDELT DOC API, 2 queries (tracked managers + credit terms, and sector terms), which return real publisher URLs. | Search APIs. |

## Rules

- A filing from a listed registrant skips the keyword rule (the registrant is a tracked vehicle and the form is in scope); the brief still decides relevance from the filing text. Registrant manager tags are always kept on the card.
- `verified_primary_source` is set only when the item's URL host is on the feed's listed domain (e.g. `sec.gov`); the model cannot grant it. Cards carry `source_origin`: `issuer_filing` or `regulator` (absent = news).
- Evidence for a filing: the index page, then the EX-99 press release if present, else the form itself; SEC cover-page boilerplate is trimmed before the 2,500-character cap.
- Primary candidates are ordered before news so the 30-item cap never drops a filing for its syndicated copies.
- SEC fair-access: requests to sec.gov declare `FundCoverageNews/1.0 <contact>`; the contact comes from `SEC_CONTACT_EMAIL` (a GitHub Actions secret, or `.env`/shell locally) and is never committed. Unset: SEC feeds are skipped and listed in `feeds_skipped`; the refresh does not fail.

## ASIC sitemap

`lastmod` is a modification time, not publication: ASIC re-touches old releases. Candidates are labelled `published_basis: sitemap_lastmod`; the page's `dcterms.date.created` replaces it (`page_created_date`). A release created before the lookback window is skipped before any model call, counted in `stale_skipped` and remembered in seen.json. If the page cannot be read, the lastmod label stays on the card.

## GDELT

- Discovery only: a GDELT hit is a real URL to retrieve, not evidence in itself. `published_at` on such cards is GDELT's first-sighting time and is labelled `published_basis: gdelt_seen`; the page's own date, when readable, is `source_published_at`.
- When GDELT and Google News carry the same headline, the Google News item (opaque link) is dropped before briefing, so no duplicate is paid for.
- GDELT tolerates little traffic: at least 10 s between its calls, one retry after 15 s on a rate limit, then the query is recorded in `feeds_failed` and the refresh continues. On 25 Sep, repeated manual test calls triggered penalty windows lasting minutes; GitHub-hosted runners share addresses, so some scheduled runs may see GDELT fail. Verification on 25 Sep: one dry run returned GDELT articles with real URLs (e.g. AFR, investinglive); other attempts, including after a 150 s cool-down, returned HTTP 429, and one managers-query reply was non-JSON (its text is now logged). Treat GDELT as best-effort until scheduled-run logs show its success rate. Its titles are de-tokenised (`$2 . 5` -> `$2.5`).

## Setup and rollback

Add repository secret `SEC_CONTACT_EMAIL` (Settings → Secrets and variables → Actions). The workflow passes it to the refresh step.

Rollback: revert the source-tier commits; no stored data depends on it. Cards already created from filings remain valid ordinary cards.
