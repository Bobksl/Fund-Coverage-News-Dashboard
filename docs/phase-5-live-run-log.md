# Phase 5 live-run log — Stage 1 & 2, DeepSeek

Started 2026-09-12/13. Provider and spending cap were supplied by the user directly in chat, not
committed anywhere; the credential itself is never recorded in this repository, this document, or
any run artifact (`work/` is git-ignored and the key lives only in a local, git-ignored `.env`).

**Provider/model:** DeepSeek, `deepseek-flash` (confirmed against current API docs at
implementation time; the user's originally-named `deepseek-v4.1-flash` is not a live model ID —
`deepseek-v4-flash` is a retired legacy alias, `deepseek-flash` is the current fast/economical
tier). **Spending cap:** ¥6.59 CNY (~US$0.93), authorized by the user for this run.

## Stage 1 — provider contract smoke (synthetic only, no network, no spend)

`tests/test_deepseek_provider.py`, 8 tests against an injected fake HTTP opener: success/usage
capture, header/body correctness, transport retry and exhaustion, HTTP error body capture,
malformed responses (missing `choices`, missing `usage`). All pass. No network call, no credential
read. This satisfies Phase 5 handover section 9 Stage 1 before any billed call.

One additional manual connectivity check (a single ~20-token call, cost negligible, not part of
any frozen run) confirmed the credential and endpoint work and revealed that `deepseek-flash` is a
**reasoning model**: its response includes a `reasoning_content` field alongside `content`, both
billed against the same `max_tokens` budget. This directly informed the token-budget issue found
in run v1 below.

## Stage 2 — calibration smoke, run v1 (failed: token budget)

**Run ID:** `calib-smoke-deepseek-flash-v1`. **Manifest:** `work/phase2/calibration-smoke/
manifest.json` (9 articles, frozen before any model output existed — see
`docs/phase-5-review-decisions.md`). **Freeze verified:** yes, against
`work/phase2/freeze-001/freeze-record.json` (`evidence_sha256` recomputed and matched). **Prompt
version:** `p1`. **Settings:** `max_output_tokens=2048` (the adapter's untouched default).

**Result:** 9/9 `review_required`. 0 provider transport failures. Usage: 138,488 input tokens,
36,864 output tokens across 18 calls (9 articles × 2 attempts) — exactly `2048 × 18`, meaning
**every single attempt hit the token cap**.

**Diagnosis:** inspected the raw saved output directly
(`work/phase2/live-runs/calib-smoke-deepseek-flash-v1/raw-outputs/`): every response was valid
JSON syntax up to the point of truncation, then cut off mid-string. Combined with the Stage-1
connectivity check's discovery of `reasoning_content`, this is a token-budget problem, not a
schema or model-quality problem: `deepseek-flash`'s internal reasoning for a large classification
prompt consumes most or all of a 2048-token completion budget, leaving no room for the visible
JSON. This is an infrastructure/settings defect, not a specification defect — it does not consume
the calibration one-repair allowance.

Separately, while fixing this, found and fixed a real bug: `tools/run_model_experiment.py`'s
`run_experiment` computed `settings_overrides` (from `--temperature`/`--top-p`/
`--max-output-tokens`) for **metadata/hashing only** and never actually passed them to
`build_provider()` — so no matter what settings a caller specified, the provider silently used its
hardcoded constructor defaults. Fixed in commit `e6a1fd2`, with a regression test
(`tests/test_run_model_experiment.py::ProviderKwargsTests`).

## Stage 2 — calibration smoke, run v2 (schema-valid, but a real specification gap found)

**Run ID:** `calib-smoke-deepseek-flash-v2`. Same manifest/freeze/prompt version (`p1`).
**Settings:** `max_output_tokens=8192`.

**Result:** still 9/9 `review_required`, but now for a different, more informative reason. Usage:
130,859 input / 109,404 output tokens. 6 of 9 articles produced valid JSON on at least one attempt
(3 remained truncated/empty even at 8192 — reasoning length is evidently variable and sometimes
still exceeds this budget; treated as a continuing infra tuning question, addressed by raising the
budget again for v3, not by the one-repair allowance).

**Finding (validated by direct inspection of every parsed attempt against
`tools.classifier._validate_output`):** in every one of the 6 schema-checkable responses, one or
more `evidence_refs` values were the literal string `"title"`, `"body"`, or a quoted excerpt of
the cited text — never the `article_id` the schema actually requires. Examples pulled directly
from the raw saved outputs: `"evidence_refs": ["body"]`;
`"evidence_refs": ["title: 'Apollo to Present at the Barclays 24th Annual Global Financial
Services Conference'"]`; `"evidence_refs": ["KKR To Sell Minority Stake In Nordic Bioscience To
Founder Claus Christiansen"]`.

**Adjudication against the one-repair policy (`docs/phase-5-review-decisions.md`):**
- *Pattern, not one article:* present in 8 of 9 articles' non-crashed attempts (every one that
  produced parseable JSON).
- *Specification-versus-model diagnosis:* checked `PROMPT_RULES` and `RESPONSE_CONTRACT` as they
  stood at prompt version `p1` — **neither ever stated the required `evidence_refs` format**. A
  model given a field named `evidence_refs` with no stated format is not unreasonable to guess
  `"title"`/`"body"`/a quoted excerpt; this is an omitted instruction, not a reasoning failure
  against a clear instruction.
- *Qualifies under the trigger:* "an omitted required editorial rule ... producing the repeated
  pattern," confirmed against ≥2 distinct articles (8 of 9, in fact).

**Repair applied (the one allowed):** added one explicit rule to `PROMPT_RULES` and one shared
`EVIDENCE_REFS_SPEC` string embedded at every `evidence_refs` field in `RESPONSE_CONTRACT`
(components, `entity_matches`, `sector_readthrough`): *"Every evidence_refs value ... MUST be
exactly the evidence's article_id string ... Never use the literal word 'title' or 'body', never
quote the cited text itself."* Prompt version incremented `p1` → `p2`
(`tools/run_model_experiment.py:DEFAULT_PROMPT_VERSION`); response-contract version incremented
`rc3` → `rc4`. No article IDs, gold facts, or case-specific exceptions entered the prompt — the
rule is fully generic. No labels, scoring thresholds, ontology, provider, model or sampling
settings were changed under this allowance (the separate `max_output_tokens` increase is
infrastructure, adjudicated above as not part of this repair).

**Synthetic verification before rerun:**
`tests/test_classifier.py::PromptContextTests::test_prompt_states_the_evidence_refs_format_explicitly`
confirms the new rule text and contract both state the requirement. Full suite: 343 tests pass,
`validate_spec` clean, `git diff --check` clean.

**Per-run token/cost accounting (v1 + v2 combined, no cost yet incurred beyond these two runs):**
input 269,347 tokens, output 146,268 tokens. At DeepSeek's published peak, cache-miss rates for
`deepseek-flash` ($0.30/M input, $1.20/M output — the conservative upper bound; off-peak is 20x
cheaper on cache-hit input), that is approximately **$0.26 (~¥1.85)** of the ¥6.59 cap, leaving
ample budget for a v3 rerun.

## Next: run v3 (post-repair, frozen)

Per the repair policy's execution rule: rerun the entire unchanged 9-article smoke set once under
a new immutable run ID, at `max_output_tokens=16384` (the infra increase) and `prompt_version=p2`
(the repair), preserving all v1/v2 outputs untouched. No second repair is permitted regardless of
v3's outcome — v3's prompt/schema/model/settings become the frozen configuration for the full
calibration partition and historical-holdout runs afterward (Phase 5 handover section 9 Stages 3–4),
whether or not this smoke batch itself meets any bar (it is a smoke test, not the evaluated run).

`calibration_prompt_repair`: **used once**, as documented above. No second repair remains
available for this experiment.
