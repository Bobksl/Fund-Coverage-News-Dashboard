"""Phase 7 frozen scope (ticket P7-1): freeze-001's 188/56/30 membership as hashed run manifests.

docs/phase-7-scope.md is the canonical statement of what this writes and why. The governing scope
is exactly the three ID lists already frozen in freeze-001's split manifest -- Stage A calibration,
Stage B/C holdout, Stage D challenge -- never the broader 91-record challenge registry.

Only ID projections are read: the split manifest's lists, each frozen evidence record's article_id
and evidence_hash, each body file's digest, and (for the optional linked diagnostic) the registry's
article_id / linked_natural_feed_article_id. No label, category, selection reason or any other
evaluator-only field is read into or written by this module; freeze-001 is hash-verified and never
modified.
"""
import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

from tools.corpus import verify_freeze
from tools.evidence_capture import digest
from tools.records import dumps_jsonl, leakage_scan, loads, read_jsonl

SCOPE_VERSION = "phase7-scope-v1"

# Removed from the analyst-review-003 packet before labeling, so neither is in freeze-001's split.
# Reasons are the packet manifest's own (work/phase2/analyst-review-003/packet-manifest.json).
EXCLUDED_ARTICLES = {
    "f6400cea-3e84-5bd7-b063-5a3aa338d076":
        "quarantined: identical canonical article already labeled in the starter batch "
        "(45ac5e6b-6cc3-4134-8701-0f7323f35db3), so a fresh label would not be independent",
    "e0f8d0fc-e619-5649-85cb-950a8c028ce9": "no established publication date (unknown)",
}

# (file stem, stage, partition, split-manifest field)
STAGES = (
    ("stage-a-calibration", "A", "calibration", ("natural_feed", "calibration")),
    ("stage-bc-holdout", "B/C", "holdout", ("natural_feed", "holdout")),
    ("stage-d-challenge", "D", "challenge", ("challenge", "article_ids")),
)
FREEZE_001_COUNTS = {"calibration": 188, "holdout": 56, "challenge": 30}
DIAGNOSTIC_STEM = "linked-diagnostic-replay-only"


def _sha256_rows(rows):
    return hashlib.sha256(dumps_jsonl(rows).encode("utf-8")).hexdigest()


def article_ids_sha256(article_ids):
    """Same formula as tools.select_calibration_smoke.build_manifest, over the sorted ID list."""
    return _sha256_rows([{"article_id": article_id} for article_id in sorted(article_ids)])


def evidence_hashes_sha256(article_ids, evidence_by_id):
    return _sha256_rows([{"article_id": article_id,
                          "evidence_hash": evidence_by_id[article_id].get("evidence_hash")}
                         for article_id in sorted(article_ids)])


def verify_bodies(article_ids, evidence_by_id, evidence_store):
    """Recompute each body file's digest against its frozen evidence_hash; return the count.

    Resolves files exactly as tools.run_model_experiment._read_bodies does, so a body that passes
    here is the body a run would load. A hashed record without a file, or a file without a hash,
    is refused rather than skipped.
    """
    verified = 0
    for article_id in sorted(article_ids):
        record = evidence_by_id[article_id]
        ref = record.get("evidence_local_ref")
        candidate = None
        if ref:
            candidate = Path(ref) if Path(ref).is_absolute() else Path(evidence_store) / Path(ref).name
        exists = candidate is not None and candidate.exists()
        if bool(record.get("evidence_hash")) != exists:
            raise ValueError(f"{article_id}: evidence_hash and body file disagree on presence")
        if not exists:
            continue
        text = candidate.read_text(encoding="utf-8", errors="replace")
        if digest(text) != record["evidence_hash"]:
            raise ValueError(f"{article_id}: body no longer matches its frozen evidence_hash")
        verified += 1
    return verified


def linked_diagnostic(registry_rows, members, evidence_by_id, source, generated_at,
                      excluded=EXCLUDED_ARTICLES):
    """The replay-only view of registry probes that are also frozen natural-feed articles."""
    # ID projection first: nothing else from a registry row is kept past this line.
    projection = [(row["article_id"], row.get("linked_natural_feed_article_id"))
                  for row in registry_rows]
    natural = members["calibration"] | members["holdout"]
    linked = {link for _, link in projection if link}
    independent = {article_id for article_id, link in projection if not link}
    stray = ((linked - natural) | (independent - members["challenge"])) - excluded.keys()
    if stray:
        raise ValueError(f"Registry IDs outside freeze-001 and not recorded exclusions: "
                         f"{sorted(stray)}")
    if members["challenge"] - independent:
        raise ValueError("Frozen challenge IDs are missing from the registry's independent probes")
    ids = sorted(linked & natural)
    diagnostic = {
        "scope_version": SCOPE_VERSION,
        "diagnostic": "linked_natural_feed_registry_probes",
        "replay_only": True,
        "run_policy": "Replay-only view over Stage A and Stage B/C raw outputs. Never a live or "
                      "billed run, never pooled into the 274-input frozen comparison.",
        "generated_at": generated_at,
        "source": dict(source, registry_projection="article_id, linked_natural_feed_article_id"),
        "article_ids": ids,
        "article_count": len(ids),
        "article_ids_sha256": article_ids_sha256(ids),
        "evidence_hashes_sha256": evidence_hashes_sha256(ids, evidence_by_id),
        "stage_membership": {"calibration": len(members["calibration"].intersection(ids)),
                             "holdout": len(members["holdout"].intersection(ids))},
        "excluded_linked_article_ids": sorted(linked & excluded.keys()),
    }
    reconciliation = {
        "registry_rows": len(projection),
        "linked_natural_feed_probes": len(linked),
        "linked_in_frozen_natural_feed": len(ids),
        "linked_excluded": sorted(linked & excluded.keys()),
        "independent_probes": len(independent),
        "independent_in_frozen_challenge": len(independent & members["challenge"]),
        "independent_excluded": sorted(independent & excluded.keys()),
        "unique_inputs_if_all_registry_probes_were_run":
            len(set().union(*members.values()) | linked | independent),
    }
    return diagnostic, reconciliation


def build_scope(split, evidence_records, freeze, generated_at, registry_rows=None,
                evidence_store=None, excluded=EXCLUDED_ARTICLES):
    """Return (scope record, {file stem: manifest}) or raise on any reconciliation failure."""
    evidence_by_id = {}
    for record in evidence_records:
        if record["article_id"] in evidence_by_id:
            raise ValueError(f"Duplicate frozen evidence record: {record['article_id']}")
        evidence_by_id[record["article_id"]] = record

    members = {}
    for _, _, partition, (group, field) in STAGES:
        ids = split[group][field]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{partition}: duplicate article IDs")
        barred = set(ids) & excluded.keys()
        if barred:
            raise ValueError(f"{partition}: recorded exclusions cannot enter the frozen "
                             f"comparison: {sorted(barred)}")
        missing = set(ids) - evidence_by_id.keys()
        if missing:
            raise ValueError(f"{partition}: no frozen evidence record for {sorted(missing)}")
        members[partition] = set(ids)
    for (left, left_ids), (right, right_ids) in combinations(members.items(), 2):
        if left_ids & right_ids:
            raise ValueError(f"{left} and {right} overlap: {sorted(left_ids & right_ids)}")
    scope_ids = set().union(*members.values())

    source = {"freeze_frozen_at": freeze.get("frozen_at"),
              "split_manifest_sha256": freeze.get("split_manifest_sha256"),
              "evidence_sha256": freeze.get("evidence_sha256")}
    manifests = {}
    for stem, stage, partition, (group, field) in STAGES:
        ids = sorted(members[partition])
        manifests[stem] = {
            "scope_version": SCOPE_VERSION, "stage": stage, "partition": partition,
            "generated_at": generated_at,
            "source": dict(source, split_manifest_field=f"{group}.{field}"),
            "article_ids": ids, "article_count": len(ids),
            "article_ids_sha256": article_ids_sha256(ids),
            "evidence_hashes_sha256": evidence_hashes_sha256(ids, evidence_by_id),
        }
    record = {
        "scope_version": SCOPE_VERSION, "generated_at": generated_at, "source": source,
        "governing_counts": dict({partition: len(ids) for partition, ids in members.items()},
                                 unique_classifier_inputs=len(scope_ids)),
        "excluded_articles": [{"article_id": article_id, "reason": reason}
                              for article_id, reason in sorted(excluded.items())],
        "bodies_verified": (verify_bodies(scope_ids, evidence_by_id, evidence_store)
                            if evidence_store else None),
        "registry_reconciliation": None,
    }
    if registry_rows is not None:
        manifests[DIAGNOSTIC_STEM], record["registry_reconciliation"] = linked_diagnostic(
            registry_rows, members, evidence_by_id, source, generated_at, excluded)
    for name, payload in [("scope-record", record), *manifests.items()]:
        leaks = leakage_scan(payload)
        if leaks:
            raise ValueError(f"{name} carries evaluator-only fields: {leaks}")
    return record, manifests


def check_run_manifest(manifest_data, partition, replay):
    """Run-entry guard for tools.run_model_experiment.main, called before any provider exists.

    Refuses a replay-only manifest on a live path, a manifest whose IDs no longer match its own
    recorded hash, a scope manifest run under a different partition name, and any scope manifest
    carrying a recorded exclusion. A plain JSON ID list carries none of these markers and passes.
    """
    if not isinstance(manifest_data, dict):
        return
    if manifest_data.get("replay_only") and not replay:
        raise ValueError("Replay-only diagnostic manifest: it never gets a live or billed run; "
                         "use --replay against an existing raw store")
    recorded = manifest_data.get("article_ids_sha256")
    if recorded is not None and article_ids_sha256(manifest_data["article_ids"]) != recorded:
        raise ValueError("Manifest article_ids no longer match its recorded article_ids_sha256")
    if manifest_data.get("scope_version") is None:
        return
    if manifest_data.get("partition") not in (None, partition):
        raise ValueError(f"Manifest is for partition {manifest_data['partition']!r}, "
                         f"not {partition!r}")
    barred = set(manifest_data["article_ids"]) & EXCLUDED_ARTICLES.keys()
    if barred:
        raise ValueError(f"Recorded exclusions cannot enter the frozen comparison: {sorted(barred)}")


def write_scope(output_dir, record, manifests):
    """Write every manifest plus the scope record; refuse to overwrite any existing file."""
    output_dir = Path(output_dir)
    encoded = {f"{stem}.json": json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
               for stem, payload in manifests.items()}
    existing = [name for name in [*encoded, "scope-record.json"] if (output_dir / name).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite frozen scope files in {output_dir}: {existing}")
    record = dict(record, manifests={
        name: {"file_sha256": hashlib.sha256(data).hexdigest(),
               "article_count": manifests[name[:-5]]["article_count"],
               "article_ids_sha256": manifests[name[:-5]]["article_ids_sha256"]}
        for name, data in encoded.items()})
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in encoded.items():
        (output_dir / name).write_bytes(data)
    (output_dir / "scope-record.json").write_bytes(
        json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8"))
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freeze_dir", type=Path,
                        help="freeze-001 directory (freeze-record.json, split-manifest.json, "
                             "evidence.jsonl); its counts must be freeze-001's 188/56/30")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--generated-at", required=True, help="ISO instant with offset")
    parser.add_argument("--evidence-store", type=Path, default=None,
                        help="body text directory; every scoped body is digest-verified")
    parser.add_argument("--registry", type=Path, default=None,
                        help="challenge registry; only article_id and "
                             "linked_natural_feed_article_id are read")
    args = parser.parse_args(argv)

    freeze = loads((args.freeze_dir / "freeze-record.json").read_text(encoding="utf-8"))
    split_path = args.freeze_dir / "split-manifest.json"
    evidence_path = args.freeze_dir / "evidence.jsonl"
    verify_freeze(freeze, evidence_path, split_manifest_path=split_path)
    split = loads(split_path.read_text(encoding="utf-8"))
    registry = None
    if args.registry:
        registry = [{"article_id": row["article_id"],
                     "linked_natural_feed_article_id": row.get("linked_natural_feed_article_id")}
                    for row in read_jsonl(args.registry)]
    record, manifests = build_scope(split, read_jsonl(evidence_path), freeze, args.generated_at,
                                    registry_rows=registry, evidence_store=args.evidence_store)
    counts = {partition: record["governing_counts"][partition] for partition in FREEZE_001_COUNTS}
    if counts != FREEZE_001_COUNTS:
        raise ValueError(f"Not freeze-001's governing scope: {counts}")
    record = write_scope(args.output_dir, record, manifests)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
