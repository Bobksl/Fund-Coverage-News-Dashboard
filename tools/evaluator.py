"""Evaluator: joins frozen predictions to gold labels after the fact, one cohort at a time.

This is the only module allowed to read analyst labels, and it refuses to run until the label,
evidence and prediction hashes are recorded. Cohorts are reported separately and never pooled.
Counting is one-to-one on events, so a duplicate card cannot create an extra correct selection
and a false merge cannot be credited with every gold event it swallowed.
"""
import hashlib
from collections import Counter
from pathlib import Path

SELECTED_RECOMMENDATIONS = {"priority_shortlist", "shortlist"}
SURFACED_RECOMMENDATIONS = SELECTED_RECOMMENDATIONS | {"review_required"}
MIN_POSITIVE_EVENTS = 20  # phase-2-experiment.md: per evaluable cohort, not per article count.


class FreezeError(RuntimeError):
    """Raised when evaluation is attempted without a recorded freeze."""


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_freeze(freeze, predictions_path=None):
    """Refuse to evaluate unless labels, evidence and predictions were frozen first."""
    required = ("labels_sha256", "evidence_sha256", "predictions_sha256", "frozen_at",
                "split_manifest_sha256")
    missing = [key for key in required if not (freeze or {}).get(key)]
    if missing:
        raise FreezeError(f"Freeze record incomplete: {missing}")
    if predictions_path is not None:
        actual = file_digest(predictions_path)
        if actual != freeze["predictions_sha256"]:
            raise FreezeError("Predictions changed after the freeze; evaluate the frozen file")
    return True


def gold_events(rows):
    """Collapse analyst rows into gold events. Publication is judged at event level."""
    events = {}
    for row in rows:
        group = row["event_group_id"]
        event = events.setdefault(group, {"event_group_id": group, "article_ids": [],
                                          "decision": row["decision"],
                                          "must_not_miss": row["must_not_miss"] == "yes"})
        event["article_ids"].append(row["article_id"])
        event["must_not_miss"] = event["must_not_miss"] or row["must_not_miss"] == "yes"
    for event in events.values():
        event["article_ids"].sort()
    return events


def _match(predictions, gold):
    """Greedy one-to-one match on shared articles. Deterministic and overlap-ranked."""
    article_to_group = {article: group for group, event in gold.items()
                        for article in event["article_ids"]}
    candidates = []
    for prediction in predictions:
        overlaps = Counter(article_to_group[article] for article in prediction["article_ids"]
                           if article in article_to_group)
        for group, shared in overlaps.items():
            candidates.append((-shared, prediction["event_id"], group))
    matched_predictions, matched_groups, pairs = {}, {}, []
    for negative_shared, event_id, group in sorted(candidates):
        if event_id in matched_predictions or group in matched_groups:
            continue
        matched_predictions[event_id] = group
        matched_groups[group] = event_id
        pairs.append({"event_id": event_id, "event_group_id": group, "shared_articles": -negative_shared})
    return matched_predictions, matched_groups, pairs


def _clustering(predictions, gold):
    article_to_group = {article: group for group, event in gold.items()
                        for article in event["article_ids"]}
    false_merges, group_to_predictions = [], {}
    for prediction in predictions:
        groups = {article_to_group[article] for article in prediction["article_ids"]
                  if article in article_to_group}
        if len(groups) > 1:
            false_merges.append({"event_id": prediction["event_id"], "gold_groups": sorted(groups)})
        for group in groups:
            group_to_predictions.setdefault(group, set()).add(prediction["event_id"])
    false_splits = [{"event_group_id": group, "event_ids": sorted(event_ids)}
                    for group, event_ids in sorted(group_to_predictions.items())
                    if len(event_ids) > 1]
    return false_merges, false_splits


def evaluate(predictions, gold_rows, cohort, split, selected_event_ids=None,
             min_positive_events=MIN_POSITIVE_EVENTS):
    """Return one cohort's result. Never combine two of these into a headline number."""
    gold = gold_events(gold_rows)
    publish_worthy = {group for group, event in gold.items() if event["decision"] == "publish"}
    must_not_miss = {group for group, event in gold.items() if event["must_not_miss"]}
    by_id = {prediction["event_id"]: prediction for prediction in predictions}
    if selected_event_ids is None:
        selected_event_ids = [prediction["event_id"] for prediction in predictions
                              if prediction["recommendation"] in SELECTED_RECOMMENDATIONS]
    selected = [by_id[event_id] for event_id in selected_event_ids if event_id in by_id]
    surfaced = [prediction for prediction in predictions
                if prediction["recommendation"] in SURFACED_RECOMMENDATIONS]

    matched_predictions, matched_groups, pairs = _match(predictions, gold)
    correct = [prediction for prediction in selected
               if matched_predictions.get(prediction["event_id"]) in publish_worthy]
    correct_ids = {prediction["event_id"] for prediction in correct}
    false_positives = [prediction["event_id"] for prediction in selected
                       if prediction["event_id"] not in correct_ids]
    recalled = {matched_predictions[prediction["event_id"]] for prediction in correct}
    surfaced_groups = {matched_predictions.get(prediction["event_id"]) for prediction in surfaced}
    missed_critical = sorted(must_not_miss - surfaced_groups)
    false_merges, false_splits = _clustering(predictions, gold)
    abstentions = [prediction["event_id"] for prediction in predictions
                   if prediction["recommendation"] == "review_required"]

    evaluable = len(publish_worthy) >= min_positive_events
    precision = (len(correct) / len(selected)) if selected else None
    recall = (len(recalled) / len(publish_worthy)) if publish_worthy else None
    return {
        "cohort": cohort, "split": split,
        "evaluable": evaluable,
        "disposition": "measured" if evaluable else "inconclusive_insufficient_positive_events",
        "gold_events": len(gold),
        "gold_publish_worthy_events": len(publish_worthy),
        "minimum_positive_events": min_positive_events,
        "predicted_events": len(predictions),
        "selected_cards": len(selected),
        "selection_precision": precision,
        "correct_selections": len(correct),
        "false_positive_event_ids": sorted(false_positives),
        "important_event_recall": recall,
        "recalled_events": len(recalled),
        "must_not_miss_events": len(must_not_miss),
        "must_not_miss_surfaced": len(must_not_miss) - len(missed_critical),
        "must_not_miss_unresolved": missed_critical,
        "review_required_rate": len(abstentions) / len(predictions) if predictions else None,
        "abstained_event_ids": sorted(abstentions),
        "false_merges": false_merges,
        "false_splits": false_splits,
        "matched_pairs": pairs,
        "identity_role_worksheet": [
            {"event_id": prediction["event_id"],
             "predicted_direct_entity_ids": prediction["direct_entity_ids"],
             "predicted_propagated_entity_ids": prediction["propagated_entity_ids"],
             "adjudication": "pending_human_review"}
            for prediction in selected],
        "limits": ("Precision is undefined with zero selected cards and cannot pass. Identity and "
                   "role correctness needs human adjudication of free-text analyst roles; no rate "
                   "is computed here. Report this cohort on its own."),
    }


def report(results):
    """Collect cohort results without pooling them into a single readiness number."""
    return {
        "cohorts": list(results),
        "pooled_metrics": None,
        "pooling_note": "Natural-feed and challenge results are never combined into one figure.",
        "sample_status": "all_cohorts_evaluable" if results and all(
            result["evaluable"] for result in results) else "insufficient_sample",
        "overall_disposition": "pending_human_disposition",
        "disposition_basis": "Sample sufficiency is not a pass. A pass, fail or inconclusive "
                             "verdict is issued by a person against the acceptance table, per "
                             "cohort, after reading the counts and unresolved cases above.",
    }
