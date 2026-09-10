# ADR 0001 — Local editorial prototype

Date: 2026-09-10

Status: Accepted for Phase 1 specification preparation under the handover; Phase 2 implementation remains future work.

Context: An internal alternatives-news demo needs investment selection quality before web infrastructure. Existing repository is a starter. The user explicitly requested architectural challenge and Phase 1 only.

Decision: Maintain a small JSON ontology and Markdown rulebook. Recommend Python + JSONL + CSV and at most two normal structured LLM stages for Phase 2. Publish only analyst-approved events. Keep geography outside intrinsic scoring. Preserve entity identities and type each relationship.

Alternatives considered: Immediate hosted PostgreSQL/Next.js would add setup and schema commitments before the editorial object stabilizes. SQLite is a reasonable later local convenience, but unnecessary for the first labelled sample. Embeddings and agent orchestration lack a demonstrated unmet need. YAML would be readable but adds a parser dependency; JSON has standard-library validation and explicit notes fields.

Consequences: Manual curation and review limit throughput deliberately. Local files are sufficient for a reproducible experiment. A future shared dashboard may need different storage/access controls. Detailed stage decisions and migration triggers are in [architecture-review.md](../architecture-review.md).
