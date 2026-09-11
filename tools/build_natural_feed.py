"""Assemble recorded natural-feed observations into contract-valid evidence and a coverage report.

Reads the per-source observation files a person produced while enumerating the fixed indexes by
hand, normalizes them through tools.collection and writes the cohort's evidence, gaps and intake
report. Performs no retrieval of its own.
"""
import argparse
import json
from pathlib import Path

from tools import collection

DEFAULT_ROOT = Path("work/phase2/natural-feed")


def load_sources(manifest):
    return {source["source_id"]: source for source in manifest["sources"]}


def build(root=DEFAULT_ROOT):
    root = Path(root)
    manifest = json.loads((root / "collection-manifest.json").read_text(encoding="utf-8"))
    errors = collection.validate_manifest(manifest)
    if errors:
        raise SystemExit(f"Frozen manifest is invalid: {errors}")
    sources = load_sources(manifest)

    records, gaps, out_of_window = [], [], 0
    for path in sorted((root / "observations").glob("*.json")):
        observation_file = json.loads(path.read_text(encoding="utf-8"))
        source_id = observation_file["source_id"]
        source = sources.get(source_id)
        if source is None:
            raise SystemExit(f"{path.name}: {source_id} is not in the frozen roster")
        retrieved_at = observation_file["retrieved_at"]
        for entry in observation_file.get("entries", []):
            record = collection.to_evidence(entry, source, retrieved_at)
            if not collection.in_window(record["published_at"], manifest):
                out_of_window += 1
                continue
            records.append(record)
        for excluded in observation_file.get("excluded_out_of_window", []):
            out_of_window += excluded.get("count", 1)

    merged = collection.merge_records(records)
    gaps_path = root / "gaps.jsonl"
    if gaps_path.exists():
        gaps = [json.loads(line) for line in gaps_path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    report = collection.intake_report(manifest, merged, gaps)
    report["entries_seen_outside_window"] = out_of_window
    collection.write_jsonl_safely(root / "evidence.jsonl", merged)
    (root / "intake-report.json").write_bytes(
        json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
