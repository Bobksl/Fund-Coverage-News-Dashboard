# Phase 7 handover — back to Codex for the remaining pre-execution work and the run

Written 2026-09-13 against commit `9c53442` on `main` (pushed; `git status` clean, 382 tests
pass, `tools/validate_spec.py` reports zero errors, `git diff --check` clean). Read, in order:

1. `docs/phase-7-pre-execution-review.md` — your own audit. Decisions 1–3 still govern.
2. `docs/phase-7-scope.md` — the canonical frozen scope (P7-1). This replaces any "57/21" or
   "91 probes" wording elsewhere.
3. `docs/handover-phase-7-astra.md` — Phase 7's purpose, roles and out-of-scope list.

Do not re-derive what those establish. Verify the specific claims below against the code before
acting on them.

## Where things actually stand

- **P7-1 through P7-4 are implemented, tested and pushed.**
  - P7-2/P7-3/P7-4 landed in `0f3c1e6`.
  - P7-1 landed in `9c53442`: 188/56/30 = 274 hashed stage manifests, two recorded exclusions,
    and a replay-only 59-ID linked diagnostic.
- **PRE-EXECUTION GATE: BLOCKED.** One engineering gap remains (T1 below), and it was found while
  writing this handover. Beyond that, the only blocker is the user's explicit spending-cap
  approval (T3).
- `historical_model_comparison = not_run`
- `automated_selection_readiness = inconclusive_pending_fresh_temporal_validation`

## Remaining tasks, in order

### T1 — Wire the spend cap into the actual run command (BLOCKING, no spend)

**Finding.** P7-3 connected `tools/inference_budget.SpendLedger` to `DeepSeekProvider(budget=...)`,
and `tests/test_deepseek_provider.py` proves the reservation works when a ledger is supplied. But
`tools/run_model_experiment.py` never constructs one:

- `main()` has no ledger or cap argument.
- `build_provider()` receives only the settings kwargs.
- `budget=None` skips the ledger entirely (`test_no_budget_supplied_skips_ledger_entirely`).

So a live Stage A launched through today's CLI would enforce **no cap at all**. The run manifest
also writes `cost_basis: None` even when a rate card is known.

**Change (minimal):**
- Add a required ledger path and cap for any live DeepSeek run, e.g. `--spend-ledger PATH
  --cap-usd N`, plus explicit rate arguments matching `SpendLedger`'s.
- Refuse a live run that lacks them. Replay needs neither.
- Construct `SpendLedger` and pass it as `budget=`.
- Record the ledger's cap and rates as `cost_basis` in `run-manifest.json`.
- `BudgetStop` must end the run as an explicit incomplete stop. It must not be treated as a
  retryable transport failure, and it must not produce a silently partial "completed" run.
- Reuse one ledger file across Stage A, any repaired calibration rerun, Stage B/C and Stage D.
  The cap is for the whole Phase 7 authorization, not per stage.

**Synthetic tests:**
- A live CLI run without a ledger is refused before any provider exists.
- With a tiny cap, the next request is blocked and no HTTP call occurs.
- `BudgetStop` leaves an honest incomplete record.
- Replay with no ledger adds zero spend.
- `cost_basis` matches the ledger header.

**Not a prompt/schema change. No live smoke.**

### T2 — Registry `categories` key missing from `EVALUATOR_ONLY` (non-blocking hardening)

`tools/records.py:EVALUATOR_ONLY` has `challenge_category`, but the real challenge registry (and
`tools/challenge.py:REQUIRED_FIELDS`) stores probe categories under `categories`, which
`leakage_scan` does not flag.

- **Current risk is low.** No inference path reads registry rows, and `tools/phase7_scope.py`
  projects IDs only.
- **Check before adding the key:** `tools/select_calibration_smoke.py` also writes a `categories`
  field into smoke manifests. Confirm that no leakage-scanned inference path would start refusing
  a legitimate payload. If one would, choose the narrowest alternative.
- Add a regression test in `tests/test_records.py`.
- It is fine to do this before Stage A or as a separate commit. It must not change `p2`/`rc4` or
  freeze-001.

### T3 — Present the frozen run configuration and cap to the user; wait for an explicit yes

After T1 (and T2 if done) are committed and the full suite is green, give the user one message
containing:

- **Code commit** to be run.
- **Provider/model and effective settings**, as actually emitted by
  `DeepSeekProvider("deepseek-flash").inference_settings()` at `9c53442`:
  - `thinking={"type":"enabled"}`, `reasoning_effort="high"`, `top_p=1.0`
  - `max_output_tokens=16384`, `structured_output_mode="json_object"`
  - `timeout_seconds=60.0`, `transport_max_attempts=3`, schema `max_attempts=2`
  - `base_url=https://api.deepseek.com/chat/completions`
  - `system_prompt_sha256=bb28cdf1…aeba`
  - Re-emit these at the commit you will actually run; don't copy them from here.
- **Prompt and contract versions:** `p2` / `rc4`.
- **Scope:** the three stage manifests' `article_ids_sha256` and `file_sha256` from
  `work/phase2/phase7-scope/scope-record.json`, re-verified at that commit.
- **Cap and rates:** Decision 3's **recommended US$25 hard cap**, with the rate card rechecked on
  the day (peak/off-peak windows included). State that it is a recommendation. The user decides
  the number.
- **What the cap covers:** initial calibration, at most one full repaired calibration rerun,
  holdout once, and challenge once. It excludes drafting, tuning and the 91-probe registry.

Spend nothing until the user replies with explicit approval in chat. Their approval of one
number does not pre-authorize a top-up.

### T4 — Execute, only after T3 approval

Follow Decisions 1–2's sequence exactly:

1. **Stage A, calibration (188).** Run `stage-a-calibration.json`, partition `calibration`, with
   `--freeze work/phase2/freeze-001/freeze-record.json`, `--evidence-store
   work/phase2/evidence-store`, the approved ledger, and a new run directory. Use a raw store you
   will keep; Stage B/C should share it so the linked diagnostic can replay both. Preserve and
   freeze the complete prediction set (predictions hash in a **new** freeze-style record at a new
   path; never edit freeze-001) **before** any evaluator join.
2. **Evaluate calibration.** `tools/evaluator.py` refuses to run without a recorded
   predictions hash. Check its `--cohort`/`--split` handling and `require_freeze` yourself.
3. **Adjudicate the one repair** (Decision 2).
   - Only a demonstrated specification defect across ≥2 distinct events, or an
     article-independent structural counterexample, qualifies.
   - If used: make one minimal generic change, bump the version, add regressions, and rerun all
     188 under a new run identity with the **same** Stage A manifest. Never pool pre- and
     post-repair predictions.
   - If unused: record `phase7_calibration_prompt_repair = not_used`.
4. **Freeze final code, prompt, contract, config, provider and settings.** Nothing changes after
   this point.
5. **Stage B/C, holdout (56), once.** Run `stage-bc-holdout.json`, partition `holdout`. Freeze its
   predictions before the evaluator join. No repair after holdout outputs are generated or
   inspected.
6. **Stage D, challenge (30).** Run `stage-d-challenge.json`, partition `challenge`. It is
   diagnostic only and can never trigger tuning.
7. **Optional linked diagnostic (59).** Use `linked-diagnostic-replay-only.json` with `--replay`,
   the final config and the shared raw store. It costs zero and is reported separately, never
   pooled. The CLI refuses it without `--replay`. A replay miss surfaces as `review_required`,
   never as a live call.

**If the cap is reached at any point:** stop, record the run as incomplete, report, and never
top up silently.

**Report (per stage, never pooled):**
- article, event and selected counts
- precision, recall, must-not-miss coverage
- false merges/splits, review rate
- schema-invalid and transport outcomes
- all-call usage and latency, and calculated cost with its rate basis
- `historical_model_comparison = meets_bars / fails_bars / inconclusive` against
  precision ≥90%, recall ≥85%, must-not-miss 100%. An unsuccessful structural repair yields
  `inconclusive_structural_failure`. Undefined precision or incomplete evidence cannot pass.

## Constraints (unchanged — do not relitigate)

- No `tools.records.EVALUATOR_ONLY` field (labels, event groups, categories, selection reasons…)
  may reach anything the classifier or drafter reads.
- freeze-001 (`freeze-record.json`, `split-manifest.json`) and `work/phase2/phase7-scope/*` are
  immutable. `tools.phase7_scope.write_scope` refuses to overwrite. A different scope needs a new
  version at a new path, plus user approval.
- Scope is 274 inputs. Never run the 91-record registry; never restore the two exclusions.
- No provider or model change, and no settings change after holdout starts. A settings change
  before holdout needs a new run identity and a complete comparable calibration.
- Out of scope: drafting, a fresh temporal holdout, live collection, backend work, and scoring
  weights tuned to these results.
- Never print or commit `DEEPSEEK_API_KEY` or `.env`. Outputs stay under git-ignored `work/`.

## Environment notes

- Test command: `python -m unittest discover -s tests -v`. Adding `-t .` fails, because `tests/`
  has no `__init__.py`.
- Test temp directories live under `work/test-workspace/` (fixtures), because sandbox temp dirs
  were unreliable on this machine.
- The `LF will be replaced by CRLF` warnings on `git add` are benign.

## Definition of done for this handover

- **T1** committed with tests, and T2 committed or explicitly deferred. Full suite,
  `validate_spec` and `git diff --check` clean.
- **T3** message sent, and an explicit user approval (or refusal) recorded.
- **T4** either completed with the per-stage reports and dispositions above, or stopped honestly
  (cap, structural failure, refusal) with the reason recorded.
- State the gate plainly at each step: **BLOCKED** (name the item) or **READY**.
