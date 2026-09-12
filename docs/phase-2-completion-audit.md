# Phase 2 completion audit — 2026-09-11

Disposition: **incomplete; no inference authorized by the existing label-freeze protocol and no Phase 3 promotion evidence**.

Subsequent update: human labels have now been received for the 20 starter articles; the blank-label counts below are historical. See `docs/phase-2-status.md` and the private `work/phase2/evaluator/label-review-001/` review. Adjudication and evidence freeze remain outstanding, as do the larger corpus and empirical experiment.

The request to finish Phase 2 does not supply the independent human judgements required by the previously agreed protocol. Do not substitute Codex, Claude, synthetic fixtures or presumed labels for those judgements.

## Verified local state

The authoritative starter packet is `work/phase2/analyst-review-002/`. Read-back found 20 article records, 20 label rows, zero human decisions and zero human event-group IDs. Its JSONL SHA-256 matches the recorded digest. Packet 001 remains superseded. No other completed-label file or evidence/split freeze was found under `work/phase2/`.

These are title/link records, not a frozen full-text benchmark. No natural-feed or challenge-set performance result exists. Blank labels mean unknown publication-worthiness, not 20 rejected events. No article has been assigned a model recommendation.

## Outstanding work, in dependency order

1. Complete the corpus: predeclare the natural-feed source roster, consecutive collection window and completeness policy, then collect without editorial cherry-picking. Curate the challenge set separately. Approximately 120 records is a planning count; extend as the protocol requires, never to improve observed model results.
2. Capture permitted evidence and retrieval/access metadata. Provide an article-only review packet with no predicted tags, categories, scores, recommendations or event groups. Existing exploratory items can support calibration but cannot retroactively count as a natural census.
3. Obtain independent human labels and adjudication. Freeze evidence and labels before any model inference, including calibration. Gold event-group IDs remain exclusively evaluator-side.
4. Construct the separate holdouts using gold publish-worthy event counts (at least 20 distinct positive events per evaluable cohort under the current protocol). Prefer later publication dates; prevent event-lineage leakage and disclose temporal exceptions. Preserve natural prevalence.
5. Implement the simple local baseline, structured classifier adapter, decision validation, predicted event grouping, deterministic scoring/ranking, saved-output replay and evaluator. Only the article-packet builder exists today. Implementation with synthetic fixtures can proceed before human labels; actual benchmark inference cannot.
6. Run calibration and freeze the final specification/model/prompt/split before holdout inference. Save predictions before evaluation joins gold labels. Compare baseline, structured pipeline and ranking ablation separately for each cohort.
7. Complete the 20-card bilingual grounding/parity review, usefulness/timing observations, measured cost/latency and independent discovery-miss audit. Report the actual denominators, defects, abstentions and uncertainty.
8. Issue an evidence-backed pass, fail or inconclusive disposition. Only a satisfactory disposition supports the Phase 3 ingestion pilot under the existing plan.

No performance result or completion date is invented. The immediately required external input is independent human labeling; a file path can identify labels prepared elsewhere. The remaining engineering and corpus work is also unfinished, not merely awaiting a ceremonial sign-off.

## Claude allocation and handover

The retrieved “Recommended allocation by phase” in the referenced conversation assigns Phase 3 news ingestion to Claude Sonnet at medium effort, with Codex for difficult integration/debugging. It names “Claude Sonnet 5”; this records the conversation's wording, not a fresh claim about available Claude products. Select an available Claude coding model in the user's environment rather than inventing a model identifier.

Use [the Claude handover prompt](handover-claude-phase-3.md). It is prepared now, but explicitly conditional on Phase 2 completion. The revised local architecture takes precedence over the older eight-phase infrastructure proposal. No Claude task was launched and nothing was sent to another service.
