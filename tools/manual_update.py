"""Phase 8 manual update: operator intake, a zero-spend review queue and candidate explanations.

Three separate operator steps, each writing only under its workspace (git-ignored `work/`):

1. `intake`: explicitly supplied source evidence (observations plus the permitted text an operator
   captured) becomes contract-valid evidence through tools.collection and tools.evidence_capture.
   Identical input is a duplicate, not a second article; changed text is reported as changed.
   Every attempt is logged and reported as a source check on the published site's status.
2. `classify` (optional, paid): classifies evidence that has no stored response, through an
   injected provider under an explicitly approved spending cap. A cap stop keeps completed work
   and is recorded as its own status. An input that already finished is never sent again.
3. `build-queue`: replays stored responses only (tools.classifier.ReplayProvider cannot reach a
   model) through tools.runner grouping and scoring, then writes queue.json with why each
   candidate was shortlisted, suppressed or sent for review. Stored responses from an earlier run
   are reused only for byte-identical inputs; everything else waits as awaiting_classification.

Nothing here drafts, approves or publishes. The queue is an operator view, never an edition.
"""
import argparse
import hashlib
import json
import os
import shutil
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from tools import (approval_ledger, baseline, classifier, collection, evidence_capture, publication,
                   runner)
from tools.inference_budget import BudgetStop, SpendLedger
from tools.records import (COMPONENTS, INFERENCE_ALLOWLIST, publication_date, read_jsonl,
                           to_inference_input, write_jsonl)

ROOT = Path(__file__).resolve().parent.parent
OPERATOR_SITE = ROOT / "site" / "operator"
OPERATOR_FILES = ("index.html", "queue.js")
DEFAULT_WORKSPACE = ROOT / "work/phase8/workspace"
DEFAULT_OPERATOR_DIR = ROOT / "work/phase8/operator"
# The exact profile of calib-smoke-deepseek-flash-v3 (frozen prompt p2), so its stored responses
# replay for byte-identical inputs. A different profile hashes differently and reuses nothing.
DEFAULT_PROFILE = {"provider": "deepseek", "model_id": "deepseek-flash", "prompt_version": "p2",
                   "inference_settings": {"provider": "deepseek", "model_id": "deepseek-flash",
                                          "max_output_tokens": 16384, "prompt_version": "p2"},
                   "max_attempts": 2}
OBSERVATION_FIELDS = ("url", "title", "publisher", "originating_publisher", "source_kind",
                      "published_at", "published_date_precision", "event_date", "access_status",
                      "supersedes_article_id")
BUCKETS = {"priority_shortlist": "shortlisted", "shortlist": "shortlisted",
           "reserve_manual_only": "reserve", "review_required": "review", "suppress": "suppressed"}
BUCKET_ORDER = ("shortlisted", "reserve", "review", "suppressed")
REASON_TEXT = {
    "shortlisted": "Every gate passed and the score falls in a shortlist band.",
    "below_band": "Every gate passed, but the score is below the shortlist bands.",
    "no_relevance": "No A/B/C connection to a monitored manager, sector or transmission path was established.",
    "routine_activity": "Routine activity without a material new fact.",
    "insufficient_evidence": "Source credibility is below the minimum needed to rely on this evidence.",
    "ambiguous_identity": "The entity or event identity is unresolved; a person must confirm it.",
    "conflicting_evidence": "Evidence is missing, unscorable or conflicting, so the gates could not be evaluated.",
    "duplicate": "Another captured article reports the same event and was grouped with it.",
    "no_new_fact": "Novelty is below the minimum; no new fact was reported.",
    "below_materiality": "Materiality is below the minimum anchor.",
    "weak_transmission": "The investment transmission path is weaker than this relevance level requires.",
    "capacity": "Shortlisted, but outside the daily capacity target.",
    "critical_review": "A tracked critical event type is always surfaced for review, never silently suppressed.",
    "override_approved": "An analyst override was recorded.",
    "draft_invalid": "The model output or the assembled decision failed validation.",
}
AWAITING_REASON = ("There is no stored model response for this exact input. Classifying it needs a "
                   "paid call under an explicitly approved spending cap (manual_update classify).")
QUEUE_LIMITS = ("Candidates and explanations only. Component reasons are untrusted model output; "
                "gates, totals and bands are computed deterministically from the anchors. No model "
                "was called to build this queue, and nothing in it is approved or published.")


class WorkspaceLocked(RuntimeError):
    """Another manual update run holds the workspace."""


@contextmanager
def _locked(workspace):
    workspace.mkdir(parents=True, exist_ok=True)
    lock = workspace / ".lock"
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise WorkspaceLocked(f"{lock} is held by another run; inspect it before removing it") from error
    try:
        yield
    finally:
        os.close(handle)
        lock.unlink()


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
    os.replace(temporary, path)


def _append_jsonl(path, row):
    with Path(path).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_evidence(workspace):
    """Return (evidence records, permitted body text by article_id) for a workspace."""
    workspace = Path(workspace)
    path = workspace / "evidence.jsonl"
    records = read_jsonl(path) if path.exists() else []
    bodies = {}
    for record in records:
        ref = record.get("evidence_local_ref")
        if ref and (workspace / ref).exists():
            bodies[record["article_id"]] = (workspace / ref).read_text(encoding="utf-8")
    return records, bodies


def _batch_problems(batch, read_error):
    if read_error:
        return [f"batch could not be read: {read_error}"]
    if not isinstance(batch, dict):
        return ["batch must be a JSON object"]
    problems = [f"batch missing {field}" for field in ("source_id", "tier", "publisher")
                if not batch.get(field)]
    if batch.get("tier") and batch["tier"] not in collection.TIER_SOURCE_KINDS:
        problems.append(f"unknown tier {batch['tier']!r}")
    if not isinstance(batch.get("items"), list) or not batch["items"]:
        problems.append("batch has no items")
    return problems


def _capture_item(workspace, item, source, checked_at):
    if not isinstance(item, dict):
        return None, ["item must be an object"]
    try:
        observation = {field: item[field] for field in OBSERVATION_FIELDS if field in item}
        record = collection.to_evidence(observation, source, checked_at)
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        return None, [f"{type(error).__name__}: {error}"]
    record["discovery_method"] = f"operator_supplied:{source['source_id']}"
    capture = {"article_id": record["article_id"], "text": item.get("text"),
               "mode": item.get("capture_mode", "full"), "gated": item.get("gated"),
               "access_status": item.get("access_status")}
    updated, report = evidence_capture.apply_captures(
        [record], [capture], workspace / "evidence-store", store_prefix="evidence-store")
    if report["invalid"]:
        return None, report["invalid"][0]["errors"]
    return updated[0], []


def _projection(record):
    """What a classifier would see, plus the evidence hash: equal projections are duplicates."""
    return dict({key: record.get(key) for key in INFERENCE_ALLOWLIST if key != "body"},
                evidence_hash=record.get("evidence_hash"))


def intake(workspace, batch, checked_at, site_dir=None, read_error=None):
    """Record one operator-supplied batch. Returns the attempt report; never classifies."""
    workspace = Path(workspace)
    with _locked(workspace):
        report = {"checked_at": checked_at, "source_id": None, "new": [], "changed": [],
                  "duplicate": [], "invalid": []}
        problems = _batch_problems(batch, read_error)
        if not problems:
            report["source_id"] = batch["source_id"]
            source = {key: batch[key] for key in ("source_id", "tier", "publisher")}
            records = {record["article_id"]: record for record in load_evidence(workspace)[0]}
            for index, item in enumerate(batch["items"]):
                record, errors = _capture_item(workspace, item, source, checked_at)
                if errors:
                    report["invalid"].append({"index": index, "errors": errors})
                    continue
                article_id = record["article_id"]
                previous = records.get(article_id)
                if previous is not None and _projection(previous) == _projection(record):
                    report["duplicate"].append(article_id)
                    continue
                if previous is None:
                    report["new"].append(article_id)
                else:
                    report["changed"].append({"article_id": article_id,
                                              "previous_evidence_hash": previous["evidence_hash"],
                                              "new_evidence_hash": record["evidence_hash"]})
                    record["first_seen_at"] = previous["first_seen_at"]
                records[article_id] = record
            if report["new"] or report["changed"] or report["duplicate"]:
                write_jsonl(workspace / "evidence.jsonl", [records[key] for key in sorted(records)],
                            allow_overwrite=True)
            else:
                problems = ["no valid item in the batch"]
        report["status"] = "failed" if problems else "succeeded"
        report["problems"] = problems
        _append_jsonl(workspace / "intake-attempts.jsonl", report)
    if site_dir is not None:
        if problems:
            publication.record_source_check(site_dir, checked_at, "failed", detail="; ".join(problems))
        else:
            skipped = f"{len(report['duplicate'])} duplicate, {len(report['invalid'])} invalid"
            publication.record_source_check(site_dir, checked_at, "succeeded", detail=skipped,
                                            new_items=len(report["new"]) + len(report["changed"]))
    return report


def input_digest(record, body, config, profile):
    """The classifier's own input hash for this record under this profile."""
    prompt = classifier.build_prompt(to_inference_input(record, body=body), config,
                                     profile["prompt_version"])
    return classifier.input_hash(prompt, profile["model_id"], profile["inference_settings"])


def _classifier(provider, store, profile):
    return classifier.StructuredClassifier(
        provider, store, profile["model_id"], profile["prompt_version"],
        max_attempts=profile["max_attempts"], inference_settings=profile["inference_settings"])


def _import_reused(workspace, store, digests, reuse_stores):
    """Copy stored responses for byte-identical inputs from earlier runs; sources stay untouched."""
    for article_id, digest in sorted(digests.items()):
        if store.load(digest, 1) is not None:
            continue
        for root in reuse_stores:
            files = sorted(Path(root).glob(f"{digest}-*.json"))
            if not (Path(root) / f"{digest}-1.json").exists():
                continue
            for path in files:
                shutil.copyfile(path, store.root / path.name)
            _append_jsonl(workspace / "reused-responses.jsonl",
                          {"article_id": article_id, "input_hash": digest, "source_store": str(root),
                           "files": [path.name for path in files]})
            break


def classify_pending(workspace, config, profile, provider, checked_at, site_dir=None,
                     reuse_stores=()):
    """Classify evidence without a completed stored response. A cap stop keeps completed work."""
    workspace = Path(workspace)
    with _locked(workspace):
        records, bodies = load_evidence(workspace)
        store = classifier.RawOutputStore(workspace / "raw-outputs")
        digests = {r["article_id"]: input_digest(r, bodies.get(r["article_id"]), config, profile)
                   for r in records}
        _import_reused(workspace, store, digests, reuse_stores)
        engine = _classifier(provider, store, profile)
        pending = [r for r in records if store.load(digests[r["article_id"]], "complete") is None]
        classified, stop = [], None
        for record in pending:
            try:
                engine.propose(record, config, body=bodies.get(record["article_id"]))
            except BudgetStop as error:
                stop = error
                break
            classified.append(record["article_id"])
        report = {"checked_at": checked_at, "status": "budget_stopped" if stop else "succeeded",
                  "detail": str(stop) if stop else None, "classified": classified,
                  "remaining": [r["article_id"] for r in pending if r["article_id"] not in classified]}
        _append_jsonl(workspace / "classification-attempts.jsonl", report)
    if stop and site_dir is not None:
        publication.record_source_check(
            site_dir, checked_at, "budget_stopped",
            detail=(f"{len(classified)} classified, {len(report['remaining'])} still awaiting; "
                    f"a new spending decision is required"))
    return report


def _run(workspace, store, config, profile, ready, records, bodies, digests):
    """Replay-only runner pass, reused as-is whenever the exact inputs were already run."""
    if not ready:
        return [], {}, None
    identity = json.dumps({"inputs": [[aid, digests[aid]] for aid in ready], "profile": profile},
                          sort_keys=True)
    run_id = "queue-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    output = workspace / "runs" / run_id
    if not (output / "run-report.json").exists():
        shutil.rmtree(output, ignore_errors=True)  # An interrupted replay is free to redo.
        engine = runner.ClassifierEngine(_classifier(classifier.ReplayProvider(store), store, profile))
        runner.run({"run_id": run_id, "partition": "phase8_manual_update", "article_ids": ready},
                   records, config, engine, output, bodies=bodies)
    report = json.loads((output / "run-report.json").read_text(encoding="utf-8"))
    return read_jsonl(output / "predictions.jsonl"), report, run_id


def _ledger_decisions(ledgers):
    rows = {}
    for label in sorted(ledgers):
        for row in approval_ledger.latest_decisions(ledgers[label]).values():
            rows.setdefault(row["event_id"], []).append(
                {"ledger": label, "status": row["status"], "revision": row["revision"],
                 "reviewer_id": row["reviewer_id"], "reviewed_at": row["reviewed_at"]})
    return rows


def _reason_text(code, recommendation):
    # tools.runner keeps the score band's code beside a review verdict (the anchor sum stands on
    # its own); saying "every gate passed" there would contradict the gate that needs a person.
    if recommendation == "review_required" and code == "shortlisted":
        return ("The score alone would fall in a shortlist band, but a gate still needs review, "
                "so a person decides.")
    if recommendation == "review_required" and code == "below_band":
        return ("The score alone would fall below the shortlist bands, and a gate still needs "
                "review, so a person decides.")
    return REASON_TEXT.get(code, "No explanation recorded.")


def explain_decision(decision, scoring, evidence_by_id, edition_position=None, ledger_decisions=()):
    """Why one candidate landed where it did, from its recorded gates, codes and anchors."""
    total = decision.get("total_score")
    band = next((b for b in scoring["bands"] if total is not None and b["min"] <= total <= b["max"]),
                None)
    gates = dict(decision["gates"])
    sources = []
    for article_id in decision["article_ids"]:
        record = evidence_by_id.get(article_id) or {}
        sources.append({"article_id": article_id, "publisher": record.get("publisher"),
                        "title": record.get("title"), "url": record.get("canonical_url"),
                        "published_date": publication_date(record) if record else None})
    metadata = decision.get("model_metadata") or {}
    return {
        "event_id": decision["event_id"], "revision": decision["revision"],
        "bucket": BUCKETS[decision["recommendation"]], "recommendation": decision["recommendation"],
        "edition_position": edition_position,
        "publication_status": (decision.get("publication") or {}).get("status"),
        "total_score": total, "relevance_level": decision.get("relevance_level"),
        "eligibility_reason": decision.get("eligibility_reason"),
        "score_band": f"{total} is in {band['min']}–{band['max']} ({band['decision']})" if band else None,
        "gates": gates,
        "failed_gates": sorted(name for name, outcome in gates.items() if outcome == "fail"),
        "review_gates": sorted(name for name, outcome in gates.items()
                               if outcome in {"review_required", "not_evaluated"}),
        "reasons": [{"code": code, "explanation": _reason_text(code, decision["recommendation"])}
                    for code in decision["disposition_reason_codes"]],
        "components": [{"name": name, "points": (decision["components"].get(name) or {}).get("points"),
                        "reason": (decision["components"].get(name) or {}).get("reason"),
                        "evidence_refs": (decision["components"].get(name) or {}).get("evidence_refs") or []}
                       for name in COMPONENTS],
        "transmission": decision.get("transmission") or {},
        "sources": sources,
        "article_dates": sorted({s["published_date"] for s in sources if s["published_date"]}),
        "provenance": {"engine": metadata.get("engine"), "model": metadata.get("model"),
                       "prompt_version": metadata.get("prompt_version"),
                       "replayed_stored_response": metadata.get("provider") == "ReplayProvider"},
        "ledger_decisions": list(ledger_decisions),
    }


def export_operator(operator_dir, queue):
    """Write the local operator page. It is never part of a published site directory."""
    operator_dir = Path(operator_dir)
    operator_dir.mkdir(parents=True, exist_ok=True)
    for name in OPERATOR_FILES:
        temporary = operator_dir / f"{name}.partial"
        shutil.copyfile(OPERATOR_SITE / name, temporary)
        os.replace(temporary, operator_dir / name)
    _write_json(operator_dir / "queue.json", queue)


def build_queue(workspace, config, profile, built_at, reuse_stores=(), ledgers=None,
                operator_dir=None):
    """Replay stored responses into grouped, scored, explained candidates. Calls no model."""
    workspace = Path(workspace)
    with _locked(workspace):
        records, bodies = load_evidence(workspace)
        evidence_by_id = {record["article_id"]: record for record in records}
        store = classifier.RawOutputStore(workspace / "raw-outputs")
        digests = {aid: input_digest(record, bodies.get(aid), config, profile)
                   for aid, record in evidence_by_id.items()}
        _import_reused(workspace, store, digests, reuse_stores)
        ready = sorted(aid for aid, digest in digests.items() if store.load(digest, 1) is not None)
        decisions, report, run_id = _run(workspace, store, config, profile, ready, records, bodies,
                                         digests)
        positions = {event_id: position for position in ("selected", "overflow", "urgent_review")
                     for event_id in report.get(position, [])}
        ledger_rows = _ledger_decisions(ledgers or {})
        events = sorted((explain_decision(d, config["scoring"], evidence_by_id,
                                          positions.get(d["event_id"]),
                                          ledger_rows.get(d["event_id"], []))
                         for d in decisions),
                        key=lambda e: (BUCKET_ORDER.index(e["bucket"]), -(e["total_score"] or 0),
                                       e["event_id"]))
        awaiting = [{"article_id": aid, "title": evidence_by_id[aid]["title"],
                     "publisher": evidence_by_id[aid]["publisher"],
                     "url": evidence_by_id[aid]["canonical_url"],
                     "published_date": publication_date(evidence_by_id[aid]),
                     "input_hash": digests[aid], "reason": AWAITING_REASON}
                    for aid in sorted(digests) if aid not in ready]
        reused_log = workspace / "reused-responses.jsonl"
        queue = {
            "schema": "queue-v1", "built_at": built_at, "run_id": run_id,
            "profile": {"provider": profile["provider"], "model_id": profile["model_id"],
                        "prompt_version": profile["prompt_version"],
                        "settings_hash": classifier.settings_hash(profile["inference_settings"])},
            "counts": dict({"articles": len(records), "classified": len(ready),
                            "awaiting_classification": len(awaiting)},
                           **{bucket: sum(e["bucket"] == bucket for e in events)
                              for bucket in BUCKET_ORDER}),
            "events": events, "awaiting": awaiting,
            "reused_responses": read_jsonl(reused_log) if reused_log.exists() else [],
            "limits": QUEUE_LIMITS,
        }
        _write_json(workspace / "queue.json", queue)
    if operator_dir is not None:
        export_operator(operator_dir, queue)
    return queue


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _profile(path, max_attempts):
    if path is None:
        return dict(DEFAULT_PROFILE)
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"provider": manifest["provider"], "model_id": manifest["model_id"],
            "prompt_version": manifest["prompt_version"],
            "inference_settings": manifest["inference_settings"], "max_attempts": max_attempts}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("intake", "classify", "build-queue"):
        command = commands.add_parser(name)
        command.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
        if name != "build-queue":
            command.add_argument("--site", type=Path, default=publication.DEFAULT_SITE,
                                 help="Published site whose status.json records this check")
        if name != "intake":
            command.add_argument("--reuse-store", type=Path, action="append", default=[],
                                 help="Earlier raw-outputs directory; read and copied, never modified")
            command.add_argument("--profile-from", type=Path, default=None,
                                 help="run-manifest.json whose provider/model/prompt/settings to use "
                                      "(default: the calib-smoke-deepseek-flash-v3 profile)")
            command.add_argument("--max-attempts", type=int, default=2)
    commands.choices["intake"].add_argument("batch", type=Path)
    queue_command = commands.choices["build-queue"]
    queue_command.add_argument("--ledger", action="append", default=[], metavar="LABEL=PATH")
    queue_command.add_argument("--operator-dir", type=Path, default=DEFAULT_OPERATOR_DIR)
    paid = commands.choices["classify"]
    paid.add_argument("--provider", required=True, choices=["deepseek"])
    for flag in ("--spend-ledger", "--cap-usd", "--input-per-million", "--output-per-million"):
        paid.add_argument(flag, required=True, help="Explicit, user-approved spending authorization")
    args = parser.parse_args(argv)
    config = baseline.load_config()

    if args.command == "intake":
        try:
            batch, read_error = json.loads(args.batch.read_text(encoding="utf-8")), None
        except (OSError, ValueError) as error:
            batch, read_error = None, str(error)
        report = intake(args.workspace, batch, _now(), site_dir=args.site, read_error=read_error)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "succeeded" else 2

    profile = _profile(args.profile_from, args.max_attempts)
    if args.command == "build-queue":
        ledgers = dict(item.split("=", 1) for item in args.ledger)
        queue = build_queue(args.workspace, config, profile, _now(), args.reuse_store, ledgers,
                            args.operator_dir)
        print(json.dumps({"run_id": queue["run_id"], "counts": queue["counts"],
                          "operator_page": str(args.operator_dir / "index.html")}, indent=2))
        return 0

    from tools.providers.deepseek_provider import DeepSeekProvider
    declared = profile["inference_settings"]
    request = {"max_output_tokens": declared.get("max_output_tokens")}
    # Refuse a settings mismatch before any spend authorization file is created: stored responses
    # are keyed by the declared settings, so a silently different request would mislabel them.
    effective = DeepSeekProvider(profile["model_id"], **request).inference_settings()
    disagreements = sorted(key for key, value in effective.items() if declared.get(key) != value)
    if disagreements:
        parser.error(f"The provider's effective settings differ from the declared profile for "
                     f"{disagreements}; declare a profile matching the request before any paid call")
    checked_at = _now()
    try:
        ledger = SpendLedger(Path(args.spend_ledger), args.cap_usd, args.input_per_million,
                             args.output_per_million)
    except BudgetStop as error:
        publication.record_source_check(args.site, checked_at, "budget_stopped", detail=str(error))
        print(json.dumps({"status": "budget_stopped", "detail": str(error)}))
        return 2
    provider = DeepSeekProvider(profile["model_id"], budget=ledger, **request)
    report = classify_pending(args.workspace, config, profile, provider, checked_at,
                              site_dir=args.site, reuse_stores=args.reuse_store)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
