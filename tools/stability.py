"""Repeated-run stability measurement, on calibration records only.

phase-2-experiment.md reruns difficult cases three times to see whether inclusion, entity
resolution and score band move between identical inputs. Materially unstable cases are routed to
review rather than averaged away, and the harness refuses to touch a holdout partition so a
stability pass can never double as extra holdout inference.
"""
from collections import Counter

from tools.records import to_inference_input
from tools.scoring import COMPONENTS, band_for, evaluate

MINIMUM_RUNS = 2


def _band(total, scoring):
    return band_for(total, scoring) if total is not None else None


def _observation(proposal, scoring):
    gates, total, recommendation, _ = evaluate(proposal, scoring)
    return {
        "recommendation": recommendation,
        "band": _band(total, scoring),
        "total_score": total,
        "direct_entity_ids": tuple(sorted(proposal.get("direct_entity_ids") or [])),
        "anchors": tuple((name, (proposal["components"].get(name) or {}).get("points"))
                         for name in COMPONENTS),
    }


def _modal(values):
    return Counter(values).most_common(1)[0]


def measure(engine, evidence_records, config, runs=3, partition="calibration", bodies=None):
    """Run the engine `runs` times over the same inputs and report what moved."""
    if "calibration" not in partition:
        raise ValueError("Stability reruns are permitted on calibration records only")
    if runs < MINIMUM_RUNS:
        raise ValueError(f"At least {MINIMUM_RUNS} runs are needed to observe variation")
    bodies = bodies or {}
    scoring = config["scoring"]
    cases = []
    for record in sorted(evidence_records, key=lambda item: item["article_id"]):
        observations = [_observation(engine.propose(record, config,
                                                    body=bodies.get(record["article_id"])), scoring)
                        for _ in range(runs)]
        inclusion = [observation["recommendation"] for observation in observations]
        bands = [observation["band"] for observation in observations]
        entities = [observation["direct_entity_ids"] for observation in observations]
        modal_inclusion, modal_count = _modal(inclusion)
        unstable_axes = sorted({axis for axis, values in
                                (("inclusion", inclusion), ("band", bands), ("entities", entities))
                                if len(set(values)) > 1})
        cases.append({
            "article_id": record["article_id"],
            "runs": runs,
            "inclusion_values": sorted(set(inclusion)),
            "band_values": sorted({band or "unscored" for band in bands}),
            "entity_values": sorted({" ".join(value) or "none" for value in entities}),
            "modal_inclusion": modal_inclusion,
            "modal_agreement": modal_count / runs,
            "unstable_axes": unstable_axes,
            "stable": not unstable_axes,
            "disposition": "stable" if not unstable_axes else "route_to_review",
        })
    unstable = [case["article_id"] for case in cases if not case["stable"]]
    return {
        "partition": partition, "runs": runs, "cases": cases,
        "articles": len(cases),
        "unstable_article_ids": unstable,
        "stable_share": (len(cases) - len(unstable)) / len(cases) if cases else None,
        "note": ("Materially unstable cases are routed to review, never averaged into a single "
                 "answer. This measures run-to-run variation on identical inputs; it says nothing "
                 "about whether a stable answer is correct."),
    }


def difficult_cases(predictions, limit=20):
    """Pick the cases worth rerunning: unresolved gates first, then scores nearest a band edge.

    Selection reads predictions only. No analyst label, group or cohort informs it.
    """
    scored = []
    for prediction in predictions:
        unresolved = any(outcome == "review_required" for outcome in prediction["gates"].values())
        total = prediction.get("total_score")
        distance = 999 if total is None else min(abs(total - edge) for edge in (60, 70, 80))
        scored.append((0 if unresolved else 1, distance, prediction["event_id"], prediction))
    return [item[3] for item in sorted(scored, key=lambda item: item[:3])[:limit]]


def inference_inputs(evidence_records, bodies=None):
    """The exact allowlisted payloads a stability run sees. Useful for recording what was rerun."""
    bodies = bodies or {}
    return [to_inference_input(record, body=bodies.get(record["article_id"]))
            for record in sorted(evidence_records, key=lambda item: item["article_id"])]
