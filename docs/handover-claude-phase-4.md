# Phase 4 handover for a new Claude agent

Copy the prompt below into the new agent. It supersedes the earlier Phase 3 task order.

---

You are taking over Junson Capital's internal Fund Coverage News Dashboard. Act as a pragmatic
senior Python/AI engineer and product partner. Implement Phase 4: an analyst-reviewed bilingual
local demo plus a separately reported, bounded structured-model experiment.

Workspace: `C:\Users\user\OneDrive - The University of Hong Kong - Connect\桌面\Projects\Fund-Coverage-News-Dashboard`.
Reviewed code HEAD was `15c11c7` on `codex/phase-1-editorial-spec`; inspect current Git state rather
than assuming it is unchanged. Other agents/users may have edited files: preserve their work.
Do not assume the old 'tomorrow night' handover deadline is current.

Read in order:
1. `docs/phase-4-plan.md` — current review, required fixes, implementation slices and acceptance.
2. `docs/phase-2-disposition.md` and `docs/demo-readme.md` — actual outcomes and limitations.
3. `docs/decision-record.md`, `docs/editorial-rulebook.md`, config files.
4. `tools/classifier.py`, `runner.py`, `evaluator.py`, `drafting.py`, `build_demo_feed.py`, `site/`.
5. `docs/git-diagnosis-2026-09-12.md` — Git connectivity findings.

Phase 2 is complete with a deterministic-baseline FAIL: natural holdout precision 75%, recall
14.3%, critical surfaced 1/2. Those counts and artifact hashes were independently reproduced.
219 tests passed outside the Windows sandbox. LLM classification/drafting remain untested.
Phase 3 delivered only a mechanics demo: 22 baseline shortlist candidates across partitions,
no real Chinese cards and no publication approval. Preserve this honest history.

Follow slices 4A-4D in the plan. First close the small correctness gaps: full compact editorial
context and response schema in the classifier; nested output validation; verified evidence/body
loading and freeze preflight; day-specific editions; safe DOM rendering and stable date navigation.
The current prompt does not contain the manager ontology or substantive scoring definitions.
Do not simply attach a provider and declare the integration complete. Level B sector-only relevance
already exists in the baseline; do not create an unconditional keyword publication rule.

Then connect ONE provider through the existing injected adapter, recording actual model ID,
parameters, prompt/config hashes, raw outputs and usage. Read current official provider docs at
implementation time; do not invent a model name from old handovers. Never read or expose credential
values in reports. If provider/model/spend authorization is missing, request only that essential
input and continue all independent engineering and offline replay work.

Use synthetic tests and a preselected 10-15-article calibration smoke run, at most one bounded
calibration prompt repair, then freeze before the full comparison. Inference must run in fresh
context containing only allowlisted source evidence and public editorial config. Do not give it
this conversation's gold labels, event IDs, rationales, challenge categories or evaluator files.
The old holdout is a historical comparison after disclosed diagnosis; fresh temporal data is
needed for a new sealed readiness claim. Do not recollect simply to make the demo work.

Build a claim-backed EN/ZH drafting path and a minimal local CSV/JSON approval ledger tied to the
exact card revision/hash. Analysts may curate a demo edition if the model is weak, but preserve
provenance and never credit their selections to the model. Benchmark publish labels are not card
approval. Export only explicitly approved revisions. If no approval arrives, finish review-ready
drafts and the UI without marking the publication/demo acceptance passed.

Extend the existing static page. It must open today's Hong Kong date, offer an explicit historical
edition shortcut, show EN/ZH, factual summary, separate 'Why it matters', entity/vehicle/sector/
geography/event tags, source links and honest empty/stale/error states. Six to ten is an upper
editorial preference, never a required minimum. No challenge records in the ordinary news feed.
Export UI plus approved JSON to an isolated ignored directory and serve only that directory on
127.0.0.1; never serve the whole repository or evaluator data.

Keep Python + files + vanilla HTML/JS. No Next.js, hosted database, cron, new accounts, vector
search, agents, paid news or paywall bypass. All watchlist entries are monitoring-only. Keep
freeze-001/run-001 immutable and keep all private artifacts under ignored work/. No force-add,
history rewrite, deletion of .git or remote push without explicit authorization.

Validate with the full unittest suite, spec validator and real browser checks. Add focused tests
for changed behavior, including malformed model payloads, evidence mutation, approval invalidation,
per-day capacity, challenge exclusion and hostile source strings. Do not weaken tests to bypass
Windows permissions. Record environment failures separately.

Finish with changed files, exact run commands, tested behavior, measured results and limitations,
remaining user input, and separate `reviewed_demo_ready` / `automated_selection_readiness`
dispositions. Do not call an untested model successful or erase the recorded baseline FAIL.
