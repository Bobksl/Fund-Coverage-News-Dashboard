# Implemented news event contract — v1 schema, events-v2 grouping

Status: offline pipeline implemented on codex/news-events-priority. Frontend integration belongs to Claude; public/app.js and public/index.html are unchanged.

## Existing data preserved
index.json and per-day files retain their old schemas and raw counts. Existing raw card IDs and content are preserved. New cards may have additive metadata below.
events.json is a lossless projection; regenerate with:
    python -m tools.news_events --data-dir public/data
This command makes no network/model calls and writes only events.json. Normal site_data.write_index also regenerates it during refresh.

## events.json
Top level: schema_version=1, grouping_version=events-v2 (was events-v1), overlay_version, ranking_version=priority-v1, as_of (offset-aware timestamp), article_count, event_count, cards_sha256, events[].
cards_sha256 hashes sorted raw cards serialized with Python json.dumps(sort_keys=True, ensure_ascii=False). It fingerprints this snapshot; a frontend need not reimplement the serializer. Validate full source membership against the current archive instead.
Event fields:
- event_id: persistent identity recovered from prior membership, or a reviewed migration ID.
- member_card_ids: all raw article IDs; no source content deleted.
- representative_card_id: exact raw card to render, preserving its review_status.
- display_gps/display_sectors: filter/display tags; includes OTF->Blue Owl parent and prevents explicit Technology Income headlines from carrying OTF.
- sources[]: publisher, url, card_id, published_at.
- first_seen_at: legacy earliest publication proxy, not a proven crawl timestamp; timestamp_basis distinguishes published_at versus date_only. Date-only fallback is 00:00 HKT solely for stable sorting.
- last_material_update_at: initial event publication proxy; syndicated copies do not advance it. A source revision advances this only with explicit material_update_confirmed metadata; the model cannot grant this field.
- last_source_revision_at: later same-source changed-content observation, separate from proven material novelty.
- updated: source revision exists; display Source updated, not 'verified new event'.
- merge_rule: reviewed (hash-checked overlay decision), headline (identical source headline with a figure/quarter/month anchor within seven days), identity (validated exact subject/action/object/period plus matching numbers), source (same canonical URL + fingerprint), single (no established equivalence).
- aliases (additive, events-v2): former event IDs now served by this survivor. Every earlier event ID resolves to a live event_id or appears in exactly one aliases list; redirect old links through it.
- member_roles (additive): card_id -> reaction | update for non-default members; others are coverage. Coverage and reaction never advance last_material_update_at; a reviewed update can, at its (corrected) publication time.
- related_event_ids (additive): reviewed related-but-distinct events (same regulator/day, background, methods explainer). Never implies identity or shared priority.
- sources[].date_correction (additive, optional): {original, corrected, basis, evidence_url, event_date?, decision}. sources[].published_at then carries the corrected value; the raw card and its day file keep the original observation.
- timestamp_basis may also be corrected.
- priority: fields below. priority_rank: lower is earlier in globally sorted Priority.
- date_views: YYYY-MM-DD -> representative_card_id, member_card_ids, display_gps, display_sectors, further_coverage, priority, priority_rank. Use this exact representative for historical views, not the global representative. All dates retain their original coverage.

## Reviewed overlay (config/news_event_groups.json, version 2)
Processing order: evidence/date correction -> identity/relatedness -> novelty/material update -> relevance/priority -> recency tie-break.
groups[]: survivor event_id, members[{id, headline, card_sha256, role?}], optional representative_card_id, aliases, reason, decision, evidence_urls, history (earlier decisions). A group applies only while every present member still matches its headline and hash; one changed card invalidates the whole decision and its cards fall back to automatic rules. A card may appear in at most one group.
relations[]: {event_ids, reason, decision}; IDs may be survivors or aliases.
corrections[]: publication-date corrections keyed by card_id + card_sha256 + original value. Observation dates are never silently rewritten into publication dates.
Survivor rule: an existing reviewed ID, else the earliest-published member's prior event. Later same-headline repeats (anchored) join a reviewed event archive-wide.

## Source evidence (new cards)
evidence: {status, level, retrieved_at, sha256?, source_published_at?, final_url?}. status is ok | unresolved_aggregator | access_denied | blocked_address | invalid_url | too_large | unsupported_content | http_error | too_many_redirects | error | skipped_cap. level is excerpt only when retrieved page text actually replaced the feed line. Excerpts stay in work/evidence-cache/ (git-ignored, not deployed); cards never carry publisher text. source_published_at is the page's own publication time, separate from published_at (feed) and observed_at (refresh time). Google News links are not decoded, so most cards remain headline-only and Needs review.

## Priority
priority: urgent | important | useful | needs_review.
severity: critical | substantial | bounded | unknown.
time_sensitivity: 48h | 7d | monitor.
linkage: direct | sector | indirect | unknown.
evidence_strength: primary | reported | unknown.
reason: {en, zh}. potential_urgent: boolean (unverified triage hint, NOT an Urgent assessment). version and as_of identify rules/assessment time.
The engine sorts these categories lexicographically in the orders above, then newer last_material_update_at, then event_id. No six-component score. Scope filters and language changes must not recalculate importance.
Primary evidence requires separately verified input metadata; an AI declaration alone never grants it. Production feed inputs currently default to reported if assessable.
Important limitation: matching evidence spans verifies provenance/syntax, not semantic truth. No live brief-v2-priority call or analyst ranking validation has run.
Day priorities use day end HKT; global priorities use export as_of. No automatic age-based demotion or inferred cure/default resolution.

## New-card metadata
source_headline, source_fingerprint (hash of cleaned source title/text), observed_at, relevance_reason, assessment, event_identity, evidence, source_published_at, source_origin (issuer_filing | regulator; absent = news), published_basis (gdelt_seen when published_at is GDELT's first sighting; see source-tiers.md); revisions also supersedes_card_id and a deterministic revision ID.
assessment stores validation outcome, source SHA-256, source-text span offsets and ordinal claims/reasons. It does not publish a complete publisher article.
event_identity is accepted only when the four identity fields occur verbatim in supplied source text/headline. Different numeric signatures stay separate. This deliberately misses some paraphrases/rounded figures.
A source URL with changed text is retained as a new revision record. Same-URL revisions group only with compatible extracted identity or unchanged source headline. Unrelated reused URLs remain separate. Revision date is observation date so historical editions are not rewritten.
Historical records lacking source fingerprints are not silently replayed through paid inference. No evidence is fabricated from AI-written summaries.
The eight reviewed migration groups are frozen by card IDs, headlines and full raw-card hashes. Changed content invalidates its group decision.

## Frontend compatibility
Treat events.json as optional. Missing, stale or invalid membership -> preserve raw-card rendering with a visible grouping limitation. Unmapped cards must remain visible.
Do not change the old index counts to pretend they count unique events. Show both events/articles where needed.
Source selection is human-reviewed card first, then assessable card, then fuller existing summary; this is not a global source-reliability score. Do not present a merged event as human reviewed unless its exact representative was reviewed.
No frontend source grouping/scoring copy: consume this contract; report required changes to Codex.

## Current snapshot
25 September migration: 222 raw cards, 214 -> 172 events; 12 reviewed groups (62 cards), 42 recorded aliases, 3 relations, 1 date correction. Original per-day files unchanged. (24 September release: 182 cards, 174 events, eight two-source pairs.)
All legacy events have needs_review priority because source-backed assessment fields were not collected by brief-v1. This is not a completed historical ranking backfill.
Raw/source URL canonical redirect resolution, broad historical near-duplicate review, source recovery/backfill, human ranking acceptance and the live browser/PDF work remain separate delivery tasks.
