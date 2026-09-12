"""Live-shaped structured-classifier run: the reproducible entry point Phase 5 handover section
5C asks for (`tools/run_model_experiment.py`). `tools/runner.py`'s CLI only exposes baseline and
replay engines; this adds the third leg -- an actual provider call -- without duplicating any of
runner.run's grouping/scoring/decision logic.

Every run:
1. Loads the frozen evidence and builds an inference-safe manifest (tools.corpus.inference_manifest),
   which re-verifies the freeze hashes before anything is sent anywhere.
2. Instantiates exactly one authorized provider (currently tools.providers.anthropic_provider) --
   or, with --replay, reads only from an existing RawOutputStore and never calls a model.
3. Runs tools.runner.run with a ClassifierEngine wrapping tools.classifier.StructuredClassifier,
   which performs the actual classification, grouping, scoring and decision-building.
4. Writes a run manifest recording the provider, exact model ID, canonical inference settings and
   every config/prompt/evidence hash involved, alongside runner's own predictions/run-report.

No label, event group or evaluator file is read anywhere in this module -- article_ids and body
text are the only inputs threaded to the classifier, matching tools.records.INFERENCE_ALLOWLIST.
"""
import argparse
import json
import time
from pathlib import Path

from tools import baseline, classifier, corpus, runner
from tools.records import loads, read_jsonl

DEFAULT_PROMPT_VERSION = "p1"


def _read_bodies(evidence_store_dir, evidence_records):
    """Read permitted excerpt/full-text bodies from the local evidence store, when present.

    A record with no matching body file (metadata_only, or simply not captured to disk) is passed
    through with body=None; the classifier's own contract does not require one.
    """
    bodies = {}
    store = Path(evidence_store_dir) if evidence_store_dir else None
    if store is None:
        return bodies
    for record in evidence_records:
        ref = record.get("evidence_local_ref")
        if not ref:
            continue
        candidate = Path(ref)
        if not candidate.is_absolute():
            candidate = store / Path(ref).name
        if candidate.exists():
            bodies[record["article_id"]] = candidate.read_text(encoding="utf-8", errors="replace")
    return bodies


def build_provider(provider_name, model_id, **provider_kwargs):
    """Instantiate exactly one authorized provider. Raises a precise, actionable error otherwise.

    This is deliberately not a plugin registry: Phase 5 handover section 8 authorizes exactly one
    real provider per experiment, chosen and authorized by the user at run time, not guessed here.
    """
    if provider_name == "anthropic":
        from tools.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(model_id, **provider_kwargs)
    raise ValueError(f"Unknown or unauthorized provider {provider_name!r}. Exactly one provider "
                     f"must be explicitly named and authorized before a billed run.")


def run_experiment(run_id, partition, manifest_article_ids, evidence_path, freeze_path,
                   output_dir, config_root=baseline.CONFIG_ROOT, evidence_store_dir=None,
                   raw_store_dir=None, prompt_version=DEFAULT_PROMPT_VERSION, provider_name=None,
                   model_id=None, inference_settings=None, replay=False, max_attempts=2):
    """Run one partition through the structured classifier and write predictions + a run manifest.

    With `replay=True`, provider_name/model_id are still required (they identify which saved raw
    outputs to read) but no provider is instantiated and no network call can occur -- a missing
    saved output fails loudly (tools.classifier.ReplayProvider), never silently falling back to a
    live call.
    """
    evidence_records = read_jsonl(evidence_path)
    freeze = loads(Path(freeze_path).read_text(encoding="utf-8")) if freeze_path else None
    manifest = corpus.inference_manifest(
        freeze, run_id, partition, manifest_article_ids, config_root,
        prompt_version=prompt_version, model_id=model_id,
        evidence_path=evidence_path if freeze else None)

    raw_store_dir = raw_store_dir or (Path(output_dir) / "raw-outputs")
    store = classifier.RawOutputStore(raw_store_dir)
    if replay:
        provider = classifier.ReplayProvider(store)
    else:
        provider = build_provider(provider_name, model_id)

    settings = classifier.build_inference_settings(
        provider=provider_name, model_id=model_id, prompt_version=prompt_version,
        **(inference_settings or {}))
    live_classifier = classifier.StructuredClassifier(
        provider, store, model_id, prompt_version, max_attempts=max_attempts,
        inference_settings=settings)
    engine = runner.ClassifierEngine(live_classifier)

    bodies = _read_bodies(evidence_store_dir, evidence_records)
    config = baseline.load_config()
    started = time.perf_counter()
    report = runner.run({"run_id": run_id, "partition": partition,
                         "article_ids": manifest["article_ids"]},
                        evidence_records, config, engine, output_dir, bodies=bodies,
                        config_root=config_root, freeze=freeze,
                        evidence_path=evidence_path if freeze else None)
    wall_clock_ms = round((time.perf_counter() - started) * 1000, 3)

    predictions = read_jsonl(Path(output_dir) / "predictions.jsonl")
    usage_totals = {"input_tokens": 0, "output_tokens": 0}
    latency_ms_total = 0.0
    provider_failures = 0
    for prediction in predictions:
        metadata = prediction.get("model_metadata") or {}
        usage = metadata.get("usage") or {}
        for key in usage_totals:
            usage_totals[key] += usage.get(key) or 0
        latency_ms_total += metadata.get("latency_ms_total") or 0
        provider_failures += sum(1 for attempt in prediction.get("attempts") or []
                                 if attempt.get("outcome") == "transport_failure")

    run_manifest = {
        "run_id": run_id, "partition": partition, "mode": "replay" if replay else "live",
        "provider": provider_name, "model_id": model_id, "prompt_version": prompt_version,
        "inference_settings": settings, "inference_settings_hash": classifier.settings_hash(settings),
        "inference_preflight": manifest["inference_preflight"],
        "usage_totals": usage_totals, "latency_ms_total": round(latency_ms_total, 3),
        "wall_clock_ms": wall_clock_ms, "provider_transport_failures": provider_failures,
        "cost_basis": None,
        "cost_note": "Cost is reported only from a documented provider rate card. None was "
                     "supplied to this run, so cost stays explicitly unknown rather than invented.",
        "articles_in": report["articles_in"], "predicted_events": report["predicted_events"],
    }
    (Path(output_dir) / "run-manifest.json").write_bytes(
        json.dumps(run_manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    return report, run_manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("partition")
    parser.add_argument("manifest", type=Path, help="JSON list of article_ids, or a manifest "
                        "object with an article_ids field (tools.corpus.runner_manifest output)")
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--freeze", type=Path, default=None,
                        help="freeze-record JSON (tools.corpus freeze); required for any run "
                             "that claims to operate on frozen evidence")
    parser.add_argument("--evidence-store", type=Path, default=None,
                        help="directory of permitted evidence body text files")
    parser.add_argument("--raw-store", type=Path, default=None)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--provider", default="anthropic")
    parser.add_argument("--model", required=True, help="exact model ID/snapshot; never guessed")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-output-tokens", type=int, default=None)
    parser.add_argument("--replay", action="store_true",
                        help="Read only from --raw-store; no network call is possible")
    args = parser.parse_args(argv)

    manifest_data = loads(args.manifest.read_text(encoding="utf-8"))
    article_ids = (manifest_data["article_ids"] if isinstance(manifest_data, dict)
                  else manifest_data)

    settings_overrides = {key: value for key, value in {
        "temperature": args.temperature, "top_p": args.top_p, "seed": args.seed,
        "max_output_tokens": args.max_output_tokens}.items() if value is not None}

    report, run_manifest = run_experiment(
        args.run_id, args.partition, article_ids, args.evidence, args.freeze, args.output,
        evidence_store_dir=args.evidence_store, raw_store_dir=args.raw_store,
        prompt_version=args.prompt_version, provider_name=args.provider, model_id=args.model,
        inference_settings=settings_overrides, replay=args.replay)
    print(json.dumps({"run_manifest": run_manifest, "run_report_summary":
                      {k: report[k] for k in ("recommendations", "selected", "invalid_decisions")}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
