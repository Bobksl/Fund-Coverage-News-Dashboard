import unittest

from tests.fixtures import article
from tools import baseline, runner, stability

CONFIG = baseline.load_config()


def record(article_id, title):
    return article(article_id=article_id, title=title,
                   original_url=f"https://news.example.com/{article_id}",
                   canonical_url=f"https://news.example.com/{article_id}",
                   evidence_hash=f"sha256:{article_id}")


CORPUS = [record("a1", "CIFC prices $400 million collateralized loan obligation"),
          record("a2", "NB reports a strong quarter")]


class FlakyEngine:
    """Alternates one anchor between runs, the way an unstable model would."""

    name = "flaky"

    def __init__(self):
        self.calls = 0

    def propose(self, evidence, config, body=None):
        proposal = runner.BaselineEngine().propose(evidence, config, body=body)
        self.calls += 1
        if self.calls % 2 == 0:
            proposal["components"]["materiality"]["points"] = 5
        return proposal


class GuardTests(unittest.TestCase):
    def test_holdout_partitions_are_refused(self):
        with self.assertRaises(ValueError):
            stability.measure(runner.BaselineEngine(), CORPUS, CONFIG, partition="natural_feed_holdout")

    def test_a_single_run_cannot_observe_variation(self):
        with self.assertRaises(ValueError):
            stability.measure(runner.BaselineEngine(), CORPUS, CONFIG, runs=1)


class MeasurementTests(unittest.TestCase):
    def test_a_deterministic_engine_is_reported_fully_stable(self):
        report = stability.measure(runner.BaselineEngine(), CORPUS, CONFIG, runs=3)
        self.assertEqual(report["stable_share"], 1.0)
        self.assertEqual(report["unstable_article_ids"], [])
        self.assertTrue(all(case["modal_agreement"] == 1.0 for case in report["cases"]))

    def test_a_flaky_engine_is_routed_to_review_not_averaged(self):
        report = stability.measure(FlakyEngine(), CORPUS, CONFIG, runs=3)
        unstable = [case for case in report["cases"] if not case["stable"]]
        self.assertTrue(unstable)
        self.assertEqual(unstable[0]["disposition"], "route_to_review")
        self.assertIn("band", unstable[0]["unstable_axes"])
        self.assertLess(unstable[0]["modal_agreement"], 1.0)

    def test_recorded_inputs_are_allowlisted_only(self):
        payloads = stability.inference_inputs(CORPUS)
        self.assertNotIn("evidence_hash", payloads[0])
        self.assertIn("title", payloads[0])


class DifficultCaseTests(unittest.TestCase):
    def test_unresolved_gates_are_picked_before_comfortable_scores(self):
        def prediction(event_id, total, review=False):
            gates = {"identity": "review_required" if review else "pass"}
            return {"event_id": event_id, "total_score": total, "gates": gates}
        picked = stability.difficult_cases([prediction("safe", 95), prediction("edge", 71),
                                            prediction("unresolved", 88, review=True)], limit=2)
        self.assertEqual([item["event_id"] for item in picked], ["unresolved", "edge"])

    def test_selection_reads_predictions_only(self):
        chosen = stability.difficult_cases([{"event_id": "e1", "total_score": None,
                                             "gates": {"identity": "pass"}}])
        self.assertEqual(chosen[0]["event_id"], "e1")


if __name__ == "__main__":
    unittest.main()
