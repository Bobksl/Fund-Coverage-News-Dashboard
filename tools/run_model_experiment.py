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
import os
import time
from pathlib import Path

from tools import baseline, classifier, corpus, phase7_scope, runner
from tools.records import loads, read_jsonl

# p2: the one calibration-smoke-driven repair (docs/phase-5-review-decisions.md) -- an explicit
# evidence_refs format instruction, added after every non-crashed smoke response across 8 of 9
# articles used a label ("title"/"body") or a quoted excerpt instead of the required article_id.
DEFAULT_PROMPT_VERSION = "p2"


def _account_articles(rows):
    totals = {"input_tokens": 0, "output_tokens": 0}
    incremental = dict(totals)
    unknown = {key: False for key in totals}
    incremental_unknown = dict(unknown)
    failures = schema_invalid = replayed = 0
    latency = 0.0
    for row in rows:
        attempts = row.get("attempts") or []
        replayed += bool(attempts) and all(a.get("replayed") for a in attempts)
        for attempt in attempts:
            # A replayed "transport_failure" is ReplayProvider deliberately refusing to
            # fabricate a response for a digest/attempt with no saved data -- a local policy
            # refusal, not evidence the live provider's transport is unreliable. Counting it
            # alongside a genuine live network failure would misreport provider health.
            failures += attempt["outcome"] == "transport_failure" and not attempt.get("replayed")
            schema_invalid += attempt["outcome"] in {"schema_invalid", "unparsable"}
            latency += attempt.get("latency_ms", 0)
            for key in totals:
                value = (attempt.get("usage") or {}).get(key)
                if type(value) is int and value >= 0:
                    totals[key] += value
                    if not attempt.get("replayed"):
                        incremental[key] += value
                else:
                    unknown[key] = True
                    if not attempt.get("replayed"):
                        incremental_unknown[key] = True
    return {"usage_totals": {k: None if unknown[k] else v for k, v in totals.items()},
            "known_usage_subtotals": totals,
            "incremental_usage_totals": {k: None if incremental_unknown[k] else v
                                         for k, v in incremental.items()},
            "replayed_articles": replayed, "provider_transport_failures": failures,
            "schema_invalid_attempts": schema_invalid, "latency_ms_total": round(latency, 3)}


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
    if provider_name == "deepseek":
        from tools.providers.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider(model_id, **provider_kwargs)
    raise ValueError(f"Unknown or unauthorized provider {provider_name!r}. Exactly one provider "
                     f"must be explicitly named and authorized before a billed run.")


def run_experiment(run_id, partition, manifest_article_ids, evidence_path, freeze_path,
                   output_dir, config_root=baseline.CONFIG_ROOT, evidence_store_dir=None,
                   raw_store_dir=None, prompt_version=DEFAULT_PROMPT_VERSION, provider_name=None,
                   model_id=None, provider_kwargs=None, inference_settings=None, replay=False,
                   max_attempts=2):
    """Run one partition through the structured classifier and write predictions + a run manifest.

    With `replay=True`, provider_name/model_id are still required (they identify which saved raw
    outputs to read) but no provider is instantiated and no network call can occur -- a missing
    saved output fails loudly (tools.classifier.ReplayProvider), never silently falling back to a
    live call. `provider_kwargs` (e.g. {"max_output_tokens": 8192, "temperature": 0}) are passed
    straight to the provider constructor -- this is how a reasoning model's `reasoning_content`
    budget (which counts against max_tokens on top of the visible JSON) gets enough headroom.
    """
    evidence_records = read_jsonl(evidence_path)
    freeze = loads(Path(freeze_path).read_text(encoding="utf-8")) if freeze_path else None
    manifest = corpus.inference_manifest(
        freeze, run_id, partition, manifest_article_ids, config_root,
        prompt_version=prompt_version, model_id=model_id,
        evidence_path=evidence_path if freeze else None)

    raw_store_dir = raw_store_dir or (Path(output_dir) / "raw-outputs")
    store = classifier.RawOutputStore(raw_store_dir)
    kwargs = dict(provider_kwargs or {})
    declared = dict(inference_settings or {})
    request_fields = {"max_output_tokens", "temperature", "top_p", "thinking", "reasoning_effort",
                      "timeout_seconds"}
    for key in request_fields & declared.keys():
        if key in kwargs and kwargs[key] != declared[key]:
            raise ValueError(f"Provider request and declared settings disagree: {key}")
        kwargs[key] = declared[key]
    if replay:
        provider = classifier.ReplayProvider(store)
        if provider_name == "deepseek":
            from tools.providers.deepseek_provider import DeepSeekProvider
            declared = dict(DeepSeekProvider(model_id, **kwargs).inference_settings(), **declared)
    else:
        provider = build_provider(provider_name, model_id, **kwargs)
        if hasattr(provider, "inference_settings"):
            effective = provider.inference_settings()
            for key in declared.keys() & effective.keys():
                if declared[key] != effective[key]:
                    raise ValueError(f"Effective request and declared settings disagree: {key}")
            declared = dict(declared, **effective)

    declared.pop("provider", None)
    declared.pop("model_id", None)
    declared.pop("prompt_version", None)
    declared["retry_policy"] = dict(declared.get("retry_policy") or {}, schema_max_attempts=max_attempts)
    declared["schema_version"] = classifier.RESPONSE_CONTRACT_VERSION
    settings = classifier.build_inference_settings(
        provider=provider_name, model_id=model_id, prompt_version=prompt_version,
        **declared)
    live_classifier = classifier.StructuredClassifier(
        provider, store, model_id, prompt_version, max_attempts=max_attempts,
        inference_settings=settings)
    engine = runner.ClassifierEngine(live_classifier)

    bodies = _read_bodies(evidence_store_dir, evidence_records)
    config = baseline.load_config(config_root)
    output_dir = Path(output_dir)
    if (output_dir / "predictions.jsonl").exists():
        raise FileExistsError("Completed prediction file already exists; use a new run directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    article_ledger = output_dir / "article-attempts.jsonl"
    existing = {r["article_id"]: r for r in read_jsonl(article_ledger)} if article_ledger.exists() else {}

    def save_article(proposal):
        if proposal["article_id"] in existing:
            old = existing[proposal["article_id"]]
            if old["model_metadata"]["input_hash"] != proposal["model_metadata"]["input_hash"]:
                raise ValueError("Interrupted run's article ledger belongs to different inputs/settings")
            return
        with article_ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(proposal, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    started = time.perf_counter()
    report = runner.run({"run_id": run_id, "partition": partition,
                         "article_ids": manifest["article_ids"]},
                        evidence_records, config, engine, output_dir, bodies=bodies,
                        config_root=config_root, freeze=freeze,
                        evidence_path=evidence_path if freeze else None, proposal_sink=save_article)
    wall_clock_ms = round((time.perf_counter() - started) * 1000, 3)

    accounting = _account_articles(read_jsonl(article_ledger))

    run_manifest = {
        "run_id": run_id, "partition": partition, "mode": "replay" if replay else "live",
        "provider": provider_name, "model_id": model_id, "prompt_version": prompt_version,
        "inference_settings": settings, "inference_settings_hash": classifier.settings_hash(settings),
        "inference_preflight": manifest["inference_preflight"],
        **accounting, "wall_clock_ms": wall_clock_ms,
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
    # P7-1 (docs/phase-7-scope.md): refuse a replay-only, tampered, mislabelled or exclusion-bearing
    # scope manifest before any provider can be constructed.
    phase7_scope.check_run_manifest(manifest_data, args.partition, args.replay)
    article_ids =(manifest_data["article_ids"] if isinstance(manifest_data, dict)
                  else manifest_data)

    settings_overrides = {key: value for key, value in {
        "temperature": args.temperature, "top_p": args.top_p, "seed": args.seed,
        "max_output_tokens": args.max_output_tokens}.items() if value is not None}

    report, run_manifest = run_experiment(
        args.run_id, args.partition, article_ids, args.evidence, args.freeze, args.output,
        evidence_store_dir=args.evidence_store, raw_store_dir=args.raw_store,
        prompt_version=args.prompt_version, provider_name=args.provider, model_id=args.model,
        provider_kwargs=settings_overrides, inference_settings=settings_overrides,
        replay=args.replay)
    print(json.dumps({"run_manifest": run_manifest, "run_report_summary":
                      {k: report[k] for k in ("recommendations", "selected", "invalid_decisions")}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
