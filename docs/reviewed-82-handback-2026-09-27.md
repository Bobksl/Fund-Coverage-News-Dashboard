# Reviewed 82 event handback — 27 September 2026

The 82 analyst rows in the local `work/needs-review-82-labels-2026-09-27.md` have been reconciled against the source archive. The analyst's later decision supersedes row 82: its Stocktwits article is dated 23 March and describes Q1 ADS requests of 11.2%, so it is excluded from September coverage and is not merged with the Q3 ADS event.

## Published projection

| Measure | Before this review | Reviewed projection |
|---|---:|---:|
| Archived source cards | 249 | 249 |
| Events in index | 172 | 160 |
| Visible events | 172 | 128 |
| Visible Useful | 84 | 106 |
| Visible Important | 6 | 9 |
| Visible Needs review | 82 | 13 |
| Analyst-excluded events retained in the index | 0 | 32 |

The 82 reviewed rows resolve to 50 included and 32 excluded decisions. Inclusion and exclusion are bound to the complete set of original card IDs and hashes in each event. A changed or newly added card invalidates that decision until reviewed again. All 249 cards remain in their original day files, each belongs to exactly one event, and every old event ID resolves to a survivor or alias. Excluded events remain in `events.json` for this preservation contract; the page omits them from its date and all-event views.

## Source decisions that change interpretation

- [KBRA's 17 August release](https://www.kbra.com/publications/yTtCyjsh/kbra-assigns-rating-to-blue-owl-technology-finance-corp-s-400-million-senior-unsecured-notes-due-2029) dates the OTF $400 million BBB/Stable note rating. Its September card is later coverage.
- [OTF's 5 August Q2 release](https://www.blueowltechnologyfinance.com/investors/sec-filings/all-sec-filings/content/0001747777-26-000027/exhibit991-otfxpressrelease.htm), [Pagaya's 16 September release](https://investor.pagaya.com/news-releases/news-release-details/pagaya-signs-auto-forward-flow-agreement-neuberger-specialty), and [Broadcom's 9 June release](https://investors.broadcom.com/news-releases/news-release-details/broadcom-apollo-and-blackstone-establish-landmark-strategic) support their date corrections. The June Apollo/Blackstone item is excluded as stale September coverage.
- [ASIC's 22 September speech](https://www.asic.gov.au/about-asic/news-centre/speeches/the-case-for-private-credit-standards-if-not-why-not) explicitly says private credit practices are an enforcement priority and multiple investigations are underway. The ASIC warning is Important; the separate Remara action remains related rather than merged.
- [OBDC's Loparex marks discussed with filing links here](https://newsletter.cobaltintelligence.com/p/blue-owl-marks-loparex-at-5-cents) support Important severity. The published text says further loss **could** occur: the $133 million of second-lien principal was marked around five cents on the dollar as of 30 June, while eventual recovery under September's recapitalization was not established.
- [The Lincoln 13D/A filing mirror](https://archive.fast-edgar.com/20260921/A222A22FZZ2R62ZU22ZQ2WYM2FRQYZ22Z28Q/) identifies 72.21% of **Class I shares**, beneficially attributed to Lincoln Financial Investments as adviser. The published headline and brief specify that share class; the evidence strength is reported because the direct SEC page was not retrieved.
- [The data-center borrower report](https://www.briefs.co/news/blue-owl-backed-data-center-borrower-lands-1-1-billion-with/) identifies a Blue Owl-backed developer as the $1.1 billion junk-bond issuer. Both historical cards now use that attribution. [Reuters' Oracle/Project Jupiter report](https://www.marketscreener.com/news/oracle-blue-owl-project-delay-sends-ripples-through-ai-financing-sources-say-ce785adfd881f521) reports a delay while quoting Blue Owl that financial commitments remain unchanged.
- Finimize's secondary-market bid discount is Useful, not a fund NAV write-down. The previous audit's lead for row 23 pointed to a Fitch rating for **Blue Owl Capital Corporation II**, a different entity; the [matching KBRA OBDC affirmation](https://www.kbra.com/publications/tFhWnxLm/kbra-affirms-ratings-for-blue-owl-capital-corporation) supports the OBDC item.

The remaining 13 visible Needs review events are the analyst's explicit evidence-limited labels. No headline-only item was promoted. Manual source review kept short quoted spans under ignored `work/`; `public/` contains summaries, evidence hashes and quote offsets, with no publisher article body. The manual evidence URL and method are attached to each relevant backfill entry. The 19 earlier paid DeepSeek calls were bounded; their exact CNY charge is unavailable from the API usage data, and no further model calls were needed for the final source checks.

## Checks and limit

The local candidate was verified before replacing `public/data/backfill.json` and `public/data/events.json`: every archived day file matched byte-for-byte, all 249 card IDs appeared exactly once, all former IDs resolved, all 82 analyst rows matched their final scope and priority, and every backfill entry matched the original card hash. All Important priority sources had quote references. Focused Python checks passed (30 passed, one deselected); `node --check public/app.js` and a Node projection of the actual archive passed, including exclusion in every day view and All dates. The Playwright browser suite could not start on this Windows host because Python's subprocess pipe creation raised `PermissionError`; live browser rendering was not verified in this run.
