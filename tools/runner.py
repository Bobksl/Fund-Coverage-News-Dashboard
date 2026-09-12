"""Local Phase 2 runner: allowlisted inputs, one engine, validated decisions, frozen predictions.

The manifest carries article IDs and a partition name only. Nothing here reads analyst labels,
gold event groups or challenge categories. Predictions are written before any evaluator joins
them to ground truth, and every candidate leaves an outcome behind: zero silent drops.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from tools import baseline, classifier, corpus, grouping, scoring
from tools.records import (COMPONENTS, dumps_jsonl, leakage_scan, loads, read_jsonl,
                           to_inference_input, validate_decision, write_jsonl)

REVIEW_FIELDS = ("event_id", "recommendation", "total_score", "relevance_level",
                 "primary_event_type", "primary_region", "article_ids", "source_urls",
                 "disposition_reason_codes", "failed_gates", "review_reason")


class BaselineEngine:
    """Deterministic comparison floor. Reads only allowlisted evidence."""

    name = "deterministic_baseline"
    metadata = {"provider": "none", "model": "deterministic_baseline", "prompt_version": None}

    def propose(self, article, config, body=None):
        return baseline.propose(to_inference_input(article, body=body), config)


class ClassifierEngine:
    """Wraps the structured classifier. The provider is injected; the CLI offers replay only."""

    name = "structured_classifier"

    def __init__(self, classifier):
        self.classifier = classifier

    def propose(self, article, config, body=None):
        return self.classifier.propose(article, config, body=body)


def replay_engine(raw_store_path, model_id, prompt_version):
    """Re-derive proposals from saved raw outputs. Cannot reach a model or a network."""
    store = classifier.RawOutputStore(raw_store_path)
    return ClassifierEngine(classifier.StructuredClassifier(
        classifier.ReplayProvider(store), store, model_id, prompt_version, max_attempts=1))


def config_hashes(config_root):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            for path in sorted(Path(config_root).glob("*.json"))}


def _primary(members):
    """Deterministic representative: best accessible evidence, then lowest article ID."""
    def key(member):
        credibility = (member["components"].get("source_credibility") or {}).get("points") or 0
        return (-credibility, member["article_id"])
    return sorted(members, key=key)[0]


def build_decision(cluster, config, run_id, spec_metadata):
    """Assemble one contract decision from a predicted cluster. Python owns every number."""
    members = cluster["members"]
    primary = _primary(members)
    components = {name: dict(primary["components"][name]) for name in COMPONENTS}
    # A stronger source inside the same event improves evidence, so take the best supported anchor.
    best_credibility = max(members,
                           key=lambda m: (m["components"]["source_credibility"]["points"] or 0))
    components["source_credibility"] = dict(best_credibility["components"]["source_credibility"])

    merged = dict(primary, components=components)
    gates, total, recommendation, reasons = scoring.evaluate(merged, config["scoring"])
    if cluster["ambiguous_with"]:
        # An unresolved cluster boundary is a prediction, not a merge; it goes to review.
        # The anchor sum still stands on its own: the gate, not the total, carries the verdict.
        gates = dict(gates, identity="review_required")
        recommendation = "review_required"
        reasons = sorted(set(reasons) | {"ambiguous_identity"})
    if cluster["duplicate_article_ids"]:
        reasons = sorted(set(reasons) | {"duplicate"})
    decision = {
        "event_id": cluster["cluster_id"], "revision": 1,
        "decision_id": f"{run_id}:{cluster['cluster_id']}", "run_id": run_id,
        "attempt": max((member.get("attempts") or [{"attempt": 1}])[-1]["attempt"] for member in members),
        "article_ids": cluster["article_ids"], "claim_ids": [],
        "event_identity": primary["event_identity"],
        "direct_entity_ids": sorted({value for member in members for value in member["direct_entity_ids"]}),
        "propagated_entity_ids": sorted({value for member in members
                                         for value in member["propagated_entity_ids"]}),
        "entity_matches": [match for member in members for match in member["entity_matches"]],
        "held_status": "monitored",
        "asset_classes": sorted({value for member in members for value in member["asset_classes"]}),
        "sector_ids": sorted({value for member in members for value in member["sector_ids"]}),
        "theme_ids": sorted({value for member in members for value in member["theme_ids"]}),
        "primary_event_type": primary["primary_event_type"], "subtype": primary["subtype"],
        "secondary_event_types": primary["secondary_event_types"],
        "countries": primary["countries"], "primary_region": primary["primary_region"],
        "region_basis": primary["region_basis"], "relevance_level": primary["relevance_level"],
        "eligibility_reason": primary["eligibility_reason"], "transmission": primary["transmission"],
        "gates": gates, "components": components, "total_score": total,
        "recommendation": recommendation, "disposition_reason_codes": reasons,
        "duplicate_of": None, "update_of": None,
        "model_metadata": dict(primary.get("model_metadata") or BaselineEngine.metadata,
                               engine=primary["engine"],
                               raw_output_refs=[member.get("raw_output_ref") for member in members]),
        "spec_metadata": spec_metadata, "analyst_review": None,
        "publication": {"status": "pending_review" if recommendation in scoring.SELECTED
                        else "not_selected", "selection_reason": None},
    }
    return decision


def _review_rows(decisions, evidence):
    rows = []
    for decision in decisions:
        urls = [(evidence.get(article) or {}).get("original_url") for article in decision["article_ids"]]
        rows.append({
            "event_id": decision["event_id"], "recommendation": decision["recommendation"],
            "total_score": "" if decision["total_score"] is None else decision["total_score"],
            "relevance_level": decision["relevance_level"] or "",
            "primary_event_type": decision["primary_event_type"],
            "primary_region": decision["primary_region"],
            "article_ids": " ".join(decision["article_ids"]),
            "source_urls": " ".join(url for url in urls if url),
            "disposition_reason_codes": " ".join(decision["disposition_reason_codes"]),
            "failed_gates": " ".join(sorted(name for name, outcome in decision["gates"].items()
                                            if outcome == "fail")),
            "review_reason": " ".join(sorted(name for name, outcome in decision["gates"].items()
                                             if outcome == "review_required")),
        })
    return rows


def run(manifest, evidence_records, config, engine, output_dir, bodies=None,
        region_history=None, config_root=baseline.CONFIG_ROOT, allow_overwrite=False,
        freeze=None, evidence_path=None, labels_path=None, split_manifest_path=None):
    """Execute one partition end to end and write the frozen prediction set.

    Pass `freeze` (plus whichever of evidence_path/labels_path/split_manifest_path the caller
    holds) to require a custodian preflight before this run claims to operate against a frozen
    corpus: the actual file bytes are re-hashed and compared to the freeze record, so a silently
    edited evidence file cannot pass. Omitting `freeze` keeps prior behaviour for synthetic/local
    runs that have no freeze yet.
    """
    leaks = leakage_scan(manifest)
    if leaks:
        raise ValueError(f"Manifest carries evaluator-only fields: {leaks}")
    if freeze is not None:
        corpus.verify_freeze(freeze, evidence_path, labels_path, split_manifest_path)
    bodies = bodies or {}
    evidence = {record["article_id"]: record for record in evidence_records}
    missing = [article_id for article_id in manifest["article_ids"] if article_id not in evidence]
    if missing:
        raise KeyError(f"Manifest references evidence that is not present: {missing}")

    run_id = manifest["run_id"]
    spec_metadata = {"config_hashes": config_hashes(config_root),
                     "scoring_version": config["scoring"]["schema_version"],
                     "partition": manifest["partition"],
                     "freeze_verified": freeze is not None,
                     "frozen_at": (freeze or {}).get("frozen_at")}
    proposals = [engine.propose(evidence[article_id], config, body=bodies.get(article_id))
                 for article_id in sorted(manifest["article_ids"])]
    clusters = grouping.group(proposals, evidence)
    theme_candidates = sorted({theme for proposal in proposals
                               for theme in proposal.get("theme_candidates") or []})
    decisions, invalid = [], []
    for cluster in clusters:
        decision = build_decision(cluster, config, run_id, spec_metadata)
        errors = validate_decision(decision, set(evidence))
        if errors:
            # A contract violation is an operational failure that is surfaced, never dropped.
            decision["gates"] = {name: "review_required" for name in decision["gates"]}
            decision["recommendation"] = "review_required"
            decision["disposition_reason_codes"] = sorted(
                set(decision["disposition_reason_codes"]) | {"draft_invalid"})
            invalid.append({"event_id": decision["event_id"], "errors": errors})
        decisions.append(decision)

    ranked = scoring.rank(decisions, config["scoring"], region_history)
    edition = scoring.select_edition(ranked, config["scoring"], region_history)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "predictions.jsonl", ranked, allow_overwrite=allow_overwrite)
    with (output_dir / "review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(_review_rows(ranked, evidence))
    report = {
        "run_id": run_id, "partition": manifest["partition"], "engine": engine.name,
        "articles_in": len(manifest["article_ids"]),
        "articles_with_outcome": sum(len(d["article_ids"]) for d in decisions),
        "predicted_events": len(decisions),
        "recommendations": {value: sum(d["recommendation"] == value for d in decisions)
                            for value in sorted({d["recommendation"] for d in decisions})},
        "selected": [d["event_id"] for d in edition["selected"]],
        "overflow": [d["event_id"] for d in edition["overflow"]],
        "urgent_review": [d["event_id"] for d in edition["urgent_review"]],
        "ambiguous_clusters": [c["cluster_id"] for c in clusters if c["ambiguous_with"]],
        "unassigned_theme_candidates": theme_candidates,
        "duplicate_articles": sorted({a for c in clusters for a in c["duplicate_article_ids"]}),
        "invalid_decisions": invalid,
        "below_daily_target": edition["below_target"],
        "europe_share_trailing": edition["europe_share"],
        "spec_metadata": spec_metadata,
        "limits": "Predictions only. No analyst labels were read and no performance is claimed.",
    }
    (output_dir / "run-report.json").write_bytes(
        json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    (output_dir / "predictions-sha256.txt").write_text(
        hashlib.sha256(dumps_jsonl(ranked).encode("utf-8")).hexdigest() + "  predictions.jsonl\n",
        encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON with run_id, partition and article_ids")
    parser.add_argument("evidence", type=Path, help="JSONL evidence records")
    parser.add_argument("output", type=Path)
    parser.add_argument("--bodies", type=Path, default=None,
                        help="Optional JSON map of article_id to permitted evidence text")
    parser.add_argument("--engine", choices=("baseline", "replay"), default="baseline",
                        help="baseline runs the deterministic floor; replay re-derives proposals "
                             "from saved raw outputs. Live inference needs a provider injected in "
                             "code and is not available from this command.")
    parser.add_argument("--raw-store", type=Path, default=None, help="Saved raw outputs for replay")
    parser.add_argument("--model", default=None, help="Exact model snapshot used for the saved run")
    parser.add_argument("--prompt-version", default=None, help="Prompt version of the saved run")
    args = parser.parse_args(argv)
    if args.engine == "replay" and not (args.raw_store and args.model and args.prompt_version):
        parser.error("replay needs --raw-store, --model and --prompt-version")
    engine = (BaselineEngine() if args.engine == "baseline"
              else replay_engine(args.raw_store, args.model, args.prompt_version))
    config = baseline.load_config()
    manifest = loads(args.manifest.read_text(encoding="utf-8"))
    bodies = loads(args.bodies.read_text(encoding="utf-8")) if args.bodies else {}
    report = run(manifest, read_jsonl(args.evidence), config, engine, args.output, bodies=bodies)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
