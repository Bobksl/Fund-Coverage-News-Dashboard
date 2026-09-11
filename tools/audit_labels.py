"""Evaluator-only label audit. No inference, semantic relabeling or gold freeze."""
from collections import Counter, defaultdict
from datetime import datetime

from tools.review_packet import LABEL_FIELDS

ENUMS = {
    "decision": {"publish", "reserve", "reject", "review"},
    "relevance_level": {"A", "B", "C", "outside", "uncertain"},
    "materiality_tier": {"high", "medium", "low", "uncertain"},
    "must_not_miss": {"yes", "no"},
    "evidence_access": {"full", "partial", "inaccessible"},
}


def audit_rows(rows, article_ids, date_format="iso"):
    if date_format not in {"iso", "mdy", "dmy"}:
        raise ValueError("Explicit supported date format required")
    errors, changes, normalized, seen = [], [], [], set()
    groups = defaultdict(list)
    blank = 0
    for number, original in enumerate(rows, start=2):
        if not any(original.values()):
            blank += 1
            continue
        if set(original) != set(LABEL_FIELDS) or any(not isinstance(v, str) for v in original.values()):
            errors.append(f"Row {number}: malformed columns or non-string values")
            continue
        row = {key: value.strip() for key, value in original.items()}
        for key in row:
            if row[key] != original[key]:
                changes.append({"row": number, "field": key, "operation": "trim_outer_whitespace"})
            if not row[key]:
                errors.append(f"Row {number}: missing {key}")
        article_id = row["article_id"]
        if article_id not in article_ids:
            errors.append(f"Row {number}: unknown article ID")
        if article_id in seen:
            errors.append(f"Row {number}: duplicate article ID")
        seen.add(article_id)
        for key, allowed in ENUMS.items():
            if row[key] not in allowed:
                errors.append(f"Row {number}: invalid {key}")
        try:
            fmt = {"iso": "%Y-%m-%d", "mdy": "%m/%d/%Y", "dmy": "%d/%m/%Y"}[date_format]
            parsed = datetime.strptime(row["reviewed_on"], fmt).date().isoformat()
            if parsed != row["reviewed_on"]:
                changes.append({"row": number, "field": "reviewed_on", "from": row["reviewed_on"], "to": parsed})
            row["reviewed_on"] = parsed
        except ValueError:
            errors.append(f"Row {number}: reviewed_on does not match explicit {date_format} format")
        if row["decision"] == "publish" and (row["relevance_level"] in {"outside", "uncertain"} or row["evidence_access"] == "inaccessible"):
            errors.append(f"Row {number}: publish conflicts with relevance/evidence")
        normalized.append(row)
        if row["event_group_id"]:
            groups[row["event_group_id"]].append(row)
    for missing in sorted(set(article_ids) - seen):
        errors.append(f"Missing label for article {missing}")
    conflicts = sorted(group for group, members in groups.items()
                       if len({r["decision"] for r in members}) > 1)
    errors.extend(f"Event group {group}: inconsistent publication decisions" for group in conflicts)
    report = {
        "label_rows": len(normalized), "blank_rows_ignored": blank,
        "decisions": dict(Counter(r["decision"] for r in normalized)),
        "event_groups": len(groups), "conflicting_event_groups": conflicts,
        "uncontested_publish_groups": sum(all(r["decision"] == "publish" for r in members) for members in groups.values()),
        "must_not_miss_rows": sum(r["must_not_miss"] == "yes" for r in normalized),
        "review_rows": sum(r["decision"] == "review" for r in normalized),
        "normalizations": changes, "errors": errors, "structurally_valid": not errors,
        "freeze_ready": False,
        "limits": "Structural audit only. Human adjudication, evidence and provenance checks, and explicit freeze remain required. No performance metrics.",
    }
    return report, normalized
