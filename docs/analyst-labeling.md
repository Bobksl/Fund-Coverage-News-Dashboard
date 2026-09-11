# Analyst labeling instructions

Use the article-only packet and original public sources. All tracked entities are monitoring-only. Apply the [editorial rulebook](editorial-rulebook.md) independently. No prefilled decisions or suggested event groups are supplied.

Fill the blank CSV columns:

| Column | Human entry |
|---|---|
| article_id | Keep the supplied opaque identifier unchanged. |
| analyst_id | Your initials or an internal identifier. |
| decision | publish, reserve, reject or review. Publish means you would select this event for the intended concise edition, not merely that it is eligible. |
| relevance_level | A, B, C, outside or uncertain, based on your reading. |
| materiality_tier | high, medium, low or uncertain; explain in rationale. |
| event_group_id | Assign your own ID. Reuse it only for evidence of the same event. Distinct material updates can have distinct IDs; describe related prior events in rationale. These IDs remain hidden evaluation ground truth. |
| entity_roles | Your observed entities and roles, or none/uncertain. No holdings should be inferred. |
| must_not_miss | yes or no; explain any critical case. |
| rationale | Brief reasons and source passage/section supporting your judgement. |
| evidence_access | full, partial or inaccessible. Use review when evidence is insufficient. |
| reviewed_on | YYYY-MM-DD. |

Judge publication at event level: articles describing the same event should share its publication judgement even if one is a duplicate source. Record article-level evidence weaknesses in rationale. This allows the evaluator to count one publish-worthy event without labelling an otherwise useful duplicate as an unrelated negative.

Leave unresolved cases visibly unresolved. Do not invent a decision to complete the sheet. A second reviewer should label independently before adjudication; preserve both original files and disagreements. Do not inspect challenge selection metadata or model outputs.

The custodian freezes a versioned copy of completed/adjudicated labels with its SHA-256 hash, analyst identity and timestamp, alongside the evidence and split manifest. Check article-ID completeness, unresolved cases and independent publish-worthy event counts before authorizing inference. Keep these files separate from pipeline inputs. No model inference is permitted until this freeze is complete; a later change creates a new label version and is never retroactively credited to earlier predictions.
