# Fund Coverage News Dashboard

Local prototype for a watchlist-first alternatives-news demo. The repository now contains the ontology, a measured deterministic filtering baseline and a static browser demo. Phase 2 closed with a baseline FAIL; structured LLM classification and bilingual drafting remain untested. Phase 3 delivered a mechanics demonstration rather than an ingestion pilot. See the [Phase 4 review and plan](docs/phase-4-plan.md), [new Claude handover](docs/handover-claude-phase-4.md), and [Git diagnosis](docs/git-diagnosis-2026-09-12.md).

## Start here

1. Read [architecture review](docs/architecture-review.md) for the simplified local-first approach and the prior-conversation retrieval limitation.
2. Read [editorial rulebook](docs/editorial-rulebook.md) for what qualifies, what does not, and how scoring/review work.
3. Review [entity findings and confirmed monitoring-only scope](docs/entity-research.md).
4. Use [Phase 2 experiment](docs/phase-2-experiment.md) and [current status](docs/phase-2-status.md) for the amended protocol and initial analyst packet.

## Files

| File | Purpose |
|---|---|
| [config/entities.json](config/entities.json) | 13 watchlist entries, 30 entity/platform records, typed relationships and ambiguity rules. |
| [config/sectors.json](config/sectors.json) | Eight monitored concepts with instruments, inclusion/exclusion and transmission. |
| [config/themes.json](config/themes.json) | Eleven core/conditional themes and their required causal channels. |
| [config/event_types.json](config/event_types.json) | Fifteen broad event types with subtypes; type alone never ensures relevance. |
| [config/scoring.json](config/scoring.json) | Six anchored components, gates, publication bands, overrides and separate geographic preferences. |
| [config/sources.json](config/sources.json) | 23 public primary-source references and scoped verification notes. |
| [docs/decision-record.md](docs/decision-record.md) | Minimum later article/event/decision audit contract. |
| [examples/editorial-cases.json](examples/editorial-cases.json) | Eighteen explicitly hypothetical editorial examples; not benchmark results. |
| [tools/validate_spec.py](tools/validate_spec.py) | Dependency-free static consistency check. |
| [tools/records.py](tools/records.py) | Evidence/decision contract, inference allowlist and atomic JSONL. |
| [tools/baseline.py](tools/baseline.py), [tools/classifier.py](tools/classifier.py) | Deterministic floor and structured-classifier adapter with replay. |
| [tools/grouping.py](tools/grouping.py), [tools/scoring.py](tools/scoring.py) | Predicted event clustering; gates, bands, ranking and the ranking ablation. |
| [tools/runner.py](tools/runner.py), [tools/evaluator.py](tools/evaluator.py), [tools/corpus.py](tools/corpus.py) | Pipeline orchestration, cohort-separated evaluation and corpus/split construction. |
| [tools/drafting.py](tools/drafting.py), [tools/stability.py](tools/stability.py) | Shortlist-only bilingual cards with parity QA; calibration-only stability reruns. |
| [docs/natural-feed-policy.md](docs/natural-feed-policy.md) | Predeclared collection roster, window and completeness rule. |
| [docs/phase-2-collection-status.md](docs/phase-2-collection-status.md) | Natural-feed run 1: counts per source, logged gaps and open decisions. |
| [tools/collection.py](tools/collection.py), [tools/build_natural_feed.py](tools/build_natural_feed.py) | Manual-collection bookkeeping and cohort assembly; no HTTP client. |
| [docs/phase-2-engineering.md](docs/phase-2-engineering.md) | What the pipeline does, how to run it and what it does not establish. |
| [docs/phase-3-entry-gate.md](docs/phase-3-entry-gate.md) | Why the ingestion pilot is blocked. |
| [docs/decisions/0001-local-editorial-prototype.md](docs/decisions/0001-local-editorial-prototype.md) | Architecture decision and alternatives considered. |
| [tasks/plan.md](tasks/plan.md), [tasks/todo.md](tasks/todo.md) | Work order and handover status. |
| [docs/verification.md](docs/verification.md) | What was checked and what remains untested. |

JSON is used instead of YAML to keep parser dependencies at zero. Notes are explicit fields. Use snake_case IDs, two-space JSON indentation, UTF-8 and explicit nulls for unknown facts. Do not use entity aliases as an unconditional publication keyword list.

## Verify

From the repository root, with Python 3.13 (the locally verified interpreter):

```powershell
python tools/validate_spec.py
python -m unittest discover -s tests -v
git diff --check
```

The validator checks JSON keys, versions, ID uniqueness/references, parent cycles, required entity fields, score anchors/totals/bands and the scored hypothetical examples. The unittest suite covers the pipeline with synthetic fixtures; its success does not establish model performance. A real deterministic baseline evaluation and browser UI now exist, but no live model run, scheduled ingestion or deployment has been completed. The Phase 4 review records remaining contract and freeze-enforcement limitations.

## Working boundaries

- Keep evidence and future analyst/model outputs in ignored `work/`; store credentials outside Git.
- This repository is currently public. Treat the watchlist as monitoring scope; never add actual positions, private mandate details or unlicensed article corpora to a public commit. A local copy inside OneDrive is not guaranteed to be machine-only storage.
- Keep model recommendation, analyst decision and publication status separate. Never claim private holdings or infer losses from a manager association.
- Preserve original evidence/labels and version changes. Verify entity relationships at historical event dates.
- Phase 2 uses manual public evidence and a small structured pipeline. Hosting, scheduled ingestion and unattended publication require later scope decisions.
- Source access/reuse permissions are assessed per source before ingestion. No paywall bypass or paid-data integration.

Specification version: 0.1.0. Publication timezone proposed as Asia/Hong_Kong; first Chinese locale proposed as Simplified Chinese. Both are explicit reversible defaults. The six scoring weights are a baseline to test, not measured optimal weights.
