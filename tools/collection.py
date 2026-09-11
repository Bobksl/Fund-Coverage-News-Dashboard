"""Manual-collection bookkeeping: frozen window manifest, intake normalization and gap log.

This module contains no HTTP client and fetches nothing. A person enumerates the fixed public
indexes in an ordinary browser under docs/natural-feed-policy.md; this module records what was
observed as contract-valid evidence, assigns stable IDs and keeps source gaps as first-class
records. Building an automated collector remains Phase 3 work and stays gated.

Index enumeration establishes metadata only. An entry's `evidence_scope` is `metadata_only` until
the article's permitted text is actually captured and hashed in a separate step.
"""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid5

from tools.records import ISO_DATE, ISO_INSTANT, validate_article, write_jsonl

# Stripped because they identify a campaign, not a document. Everything else is substantive.
TRACKING_PARAMETERS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                       "utm_id", "gclid", "fbclid", "mc_cid", "mc_eid", "igshid", "_hsenc",
                       "_hsmi", "vero_id", "ref_src"}
TIER_SOURCE_KINDS = {"manager_newsroom": "issuer_release", "regulator_filing": "filing",
                     "independent_publication": "independent_reporting"}
GAP_REASONS = {"index_unreachable", "index_empty", "no_index_published", "pagination_truncated",
               "article_inaccessible", "article_links_unavailable", "index_dates_unavailable",
               "roster_pending"}
MANIFEST_FIELDS = ("cohort", "policy_document", "policy_sha256", "window_start", "window_end",
                   "holdout_cutoff", "recorded_at", "sources", "note")


def canonicalize(url):
    """Remove known tracking parameters only. Substantive identifiers are preserved."""
    parts = urlsplit(url)
    kept = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in TRACKING_PARAMETERS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def article_id_for(canonical_url):
    """Stable opaque ID derived from the canonical URL, so re-collection is idempotent."""
    return str(uuid5(NAMESPACE_URL, canonical_url))


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_manifest(manifest):
    errors = []
    missing = [field for field in MANIFEST_FIELDS if field not in manifest]
    errors += [f"manifest: missing {field}" for field in missing]
    if missing:
        return errors
    for field in ("window_start", "window_end", "holdout_cutoff"):
        if not ISO_DATE.match(str(manifest[field])):
            errors.append(f"manifest: {field} must be an ISO date")
    if not ISO_INSTANT.match(str(manifest["recorded_at"])):
        errors.append("manifest: recorded_at must be an ISO instant with offset")
    if errors:
        return errors
    start = date.fromisoformat(manifest["window_start"])
    end = date.fromisoformat(manifest["window_end"])
    cutoff = date.fromisoformat(manifest["holdout_cutoff"])
    if start >= end:
        errors.append("manifest: window_start must precede window_end")
    if not start < cutoff <= end:
        errors.append("manifest: holdout_cutoff must fall inside the window")
    if not manifest["sources"]:
        errors.append("manifest: roster is empty")
    seen = set()
    for source in manifest["sources"]:
        for field in ("source_id", "tier", "entry_point", "verification", "scope_note"):
            if not source.get(field):
                errors.append(f"manifest: source missing {field}")
        if source.get("tier") not in TIER_SOURCE_KINDS:
            errors.append(f"manifest: unknown tier for {source.get('source_id')}")
        if source.get("source_id") in seen:
            errors.append(f"manifest: duplicate source {source['source_id']}")
        seen.add(source.get("source_id"))
    return errors


def build_manifest(window_start, window_end, holdout_cutoff, sources, policy_path, recorded_at,
                   cohort="natural_feed"):
    """Freeze the window and roster before any entry is recorded."""
    manifest = {
        "cohort": cohort,
        "policy_document": str(policy_path).replace("\\", "/"),
        "policy_sha256": file_digest(policy_path),
        "window_start": window_start, "window_end": window_end,
        "holdout_cutoff": holdout_cutoff,
        "recorded_at": recorded_at,
        "sources": sorted(sources, key=lambda source: source["source_id"]),
        "note": ("Window, cutoff and roster are fixed before collection. An added or replaced "
                 "source requires a dated amendment and cannot be blended into this cohort."),
    }
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError(f"Collection manifest invalid: {errors}")
    return manifest


def calendar_date(published_at):
    """The publisher's calendar date, for a date-only or a full-precision timestamp alike."""
    if not published_at:
        return None
    candidate = str(published_at)[:10]
    return candidate if ISO_DATE.match(candidate) else None


def in_window(published_at, manifest):
    day = calendar_date(published_at)
    if day is None:
        return False
    return manifest["window_start"] <= day <= manifest["window_end"]


def partition_for(published_date, manifest):
    """Calibration before the cutoff, holdout from it. Undated entries belong to neither."""
    if not in_window(published_date, manifest):
        return None
    return ("holdout" if calendar_date(published_date) >= manifest["holdout_cutoff"]
            else "calibration")


def to_evidence(observation, source, retrieved_at, first_seen_at=None):
    """Normalize one observed index entry into a contract-valid evidence record."""
    canonical = canonicalize(observation["url"])
    precision = observation.get("published_date_precision", "date")
    published_at = observation.get("published_at")
    if precision == "unknown":
        published_at = None
    record = {
        "article_id": article_id_for(canonical),
        "title": observation["title"].strip(),
        "original_url": observation["url"],
        "canonical_url": canonical,
        "publisher": observation.get("publisher") or source["publisher"],
        "originating_publisher": observation.get("originating_publisher"),
        "discovery_method": f"manual_index_enumeration:{source['source_id']}",
        "source_kind": observation.get("source_kind") or TIER_SOURCE_KINDS[source["tier"]],
        "published_at": published_at,
        "published_date_precision": precision,
        "event_date": observation.get("event_date"),
        "first_seen_at": first_seen_at or retrieved_at,
        "retrieved_at": retrieved_at,
        # Enumeration sees a listing, not an article. Text capture is a separate, later step.
        "access_status": observation.get("access_status", "accessible"),
        "evidence_scope": observation.get("evidence_scope", "metadata_only"),
        "evidence_hash": observation.get("evidence_hash"),
        "evidence_local_ref": observation.get("evidence_local_ref"),
        "claims": [],
        "supersedes_article_id": observation.get("supersedes_article_id"),
    }
    errors = validate_article(record)
    if errors:
        raise ValueError(f"Observation does not satisfy the evidence contract: {errors}")
    return record


def merge_records(records):
    """Collapse the same canonical article seen on two indexes into one record.

    Both discovery paths are kept in `discovery_method`, and the earliest first_seen_at wins, so
    cross-index provenance survives without inventing a second article. This is exact-URL
    deduplication, not semantic event clustering.
    """
    merged = {}
    for record in sorted(records, key=lambda item: (item["article_id"], item["first_seen_at"])):
        existing = merged.get(record["article_id"])
        if existing is None:
            merged[record["article_id"]] = dict(record)
            continue
        sources = sorted({part for field in (existing["discovery_method"], record["discovery_method"])
                          for part in field.split(":", 1)[1].split("+")})
        existing["discovery_method"] = "manual_index_enumeration:" + "+".join(sources)
        existing["first_seen_at"] = min(existing["first_seen_at"], record["first_seen_at"])
        if existing["access_status"] == "unavailable" and record["access_status"] != "unavailable":
            existing["access_status"] = record["access_status"]
    return [merged[key] for key in sorted(merged)]


def gap_record(source_id, reason, observed_at, detail, attempts=1):
    """A source gap is a recorded fact, never an absence of news."""
    if reason not in GAP_REASONS:
        raise ValueError(f"Unknown gap reason {reason}")
    return {"source_id": source_id, "reason": reason, "observed_at": observed_at,
            "attempts": attempts, "detail": detail,
            "note": "Recorded coverage gap. This is not evidence that the source published nothing."}


def intake_report(manifest, records, gaps):
    """Per-source counts, partition split and gaps. No editorial judgement is applied."""
    by_source, partitions, out_of_window = {}, {"calibration": 0, "holdout": 0}, 0
    duplicates = len(records) - len({record["article_id"] for record in records})
    for record in records:
        for source_id in record["discovery_method"].split(":", 1)[1].split("+"):
            by_source[source_id] = by_source.get(source_id, 0) + 1
        partition = partition_for(record.get("published_at"), manifest)
        if partition:
            partitions[partition] += 1
        else:
            out_of_window += 1
    covered = sorted(by_source)
    gapped = {gap["source_id"] for gap in gaps}
    roster = {source["source_id"] for source in manifest["sources"]}
    # A source that was enumerated and simply had nothing in the window is an observed zero,
    # not a coverage gap. Collapsing the two would overstate how much coverage was lost.
    observed_zero = sorted(roster - set(covered) - gapped)
    return {
        "cohort": manifest["cohort"],
        "window": [manifest["window_start"], manifest["window_end"]],
        "holdout_cutoff": manifest["holdout_cutoff"],
        "records": len(records),
        "duplicate_article_ids": duplicates,
        "records_by_source": dict(sorted(by_source.items())),
        "partition_counts": partitions,
        "records_outside_window_or_undated": out_of_window,
        "sources_in_roster": len(manifest["sources"]),
        "sources_with_records": len(covered),
        "sources_observed_zero_in_window": observed_zero,
        "sources_gapped_or_pending": sorted(gapped),
        "gaps": gaps,
        "limits": ("Enumeration metadata only: no article text has been captured or hashed, so no "
                   "record is yet labelable evidence. Counts are collection facts, not editorial "
                   "or performance results."),
    }


def write_collection(directory, manifest, records, gaps, allow_overwrite=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "collection-manifest.json"
    if manifest_path.exists() and not allow_overwrite:
        raise FileExistsError(f"Refusing to overwrite the frozen manifest at {manifest_path}")
    manifest_path.write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    write_jsonl(directory / "evidence.jsonl", records, allow_overwrite=True)
    write_jsonl(directory / "gaps.jsonl", gaps, allow_overwrite=True)
    report = intake_report(manifest, records, gaps)
    (directory / "intake-report.json").write_bytes(
        json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    (directory / "manifest-sha256.txt").write_text(
        file_digest(manifest_path) + "  collection-manifest.json\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--report", action="store_true",
                        help="Recompute the intake report from recorded evidence and gaps")
    args = parser.parse_args(argv)
    manifest = json.loads((args.directory / "collection-manifest.json").read_text(encoding="utf-8"))
    errors = validate_manifest(manifest)
    if errors:
        raise SystemExit(f"Frozen manifest is invalid: {errors}")
    records, gaps = [], []
    for name, target in (("evidence.jsonl", records), ("gaps.jsonl", gaps)):
        path = args.directory / name
        if path.exists():
            target.extend(json.loads(line) for line in
                          path.read_text(encoding="utf-8").splitlines() if line.strip())
    report = intake_report(manifest, records, gaps)
    if args.report:
        (args.directory / "intake-report.json").write_bytes(
            json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def write_jsonl_safely(path, rows):
    """Rewrite a derived file. Evidence is rebuilt from observations, so replacement is expected."""
    return write_jsonl(path, rows, allow_overwrite=True)
