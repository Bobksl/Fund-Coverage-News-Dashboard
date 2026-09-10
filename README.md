# Fund Coverage News Dashboard

Phase 1 specification for a watchlist-first alternatives-news demo. The objective is a small, useful daily selection of public events, with private-credit emphasis, evidence-linked summaries and investment interpretation. This repository currently contains an ontology and editorial specification, not a running news collector or website.

## Start here

1. Read [architecture review](docs/architecture-review.md) for the simplified local-first approach and the prior-conversation retrieval limitation.
2. Read [editorial rulebook](docs/editorial-rulebook.md) for what qualifies, what does not, and how scoring/review work.
3. Review [entity findings and two investment-team questions](docs/entity-research.md).
4. Use [Phase 2 experiment](docs/phase-2-experiment.md) as the next development brief.

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
| [docs/decisions/0001-local-editorial-prototype.md](docs/decisions/0001-local-editorial-prototype.md) | Architecture decision and alternatives considered. |
| [tasks/plan.md](tasks/plan.md), [tasks/todo.md](tasks/todo.md) | Work order and handover status. |
| [docs/verification.md](docs/verification.md) | What was checked and what remains untested. |

JSON is used instead of YAML to keep parser dependencies at zero. Notes are explicit fields. Use snake_case IDs, two-space JSON indentation, UTF-8 and explicit nulls for unknown facts. Do not use entity aliases as an unconditional publication keyword list.

## Verify

From the repository root, with Python 3.13 (the locally verified interpreter):

```powershell
python tools/validate_spec.py
git diff --check
```

The validator checks JSON keys, versions, ID uniqueness/references, parent cycles, required entity fields, score anchors/totals/bands and the scored hypothetical examples. It does not implement entity resolution, classification, a complete JSON Schema validator, an LLM pipeline or analyst evaluation. There is no application build/dev command or runtime test suite yet.

## Working boundaries

- Keep evidence and future analyst/model outputs in ignored `work/`; store credentials outside Git.
- This repository is currently public. Treat the watchlist as monitoring scope; never add actual positions, private mandate details or unlicensed article corpora to a public commit. A local copy inside OneDrive is not guaranteed to be machine-only storage.
- Keep model recommendation, analyst decision and publication status separate. Never claim private holdings or infer losses from a manager association.
- Preserve original evidence/labels and version changes. Verify entity relationships at historical event dates.
- Phase 2 uses manual public evidence and a small structured pipeline. Hosting, scheduled ingestion and unattended publication require later scope decisions.
- Source access/reuse permissions are assessed per source before ingestion. No paywall bypass or paid-data integration.

Specification version: 0.1.0. Publication timezone proposed as Asia/Hong_Kong; first Chinese locale proposed as Simplified Chinese. Both are explicit reversible defaults. The six scoring weights are a baseline to test, not measured optimal weights.
