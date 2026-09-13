# Phase 7 spend-cap wiring completion

2026-09-13. T1 and T2 implemented against main after 32b5d7b.

Live DeepSeek CLI runs require a shared spend-ledger path, an explicitly approved
USD cap, and input/output rates per million tokens. The runner passes that ledger
to the provider and records its exact header as cost_basis, cumulative balances,
and the run's incremental conservative charge. Reuse the same ledger across all
authorized stages and any permitted full calibration rerun.

Each HTTP attempt reserves funds before sending, including transport retries.
Unknown billing retains its reservation. BudgetStop is not retryable: the run
records status=incomplete, completed article count and stop reason, preserves
article/raw artifacts, and does not emit a partial completed prediction set.
Replay requires no ledger and adds zero spend. Existing run manifests cannot be
overwritten; use a new run directory.

T2 adds registry categories to EVALUATOR_ONLY. The registry validator explicitly
permits its own required categories field; inference projections still exclude
it. Smoke-manifest categories do not enter inference payloads. No prompt,
response-contract, frozen scope or evidence changes were made; p2/rc4 remain.

Verification: 392 unittest tests pass, validate_spec reports zero errors, and
git diff --check passes. The full suite was run outside the filesystem sandbox
after sandbox-only temporary-directory cleanup PermissionErrors; tests were not
weakened. Synthetic regressions cover missing CLI budget/rates, zero-call cap
refusal, transport retry reservation, incomplete stop after a completed article,
ledger header consistency, refusal of cap changes, and zero-spend replay.

Official USD pricing rechecked on 2026-09-13:
https://api-docs.deepseek.com/quick_start/pricing/
deepseek-flash currently maps to DeepSeek-V4.1-Flash. Cache-miss input/output
rates per million tokens are USD 0.30/1.20 peak and 0.15/0.60 off-peak.
Peak hours are weekdays 01:00-04:00 and 06:00-10:00 UTC (09:00-12:00 and
14:00-18:00 Hong Kong); all other hours are off-peak.

PRE-EXECUTION GATE: BLOCKED — explicit user spending-cap approval pending.
The USD 25 whole-experiment cap remains a recommendation, not authorization.
No live inference was performed for this change. No top-up is pre-authorized.
historical_model_comparison = not_run
automated_selection_readiness = inconclusive_pending_fresh_temporal_validation
