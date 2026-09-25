# Primary-source tier — 25 September 2026

Branch `claude/primary-sources` (on top of `claude/sunday-accuracy`). Config: `config/primary_sources.json`. Code: `tools/fetch_news.py` (feeds, EDGAR parsing, ordering), `tools/source_evidence.py` (SEC contact header, filing document choice, cover-page trimming).

## What the refresh reads now

| Tier (editorial rulebook) | Implemented | Not yet |
|---|---|---|
| Primary: SEC EDGAR / public BDC filings | 13 registrants' own EDGAR feeds (OCIC, OTIC, OBDC, OTF, OWL, ADS, MFIC, APO, K-FIT, FSK, KKR, BCSF, Lincoln Bain TCF). Forms: 8-K, 8-K/A, SC TO-I(/A), 424B2, 424B5, 13D(/A). | 10-Q/10-K (main documents exceed the 1 MB cap); 424B3 sticker supplements excluded as noise. |
| Primary: regulators | Fed, SEC press releases, ECB, Bank of England, ESMA official RSS; still subject to the keyword rule. | FCA (403 to automated clients), ASIC and NAIC (no official feed found). |
| Primary: GP / borrower IR, rating agencies | — | No open feeds; KBRA/Fitch releases arrive through Business Wire and news. |
| Secondary: wires, reputable press | Alternative Credit Investor and Commercial Observer RSS; bounded page retrieval. | Business Wire / PR Newswire / GlobeNewswire feeds. |
| Discovery | 26 Google News queries (headline-only: links are not decoded). | GDELT (returns real publisher URLs). |

## Rules

- A filing from a listed registrant skips the keyword rule (the registrant is a tracked vehicle and the form is in scope); the brief still decides relevance from the filing text. Registrant manager tags are always kept on the card.
- `verified_primary_source` is set only when the item's URL host is on the feed's listed domain (e.g. `sec.gov`); the model cannot grant it. Cards carry `source_origin`: `issuer_filing` or `regulator` (absent = news).
- Evidence for a filing: the index page, then the EX-99 press release if present, else the form itself; SEC cover-page boilerplate is trimmed before the 2,500-character cap.
- Primary candidates are ordered before news so the 30-item cap never drops a filing for its syndicated copies.
- SEC fair-access: requests to sec.gov declare `FundCoverageNews/1.0 <contact>`; the contact comes from `SEC_CONTACT_EMAIL` (a GitHub Actions secret, or `.env`/shell locally) and is never committed. Unset: SEC feeds are skipped and listed in `feeds_skipped`; the refresh does not fail.

## Setup and rollback

Add repository secret `SEC_CONTACT_EMAIL` (Settings → Secrets and variables → Actions). The workflow passes it to the refresh step.

Rollback: revert the primary-source commit; no stored data depends on it. Cards already created from filings remain valid ordinary cards.
