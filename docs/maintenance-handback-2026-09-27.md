# Maintenance handback — 27 September 2026 (Sunday evening HKT)

**Next action:** after Monday 28 September 08:00 HKT, check that scheduled run (section 1). Then send the analyst the ranking sample (section 3).

## 1. Refresh health

The first scheduled run after PR #11 has **not happened yet** (next: Monday 08:00 HKT). Latest evidence instead:

1. **Feeds:** the last main run, #29 (manual, 26 Sep, succeeded), reported 49 feeds ok and 3 failed. The failing feed names are only in the Actions log, which was not readable without sign-in. A local no-write dry run on 27 Sep (no model calls, SEC skipped without a local contact) gave 37 ok and 2 failed: `google_news_17` (TLS timeout, likely transient) and `gdelt_managers` ("query was too short or too long"). GDELT's sector query succeeded. Retests were then rate-limited (HTTP 429), so the cause of the managers-query error is unconfirmed.
2. **SEC/regulator/wire items:** none among the 21 cards added on 26 Sep. That is no new item, not a failed feed: run #29 had only 3 failures.
3. **Evidence:** 1 excerpt (Alternative Credit Investor); 20 headline-only (Google News).
4. **Routine flags:** 0 of 21.
5. **Model calls / spend:** the run's call count is in the Actions log only. It is bounded by the candidates briefed (30 in side-branch run #27, recovered by PR #7; 2 in run #29). This matches the earlier estimate of about CNY 0.05 per day on `deepseek-flash`. No paid calls were made today.

**Live site:** `events.json`, `status.json`, `index.json`, `app.js` and `index.html` served by GitHub Pages match `origin/main` byte-for-byte after normalising line endings. Run #32 (PR #11 deploy) succeeded.

## 2. Residual evidence (13 visible Needs review)

- None is flagged potential-urgent. All 13 are Google-News-only, and the 82-review handback records them as the analyst's deliberate evidence-limited labels.
- Brave search had already covered all 13 on 26 Sep (the key is present in ignored `.env`, value not printed). No new searches were made.
- Candidate URLs exist for 5 events on 4 pages: two PitchBook pages (access denied), AFR Bathla (unreadable) and TradingView/Reuters roundup (unreadable). No readable source was found, so nothing was promoted.
- A direct Brave resolver would not help: the gap is page access, not discovery. No change to `tools/backfill.py`.
- The 8 events without candidates stay Needs review. Track new Google-News-only Important-looking misses for a week from 28 Sep.

## 3. Same-class ranking sample for the analyst

The accepted order is unchanged. For each pair, say which should rank higher and why, with a source passage. Also say whether a **field label** or the **rule** is wrong. The pilot preferences (`03 > 05 > 02`, C08) are challenge cases, not authority.

**Important (all 9 are substantial / monitor / reported).** The order is therefore direct before sector, then newest first:
1 Loparex (direct) · 2 Cox tender for BCRED/HPS · 3 ASIC enforcement warning · 4 ABL capacity · 5 record 6.3% default rate · 6 CRE CLO distress 28% · 7 KBRA BDC non-accruals · 8 Bathla collapse · 9 CMBS office distress.
Question: should ASIC (3) or the default-rate record (5) outrank a tender offer (2)?

**Useful pairs (106 events, heavy ties):**

| Pair | Higher now | Lower now | Tests |
|---|---|---|---|
| A | #10 Kotak Alts ₹5,000 cr fund close (direct, primary) | #115 KBRA BBB rating of OTF $400M notes (direct, primary, **routine**) | top vs bottom; is a rating "routine"? |
| B | #15 Oracle notice delays Blue Owl Project Jupiter (direct, reported) | #43 BCRED/HPS secondary bids 12.5–17.5% below NAV (sector, reported) | direct vs sector |
| C | #12 KKR 8-K after $250M settlement report (primary, 27 Aug) | #15 Oracle / Project Jupiter (reported, 24 Sep) | primary vs reported, older vs newer |
| D | #43 BCRED/HPS secondary bids (sector, 25 Sep) | #107 Janus Henderson AAA CLO ETF $30bn (sector, 13 Aug) | newer vs older, same fields |
| E | #42 OTF Q2 NAV $16.48 (direct, reported) | #108 MCO growth financing from Accel-KKR (indirect) | direct vs indirect |

Record disagreements outside `public/`. A rule change needs your written approval and a version bump.

## 4. Presentation and tags

- **Changed:** the card badge. On an auto-selected card whose whole event carries a hash-bound analyst inclusion, it now reads "Auto-selected · event reviewed" / "自动筛选 · 事件已审核". Other auto-selected cards keep "Auto-selected · not yet reviewed". The card itself is still never called human-approved. A browser test covers both languages. This changes the badge on 40 of the 44 visible reviewed-include events (the other 4 display a human-reviewed card).
- **Proposal only (needs your policy decision):** add a `gp_roles` sidecar (`config/gp_roles.json`, keyed by card ID and hash) recording each tagged manager's source-backed role: lender/manager, equity-only, advisor or mention. The display would demote equity-only or mention tags to a secondary line rather than removing them. Example: Apollo/Kelvion equity involvement. Removing tracked-manager tags affects the F11 equity-only decision; nothing was changed.
- **Approve/group button:** design only. Such a button needs an authenticated write path, for example a GitHub-issue or PR draft generated by the page and validated and committed by a maintainer with hash checks. Not built.

## 5. Source gaps

- **FCA:** `robots.txt` and the news RSS both return 403 to an identified automated client. Not usable without bypassing that protection.
- **NAIC:** `robots.txt` loads (no sitemap listed), but the newsroom, `rss.xml` and `sitemap.xml` return 403. Not usable.
- **Business Wire, 10-Q/10-K and paid press:** unchanged. Each still needs, respectively, a usable feed code, your NAV/NII threshold, or measured coverage counts.
- **A15/Jefferies correction** and **Chinese report v3:** not done. They wait for your request and analyst approval; v2 stays live.

## 6. File deletion candidates (nothing deleted)

| Path | Tracked? | Why it may be redundant | References | Unique evidence lost? |
|---|---|---|---|---|
| `docs/handover-codex-from-claude-dashboard-reports.md` | tracked | superseded handover | none | no; history is in git |
| `docs/handover-claude-dashboard-extension.md` | tracked | superseded handover | 3 docs link to it | no; links would break |
| `docs/handover-claude-inline-pdf.md`, `docs/handover-claude-sunday-accuracy.md` | tracked | done work | plan.md, todo.md, 2 docs | no; links would break |
| `docs/handover-chatgpt-final-review.md` | tracked | review done | todo.md | no |
| `docs/architecture-review.md` | tracked | old review | none | possibly; review first |
| `.pytest_cache/`, `.ruff_cache/`, `tests/__pycache__/`, `tools/__pycache__/`, `work/__pycache__/` | ignored | regenerable caches (~2.4 MB) | none | no |
| `work/release-temp-20260927/`, `work/test-tmp/`, empty `work/pytest-*` and `work/release-pytest-20260927/` | ignored | leftover test temp dirs | `test-tmp` is recreated by a test | no; you asked to keep `work/` |

Keep: the audit and acceptance records, report PDFs, day files, `site/` (archived research UI, referenced by README), `work/evidence-cache`, `work/site-cache` (used by `tools/build_site.py`), `work/phase4-history-backup.bundle` and `.claude/`.

## 7. Branch cleanup (fetched 27 Sep; 0 open PRs, 11 closed)

| Branch | Action | Proof |
|---|---|---|
| local `claude/{acceptance-fixes,backfill,gdelt-backfill,handover,primary-sources,sunday-accuracy}`, `codex/{date-selector-count,reviewed-82-events,verified-priority-backfill}` | deleted with `git branch -d` | each tip is an ancestor of `origin/main` |
| remote `claude/acceptance-fixes` (#4), `claude/backfill` (#5/#7), `claude/gdelt-backfill` (#6), `claude/handover` (#8), `claude/primary-sources` (#3), `codex/date-selector-count` (#11), `codex/reviewed-82-events` (#10), `codex/verified-priority-backfill` (#9, merge `d0752a0` second parent = `889e246`) | deleted with `git push --delete` | exact `ls-remote` SHA verified as merged; merged PR named |
| `codex/news-events-priority` (local `c616729`, remote `514897c`) | kept | `c616729` is on main's first-parent history (pushed directly, run #18), so the "ahead 1" commit is accounted for. `-d` refused because its upstream lacks it, and the remote has no PR record. Safe to delete later by hand. |
| `codex/update-claude-handover` (`7dbf4ca`, unpushed) | kept | its only commit is cherry-picked into this PR; delete after merge |
| `archive/research-log` | kept | archive/recovery branch by name |
| `main` | fast-forwarded to `849fb78` | — |
