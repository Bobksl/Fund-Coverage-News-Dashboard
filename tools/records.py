"""Phase 2 evidence/decision contract: validation, inference allowlist and byte-exact JSONL."""
import json
import os
import re
from pathlib import Path

from tools.validate_spec import reject_constant, unique_keys

SOURCE_KINDS = {"filing", "regulatory_record", "issuer_release", "ratings_analysis",
                "independent_reporting", "discovery_only", "other"}
ACCESS_STATUS = {"accessible", "partial", "unavailable"}
EVIDENCE_SCOPES = {"full_text", "primary_excerpt", "metadata_only"}
DATE_PRECISIONS = {"datetime", "date", "month", "unknown"}
GATE_NAMES = ("evidence", "identity", "relevance", "materiality", "transmission", "novelty")
GATE_OUTCOMES = {"pass", "fail", "review_required", "not_evaluated"}
RECOMMENDATIONS = {"priority_shortlist", "shortlist", "reserve_manual_only", "suppress", "review_required"}
REASON_CODES = {"no_relevance", "routine_activity", "insufficient_evidence", "ambiguous_identity",
                "conflicting_evidence", "duplicate", "no_new_fact", "below_materiality",
                "weak_transmission", "below_band", "capacity", "shortlisted", "critical_review",
                "override_approved", "draft_invalid"}
PUBLICATION_STATUS = {"not_selected", "pending_review", "approved", "published", "corrected"}
ANALYST_ONLY_PUBLICATION = {"approved", "published", "corrected"}
ASSET_CLASSES = {"venture_capital", "real_estate", "private_equity", "private_credit"}
RELEVANCE_LEVELS = {"A", "B", "C"}
COMPONENTS = ("portfolio_fit", "materiality", "investment_transmission", "actionability",
              "source_credibility", "novelty")

ARTICLE_FIELDS = ("article_id", "title", "original_url", "canonical_url", "publisher",
                  "originating_publisher", "discovery_method", "source_kind", "published_at",
                  "published_date_precision", "event_date", "first_seen_at", "retrieved_at",
                  "access_status", "evidence_scope", "evidence_hash", "evidence_local_ref",
                  "claims", "supersedes_article_id")
ARTICLE_NULLABLE = {"originating_publisher", "published_at", "event_date", "evidence_hash",
                    "evidence_local_ref", "supersedes_article_id"}

# The only article fields a baseline, classifier, grouper, ranker or drafter may read.
INFERENCE_ALLOWLIST = ("article_id", "title", "original_url", "canonical_url", "publisher",
                       "originating_publisher", "source_kind", "published_at",
                       "published_date_precision", "event_date", "access_status",
                       "evidence_scope", "body")
# Evaluator-only ground truth. Never an inference input, at any nesting depth.
EVALUATOR_ONLY = {"decision", "analyst_id", "relevance_label", "materiality_tier",
                  "event_group_id", "gold_event_group_id", "must_not_miss", "rationale",
                  "evidence_access", "reviewed_on", "cohort", "challenge_category",
                  "selection_reason", "split", "partition_reason", "gold", "labels"}

DECISION_FIELDS = ("event_id", "revision", "decision_id", "run_id", "attempt", "article_ids",
                   "claim_ids", "event_identity", "direct_entity_ids", "propagated_entity_ids",
                   "entity_matches", "held_status", "asset_classes", "sector_ids", "theme_ids",
                   "primary_event_type", "subtype", "secondary_event_types", "countries",
                   "primary_region", "region_basis", "relevance_level", "eligibility_reason",
                   "transmission", "gates", "components", "total_score", "recommendation",
                   "disposition_reason_codes", "duplicate_of", "update_of", "model_metadata",
                   "spec_metadata", "analyst_review", "publication")

CREDENTIAL_KEY = re.compile(r"api[_-]?key|secret|token|password|authorization", re.I)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_MONTH = re.compile(r"^\d{4}-\d{2}$")
ISO_INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$")


def validate_article(record):
    """Return contract errors for one evidence record. Unknown facts stay null, never imputed."""
    errors = []
    if not isinstance(record, dict):
        return ["article: not an object"]
    errors += [f"article: missing field {f}" for f in ARTICLE_FIELDS if f not in record]
    errors += [f"article: unexpected field {f}" for f in sorted(set(record) - set(ARTICLE_FIELDS))]
    for field in ARTICLE_FIELDS:
        if field in record and record[field] is None and field not in ARTICLE_NULLABLE:
            errors.append(f"article: {field} must not be null")
    if record.get("source_kind") not in SOURCE_KINDS:
        errors.append("article: invalid source_kind")
    if record.get("access_status") not in ACCESS_STATUS:
        errors.append("article: invalid access_status")
    if record.get("evidence_scope") not in EVIDENCE_SCOPES:
        errors.append("article: invalid evidence_scope")
    precision = record.get("published_date_precision")
    if precision not in DATE_PRECISIONS:
        errors.append("article: invalid published_date_precision")
    # published_at carries exactly the precision the source actually published.
    published_at = record.get("published_at")
    if precision == "datetime":
        if published_at is None:
            errors.append("article: datetime precision without published_at")
        elif not ISO_INSTANT.match(str(published_at)):
            errors.append("article: published_at needs an ISO instant with offset")
    elif precision == "date":
        if not ISO_DATE.match(str(published_at)):
            errors.append("article: date-only evidence must not carry an invented publication time")
    elif precision == "month":
        if not ISO_MONTH.match(str(published_at)):
            errors.append("article: month precision needs a YYYY-MM value")
    elif precision == "unknown" and published_at is not None:
        errors.append("article: unknown precision must leave published_at null")
    if record.get("event_date") is not None and not ISO_DATE.match(str(record["event_date"])):
        errors.append("article: event_date must be an ISO date")
    for field in ("first_seen_at", "retrieved_at"):
        if field in record and not ISO_INSTANT.match(str(record.get(field))):
            errors.append(f"article: {field} must be an ISO instant with offset")
    if record.get("access_status") == "unavailable" and record.get("evidence_scope") != "metadata_only":
        errors.append("article: unavailable evidence cannot claim examined text")
    if record.get("evidence_scope") in {"full_text", "primary_excerpt"} and not record.get("evidence_hash"):
        errors.append("article: examined evidence needs evidence_hash of the actual input")
    claims = record.get("claims")
    if not isinstance(claims, list):
        errors.append("article: claims must be a list")
    else:
        for claim in claims:
            if not isinstance(claim, dict) or not all(
                    key in claim for key in ("claim_id", "statement", "article_id", "evidence_span")):
                errors.append("article: claim missing required keys")
                continue
            if claim.get("amount") is not None and not all(
                    claim.get(key) is not None for key in ("currency", "unit", "basis", "period")):
                errors.append(f"claim {claim['claim_id']}: numeric claim needs currency, unit, basis and period")
    return errors


def leakage_scan(payload, path="input"):
    """Return the paths of evaluator-only keys found at any depth."""
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in EVALUATOR_ONLY:
                found.append(f"{path}.{key}")
            found += leakage_scan(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for number, value in enumerate(payload):
            found += leakage_scan(value, f"{path}[{number}]")
    return found


def to_inference_input(article, body=None):
    """Project one evidence record onto the allowlist. Evaluator metadata cannot survive this.

    Evidence text is held privately and passed in explicitly; it is never a stored record field.
    """
    payload = {key: article[key] for key in INFERENCE_ALLOWLIST if key in article}
    if body is not None:
        payload["body"] = body
    leaks = leakage_scan(payload)
    if leaks:
        raise ValueError(f"Evaluator-only fields reached an inference input: {leaks}")
    return payload


def validate_decision(record, article_ids=None):
    """Return contract errors for one decision attempt."""
    errors = []
    if not isinstance(record, dict):
        return ["decision: not an object"]
    errors += [f"decision: missing field {f}" for f in DECISION_FIELDS if f not in record]
    errors += [f"decision: unexpected field {f}" for f in sorted(set(record) - set(DECISION_FIELDS))]
    for field in ("event_id", "decision_id", "run_id", "primary_event_type"):
        if not isinstance(record.get(field), str) or not record.get(field):
            errors.append(f"decision: {field} must be a stable non-empty ID")
    for field in ("revision", "attempt"):
        if not isinstance(record.get(field), int) or isinstance(record.get(field), bool):
            errors.append(f"decision: {field} must be an integer")
    article_refs = record.get("article_ids")
    if not isinstance(article_refs, list) or not article_refs:
        errors.append("decision: article_ids must list the evidence packet")
    elif article_ids is not None:
        errors += [f"decision: unknown article {a}" for a in article_refs if a not in article_ids]
    if record.get("held_status") != "monitored":
        errors.append("decision: Phase 2 held_status must be exactly monitored")
    for field, allowed in (("asset_classes", ASSET_CLASSES), ("disposition_reason_codes", REASON_CODES)):
        values = record.get(field)
        if not isinstance(values, list):
            errors.append(f"decision: {field} must be a list")
        else:
            errors += [f"decision: invalid {field} value {v}" for v in values if v not in allowed]
    if not record.get("disposition_reason_codes"):
        errors.append("decision: at least one disposition reason code required")
    if record.get("relevance_level") not in RELEVANCE_LEVELS | {None}:
        errors.append("decision: invalid relevance_level")
    if record.get("recommendation") not in RECOMMENDATIONS:
        errors.append("decision: invalid recommendation")
    gates = record.get("gates")
    if not isinstance(gates, dict) or set(gates) != set(GATE_NAMES):
        errors.append("decision: gates must cover exactly the six named gates")
        gates = {}
    errors += [f"decision: invalid gate outcome for {name}" for name, outcome in gates.items()
               if outcome not in GATE_OUTCOMES]
    components = record.get("components")
    if not isinstance(components, dict) or set(components) != set(COMPONENTS):
        errors.append("decision: components must cover exactly the six named components")
        components = {}
    scored = {}
    for name, component in components.items():
        if not isinstance(component, dict) or "points" not in component or "reason" not in component:
            errors.append(f"decision: component {name} needs points and reason")
            continue
        points = component["points"]
        if points is None:
            continue
        if not isinstance(points, int) or isinstance(points, bool):
            errors.append(f"decision: component {name} points must be an integer anchor or null")
            continue
        scored[name] = points
    total = record.get("total_score")
    complete = len(scored) == len(COMPONENTS)
    if complete and total != sum(scored.values()):
        errors.append("decision: total_score must be the deterministic sum of the six anchors")
    if not complete and total is not None:
        errors.append("decision: unscorable components require a null total, never an imputed zero")
    if "review_required" in gates.values() and record.get("recommendation") != "review_required":
        errors.append("decision: an unresolved gate must surface as review_required")
    if "fail" in gates.values() and record.get("recommendation") in {"priority_shortlist", "shortlist"}:
        errors.append("decision: a failed gate cannot be shortlisted")
    publication = record.get("publication")
    if not isinstance(publication, dict) or publication.get("status") not in PUBLICATION_STATUS:
        errors.append("decision: publication.status invalid")
    elif publication["status"] in ANALYST_ONLY_PUBLICATION and not record.get("analyst_review"):
        errors.append("decision: only a recorded analyst review can approve or publish")
    metadata = record.get("model_metadata") or {}
    if isinstance(metadata, dict):
        errors += [f"decision: model_metadata must not carry credentials ({key})"
                   for key in metadata if CREDENTIAL_KEY.search(key)]
    return errors


def loads(text):
    """Strict JSON load: duplicate keys and non-finite numbers are contract violations."""
    return json.loads(text, object_pairs_hook=unique_keys, parse_constant=reject_constant)


def read_jsonl(path):
    return [loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def dumps_jsonl(rows):
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write_jsonl(path, rows, allow_overwrite=False):
    """Single-writer atomic write with byte-exact LF endings; refuses to clobber frozen evidence."""
    path = Path(path)
    if path.exists() and not allow_overwrite:
        raise FileExistsError(f"Refusing to overwrite existing evidence at {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(dumps_jsonl(rows).encode("utf-8"))
    os.replace(temporary, path)
    return len(rows)


def publication_date(record):
    """Return the published calendar date, or None when the source did not establish one.

    A month-precision or unknown record has no day; the caller records it as a split exception
    rather than inventing one.
    """
    value = record.get("published_at")
    precision = record.get("published_date_precision")
    if precision == "datetime" and value:
        return str(value)[:10]
    if precision == "date" and value:
        return str(value)
    return None
