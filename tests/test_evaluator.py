import unittest

from tests.fixtures import temporary_directory
from tools import evaluator


def gold(article_id, group, decision="publish", must_not_miss="no"):
    return {"article_id": article_id, "event_group_id": group, "decision": decision,
            "must_not_miss": must_not_miss}


def prediction(event_id, article_ids, recommendation="shortlist"):
    return {"event_id": event_id, "article_ids": list(article_ids),
            "recommendation": recommendation, "direct_entity_ids": ["blue_owl"],
            "propagated_entity_ids": []}


def freeze(**overrides):
    record = {"labels_sha256": "l", "evidence_sha256": "e", "predictions_sha256": "p",
              "split_manifest_sha256": "s", "frozen_at": "2026-09-11T00:00:00+00:00"}
    record.update(overrides)
    return record


class FreezeTests(unittest.TestCase):
    def test_incomplete_freeze_blocks_evaluation(self):
        with self.assertRaises(evaluator.FreezeError):
            evaluator.require_freeze(freeze(labels_sha256=None))

    def test_missing_freeze_record_blocks_evaluation(self):
        with self.assertRaises(evaluator.FreezeError):
            evaluator.require_freeze(None)

    def test_predictions_changed_after_the_freeze_are_refused(self):
        with temporary_directory() as workspace:
            path = workspace / "predictions.jsonl"
            path.write_bytes(b'{"event_id": "e1"}\n')
            digest = evaluator.file_digest(path)
            self.assertTrue(evaluator.require_freeze(freeze(predictions_sha256=digest), path))
            path.write_bytes(b'{"event_id": "e2"}\n')
            with self.assertRaises(evaluator.FreezeError):
                evaluator.require_freeze(freeze(predictions_sha256=digest), path)


class MetricTests(unittest.TestCase):
    def test_duplicate_cards_cannot_create_two_correct_selections(self):
        rows = [gold("a1", "G1"), gold("a2", "G1")]
        predictions = [prediction("p1", ["a1"]), prediction("p2", ["a2"])]
        result = evaluator.evaluate(predictions, rows, "challenge", "holdout",
                                    min_positive_events=1)
        self.assertEqual(result["correct_selections"], 1)
        self.assertEqual(result["selection_precision"], 0.5)
        self.assertEqual(len(result["false_splits"]), 1)

    def test_false_merge_is_credited_with_at_most_one_gold_event(self):
        rows = [gold("a1", "G1"), gold("a2", "G2")]
        result = evaluator.evaluate([prediction("p1", ["a1", "a2"])], rows, "natural_feed",
                                    "holdout", min_positive_events=1)
        self.assertEqual(result["correct_selections"], 1)
        self.assertEqual(result["important_event_recall"], 0.5)
        self.assertEqual(result["false_merges"][0]["gold_groups"], ["G1", "G2"])

    def test_selecting_a_rejected_event_is_a_false_positive(self):
        rows = [gold("a1", "G1"), gold("a2", "G2", decision="reject")]
        result = evaluator.evaluate([prediction("p1", ["a1"]), prediction("p2", ["a2"])], rows,
                                    "natural_feed", "holdout", min_positive_events=1)
        self.assertEqual(result["false_positive_event_ids"], ["p2"])
        self.assertEqual(result["selection_precision"], 0.5)

    def test_abstaining_does_not_earn_recall(self):
        rows = [gold("a1", "G1")]
        result = evaluator.evaluate([prediction("p1", ["a1"], "review_required")], rows,
                                    "natural_feed", "holdout", min_positive_events=1)
        self.assertEqual(result["important_event_recall"], 0.0)
        self.assertEqual(result["review_required_rate"], 1.0)
        self.assertIsNone(result["selection_precision"])

    def test_zero_selected_cards_leaves_precision_undefined(self):
        rows = [gold("a1", "G1")]
        result = evaluator.evaluate([prediction("p1", ["a1"], "suppress")], rows, "natural_feed",
                                    "holdout", min_positive_events=1)
        self.assertIsNone(result["selection_precision"])
        self.assertEqual(result["selected_cards"], 0)

    def test_must_not_miss_counts_urgent_review_as_surfaced(self):
        rows = [gold("a1", "G1", decision="publish", must_not_miss="yes"),
                gold("a2", "G2", decision="publish", must_not_miss="yes")]
        predictions = [prediction("p1", ["a1"], "review_required"),
                       prediction("p2", ["a2"], "suppress")]
        result = evaluator.evaluate(predictions, rows, "challenge", "holdout",
                                    min_positive_events=1)
        self.assertEqual(result["must_not_miss_surfaced"], 1)
        self.assertEqual(result["must_not_miss_unresolved"], ["G2"])

    def test_undersized_cohort_is_inconclusive_not_a_pass(self):
        rows = [gold("a1", "G1")]
        result = evaluator.evaluate([prediction("p1", ["a1"])], rows, "natural_feed", "holdout")
        self.assertFalse(result["evaluable"])
        self.assertEqual(result["disposition"], "inconclusive_insufficient_positive_events")
        self.assertEqual(result["gold_publish_worthy_events"], 1)

    def test_identity_roles_are_left_for_human_adjudication(self):
        rows = [gold("a1", "G1")]
        result = evaluator.evaluate([prediction("p1", ["a1"])], rows, "challenge", "holdout",
                                    min_positive_events=1)
        self.assertEqual(result["identity_role_worksheet"][0]["adjudication"], "pending_human_review")


class ReportTests(unittest.TestCase):
    def test_cohorts_are_never_pooled_and_no_pass_is_asserted(self):
        rows = [gold(f"a{n}", f"G{n}") for n in range(25)]
        natural = evaluator.evaluate([prediction("p1", ["a1"])], rows, "natural_feed", "holdout")
        challenge = evaluator.evaluate([prediction("p2", ["a2"])], rows, "challenge", "holdout")
        combined = evaluator.report([natural, challenge])
        self.assertIsNone(combined["pooled_metrics"])
        self.assertEqual(combined["sample_status"], "all_cohorts_evaluable")
        self.assertEqual(combined["overall_disposition"], "pending_human_disposition")


if __name__ == "__main__":
    unittest.main()
