# Minimum decision record for Phase 2

This is a data contract for the local prototype, not a database/API design. Use UTF-8 JSONL, one immutable decision attempt per line; use stable string IDs and explicit nulls for unknowns. Nested data stays in JSONL; CSV exports flatten selected fields for review. Use UTC ISO timestamps with offsets and ISO dates; amounts keep number, currency, unit and basis separately. Reject duplicate JSON keys, non-finite numbers and unknown enum values. Phase 2 is monitoring-only by user confirmation on 2026-09-11.

## Evaluation boundary

Keep analyst publish labels, gold event-group IDs, must-not-miss flags, rationale, cohort selection reasons and split-quality metadata in evaluator-only files. None may be a baseline, model, grouping, ranking or drafting input. The pipeline proposes its own clusters. Split construction may use gold groups privately, but exports article IDs only. Freeze predictions before evaluation joins them to ground truth. Natural-feed and challenge results are separate; eligible A/B/C records do not necessarily count as publish-worthy positives.

## Article/evidence record

| Field | Requirement |
|---|---|
| article_id | Stable local ID; canonical URL/content hashes support deduplication but do not replace the ID. |
| original_url, canonical_url | Preserve supplied URL; remove only known tracking parameters when canonicalizing. |
| publisher, originating_publisher, discovery_method | Separate discovery engine and syndication distributor from original evidence source. |
| source_kind | `filing`, `regulatory_record`, `issuer_release`, `ratings_analysis`, `independent_reporting`, `discovery_only`, `other`. |
| published_at, published_date_precision | Known timestamp/offset or null; date-only evidence must not acquire an invented publication time. |
| event_date, first_seen_at, retrieved_at | Nullable event date, immutable discovery time and actual retrieval time. |
| access_status | `accessible`, `partial`, `unavailable`; failure detail stays separate from editorial outcome. |
| evidence_scope | `full_text`, `primary_excerpt`, `metadata_only`; declare exactly what was examined. |
| evidence_hash, evidence_local_ref | Hash the actual input available to the classifier. Store permitted excerpts privately under work/, not copied article corpora in Git. |
| claims | Stable claim IDs, concise factual statement, article ID and evidence span/locator; numeric claim also carries amount/unit/basis/period. |
| supersedes_article_id | Nullable; distinguish publisher corrections from silently changing evidence. |

## Event/decision record

| Field | Requirement |
|---|---|
| event_id, revision, decision_id, run_id, attempt | Stable event ID; append a revision for updates. Separate transport retries from new decisions. |
| article_ids, claim_ids | Evidence packet membership. Include all sources used, not only the prettiest URL. |
| event_identity | Parties, roles, vehicle/asset/deal identifier, action, subtype, event date and reporting period; unknowns explicit. |
| direct_entity_ids, propagated_entity_ids | Canonical ontology IDs; preserve direct vehicle and parent tags separately. |
| entity_matches | Matched text span, article ID, ER rule, candidate entity, resolved/ambiguous status and relationship path. |
| held_status | Phase 2: exactly `monitored`. No confirmed-held override or private exposure overlay is used. A future phase would require a separate scope decision. |
| asset_classes | Any of `venture_capital`, `real_estate`, `private_equity`, `private_credit`; no automatic VC/PE allocation from software tag. |
| sector_ids, theme_ids, strategy, instruments | Canonical references where configured; preserve instrument specificity and multi-sector tags. |
| primary_event_type, subtype, secondary_event_types | IDs and subtype must be valid in event_types.json; unknown type enters review. |
| countries, primary_region, region_basis | Actual economic-impact geography with evidence; no inference from manager headquarters alone. |
| relevance_level, eligibility_reason, transmission | A/B/C or null; observed trigger, mechanism, affected investment outcome and uncertainty. |
| gates | Explicit evidence, identity, relevance, materiality, transmission, novelty outcomes: `pass`, `fail`, `review_required`, `not_evaluated`. |
| components | Six named anchor scores, each with reason and claim/rule references. Null only if unscorable; do not silently substitute zero. |
| total_score | Deterministically summed integer when all six are scored; otherwise null. |
| recommendation | `priority_shortlist`, `shortlist`, `reserve_manual_only`, `suppress`, `review_required`. |
| disposition_reason_codes | At least one: `no_relevance`, `routine_activity`, `insufficient_evidence`, `ambiguous_identity`, `conflicting_evidence`, `duplicate`, `no_new_fact`, `below_materiality`, `weak_transmission`, `below_band`, `capacity`, `shortlisted`, `critical_review`, `override_approved`, `draft_invalid`. |
| duplicate_of, update_of | Nullable IDs. Keep relationship reason; do not merge distinct deals merely sharing a manager. |
| model_metadata | Provider, exact model/snapshot, settings, prompt version/hash, input hash, raw output reference, token counts, actual cost basis and latency. No credentials. |
| spec_metadata | Ontology/rulebook/scoring versions plus actual file hashes, code commit when available; never record an invented commit. |
| analyst_review | Reviewer identifier, time, final label/reason, changed components, unresolved issues and override evidence. Append history; no overwrite of original prediction. |
| publication | `not_selected`, `pending_review`, `approved`, `published`, `corrected`; date/time and selection reason. The model cannot set published. |
| content | English and Chinese headline/summary/interpretation, claim references, canonical source URL, language QA result. |

The prototype may store the evidence, event and decision objects in three files rather than one nested object; stable IDs are sufficient. No normalized SQL schema is required now. A classification failure remains an operational failure, even if a human later rejects the article.

## Change and replay semantics

Freeze the complete evidence packet before each evaluation run. Hash every actual config and prompt input. A saved-output replay tests deterministic parsing/ranking; a new model run tests inference variation. Report them separately. Corrections append a decision and preserve prior labels, inputs and content. Do not rerun only failed holdout cases and call that the original result.

Ontology research sources in config/sources.json establish mappings, not claims about later articles. Historical tests must check a relationship existed at that time; current mapping evidence alone is insufficient. Keep a lightweight valid-at note on historical match evidence rather than building a temporal graph database now.
