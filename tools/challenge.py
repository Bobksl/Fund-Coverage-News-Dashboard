"""Challenge-set curation: categories, coverage against the protocol minimums, leakage guards.

The challenge cohort is deliberately constructed, so its selection rationale is evaluator-only and
must never reach the analyst packet or an inference input. Coverage is counted against the minimums
in phase-2-experiment.md and reported short when it is short: a constructed set that misses its
coverage targets is an incomplete probe, not a passing one.

Challenge records are linked to a natural-feed record when they describe the same article, never
counted twice.
"""
import json
from pathlib import Path

from tools.records import EVALUATOR_ONLY, leakage_scan

# phase-2-experiment.md coverage requirements. Overlapping, not additive.
CATEGORY_MINIMUMS = {
    "hard_negative": 25,
    "manager_independent_bc": 15,
    "identity": 10,
    "multi_article_group": 10,
    "material_update": 5,
    "critical_risk": 8,
    "apac_global_other": 5,
    "similar_headline_pair": 2,
    "operational": 0,
}
REQUIRED_FIELDS = ("article_id", "categories", "selection_reason")


def validate_rows(rows, natural_feed_ids=frozenset()):
    """Return errors for challenge registry rows. A label is not a selection rationale."""
    errors, seen = [], set()
    for number, row in enumerate(rows, start=1):
        missing = [field for field in REQUIRED_FIELDS if not row.get(field)]
        errors += [f"row {number}: missing {field}" for field in missing]
        categories = row.get("categories")
        if categories is not None and not isinstance(categories, list):
            errors.append(f"row {number}: categories must be a list")
            categories = []
        # The protocol's coverage requirements overlap rather than sum, so one record may serve
        # more than one probe. Each named category must still be real.
        errors += [f"row {number}: unknown category {c}" for c in (categories or [])
                   if c not in CATEGORY_MINIMUMS]
        article_id = row.get("article_id")
        if article_id in seen:
            errors.append(f"row {number}: duplicate article {article_id}")
        seen.add(article_id)
        # A challenge row may link to a natural-feed record; it may never silently duplicate one.
        linked = row.get("linked_natural_feed_article_id")
        if article_id in natural_feed_ids and not linked:
            errors.append(f"row {number}: {article_id} is already a natural-feed record and must "
                          "be linked rather than recounted")
        # These fields belong in the evaluator-side registry, but never in inference inputs.
        forbidden = sorted(set(row) & (EVALUATOR_ONLY - {
            "selection_reason", "challenge_category", "categories"}))
        errors += [f"row {number}: carries analyst field {field}" for field in forbidden]
    return errors


def coverage(rows):
    """Count each category against its minimum. Overlapping categories are counted per row."""
    counts = {}
    for row in rows:
        for category in row.get("categories") or []:
            counts[category] = counts.get(category, 0) + 1
    report = {}
    for category, minimum in sorted(CATEGORY_MINIMUMS.items()):
        have = counts.get(category, 0)
        report[category] = {"have": have, "minimum": minimum, "short_by": max(0, minimum - have),
                            "met": have >= minimum}
    return {
        "records": len(rows),
        "category_assignments": sum(len(row.get("categories") or []) for row in rows),
        "by_category": report,
        "categories_met": sorted(k for k, v in report.items() if v["met"]),
        "categories_short": sorted(k for k, v in report.items() if not v["met"]),
        "complete": all(v["met"] for v in report.values()),
        "note": ("Coverage counts curated records, not analyst-confirmed events. Meeting a minimum "
                 "says the probe was constructed, never that the pipeline passed it."),
    }


def packet_rows(rows):
    """Strip a challenge registry to what an analyst packet may see: the article ID alone."""
    payload = [{"article_id": row["article_id"]} for row in rows]
    leaks = leakage_scan(payload)
    if leaks:
        raise ValueError(f"Challenge rationale reached the packet: {leaks}")
    return payload


def write_registry(path, rows, natural_feed_ids=frozenset(), allow_overwrite=False):
    errors = validate_rows(rows, natural_feed_ids)
    if errors:
        raise ValueError(f"Challenge registry invalid: {errors[:5]}")
    path = Path(path)
    if path.exists() and not allow_overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_bytes(payload.encode("utf-8"))
    return len(rows)
