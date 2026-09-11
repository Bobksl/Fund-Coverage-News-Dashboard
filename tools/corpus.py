"""Corpus construction: cohort registry, blinded review packets and leakage-safe splits.

Natural-feed and challenge records are registered separately and stay separate in every report.
The review packet the analyst sees is one combined, opaquely ordered article list: it reveals no
cohort, challenge category or selection rationale. The custodian may use gold groups to build a
leakage-safe split; only article IDs and a partition name leave this module for the pipeline.
"""
import argparse
import hashlib
import json
from pathlib import Path

from tools.records import (dumps_jsonl, leakage_scan, publication_date, read_jsonl,
                           write_jsonl)
from tools.review_packet import build_packet

COHORTS = ("natural_feed", "challenge")
MIN_POSITIVE_EVENTS = 20


def register(records, cohort, policy, challenge_category=None, selection_reason=None):
    """Return evaluator-only registry rows. Never an inference input and never in a packet."""
    if cohort not in COHORTS:
        raise ValueError(f"Unknown cohort {cohort}")
    if cohort == "natural_feed" and (challenge_category or selection_reason):
        raise ValueError("A natural-feed record has no selection rationale by definition")
    if cohort == "challenge" and not challenge_category:
        raise ValueError("Challenge records must record their coverage category")
    return [{"article_id": record["article_id"], "cohort": cohort, "policy": policy,
             "challenge_category": challenge_category, "selection_reason": selection_reason}
            for record in records]


def write_registry(path, rows, allow_overwrite=False):
    return write_jsonl(path, rows, allow_overwrite=allow_overwrite)


def build_review_packet(records, destination):
    """Build one blinded article-only packet across cohorts, in opaque ID order.

    Records without an established publication date are excluded and reported rather than given a
    guessed date. Cohort membership is never written into the packet.
    """
    usable, excluded = [], []
    for record in sorted(records, key=lambda item: item["article_id"]):
        published = publication_date(record)
        if not published:
            excluded.append({"article_id": record["article_id"],
                             "reason": f"no established publication date "
                                       f"({record.get('published_date_precision')})"})
            continue
        usable.append({"article_id": record["article_id"], "title": record["title"],
                       "url": record["original_url"], "publisher": record["publisher"],
                       "published_date": published})
    leaks = leakage_scan(usable)
    if leaks:
        raise ValueError(f"Packet input carries evaluator-only fields: {leaks}")
    created = build_packet(usable, destination) if usable else 0
    return {"articles": created, "excluded": excluded,
            "note": "Ordering is by opaque ID. Cohort and challenge category are not disclosed."}


def temporal_split(records, gold_group_by_article, cutoff):
    """Split by publication date, keeping each gold event lineage on one side of the cutoff.

    A lineage that spans the cutoff is quarantined into the holdout with its earlier articles
    removed from calibration, so no later article is ever moved into calibration and called
    strict temporal separation.
    """
    dated, exceptions = {}, []
    for record in records:
        published = publication_date(record)
        if not published:
            exceptions.append({"article_id": record["article_id"], "reason": "no established date",
                               "precision": record.get("published_date_precision")})
            continue
        dated[record["article_id"]] = published

    lineages = {}
    for article_id, published in dated.items():
        group = gold_group_by_article.get(article_id, f"ungrouped:{article_id}")
        lineages.setdefault(group, []).append((article_id, published))

    calibration, holdout, quarantined = [], [], []
    for group, members in sorted(lineages.items()):
        later = [article_id for article_id, published in members if published >= cutoff]
        earlier = [article_id for article_id, published in members if published < cutoff]
        if later and earlier:
            holdout.extend(sorted(later + earlier))
            quarantined.append({"event_group_id": group, "article_ids": sorted(later + earlier),
                                "reason": "event lineage spans the cutoff; reserved wholly for holdout"})
        elif later:
            holdout.extend(sorted(later))
        else:
            calibration.extend(sorted(earlier))
    return {"cutoff": cutoff, "calibration": sorted(calibration), "holdout": sorted(holdout),
            "quarantined_lineages": quarantined, "date_exceptions": exceptions,
            "unassigned": sorted(item["article_id"] for item in exceptions),
            "note": "Undated records are excluded from the headline holdout and reported explicitly."}


def sufficiency(article_ids, gold_rows, cohort, split, min_positive_events=MIN_POSITIVE_EVENTS):
    """Count distinct analyst-publish-worthy events in one partition. Eligibility is not a positive."""
    selected = set(article_ids)
    groups = {}
    for row in gold_rows:
        if row["article_id"] not in selected:
            continue
        groups.setdefault(row["event_group_id"], set()).add(row["decision"])
    publish_worthy = sorted(group for group, decisions in groups.items() if "publish" in decisions)
    negatives = sorted(group for group, decisions in groups.items() if "publish" not in decisions)
    return {"cohort": cohort, "split": split, "articles": len(selected),
            "distinct_events": len(groups),
            "publish_worthy_events": len(publish_worthy),
            "non_publish_worthy_events": len(negatives),
            "minimum_required": min_positive_events,
            "sufficient": len(publish_worthy) >= min_positive_events,
            "disposition": "evaluable" if len(publish_worthy) >= min_positive_events
            else "inconclusive_insufficient_positive_events",
            "note": "Extend the consecutive window under a recorded rule; never top up with "
                    "challenge positives and never resize after seeing model results."}


def runner_manifest(run_id, partition, article_ids):
    """The only thing that crosses to the pipeline: a run ID, a partition name and article IDs."""
    manifest = {"run_id": run_id, "partition": partition, "article_ids": sorted(set(article_ids))}
    leaks = leakage_scan(manifest)
    if leaks:
        raise ValueError(f"Manifest carries evaluator-only fields: {leaks}")
    return manifest


def freeze_record(labels_path, evidence_path, split_manifest_path, predictions_path, frozen_at):
    """Record the hashes that must exist before any benchmark inference is evaluated."""
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return {"labels_sha256": digest(labels_path), "evidence_sha256": digest(evidence_path),
            "split_manifest_sha256": digest(split_manifest_path),
            "predictions_sha256": digest(predictions_path) if predictions_path else None,
            "frozen_at": frozen_at,
            "note": "A later label change creates a new version; it is never retroactively "
                    "credited to earlier predictions."}


def registry_digest(rows):
    return hashlib.sha256(dumps_jsonl(rows).encode("utf-8")).hexdigest()


def _write_json(path, payload):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
    return path


def main(argv=None):
    """Custodian commands. These read gold groups; their outputs never reach inference."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    packet = sub.add_parser("packet", help="Build one blinded article-only analyst packet")
    packet.add_argument("evidence", type=Path)
    packet.add_argument("destination", type=Path)

    split = sub.add_parser("split", help="Write a leakage-safe temporal split manifest")
    split.add_argument("evidence", type=Path)
    split.add_argument("cutoff", help="ISO date; earlier is calibration, later is holdout")
    split.add_argument("output", type=Path)
    split.add_argument("--gold-groups", type=Path, default=None,
                       help="Evaluator-only JSON map of article_id to gold event group")

    freeze = sub.add_parser("freeze", help="Record the hashes that must precede inference")
    freeze.add_argument("labels", type=Path)
    freeze.add_argument("evidence", type=Path)
    freeze.add_argument("split_manifest", type=Path)
    freeze.add_argument("output", type=Path)
    freeze.add_argument("--predictions", type=Path, default=None)
    freeze.add_argument("--frozen-at", required=True, help="ISO instant with offset")

    args = parser.parse_args(argv)
    if args.command == "packet":
        result = build_review_packet(read_jsonl(args.evidence), args.destination)
    elif args.command == "split":
        groups = (json.loads(args.gold_groups.read_text(encoding="utf-8"))
                  if args.gold_groups else {})
        result = temporal_split(read_jsonl(args.evidence), groups, args.cutoff)
        _write_json(args.output, result)
    else:
        result = freeze_record(args.labels, args.evidence, args.split_manifest,
                               args.predictions, args.frozen_at)
        _write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
