import json
import unittest

from tests.fixtures import article, temporary_directory
from tools import baseline, classifier

CONFIG = baseline.load_config()


def valid_output(**overrides):
    payload = {
        "relevance_level": "A",
        "primary_event_type": "capital_formation",
        "subtype": "final_close",
        "sector_ids": ["private_credit"],
        "theme_ids": [],
        "event_identity": {"parties": ["Example Manager"], "action": "final_close",
                           "vehicle": "Example Credit Fund II", "period": None,
                           "event_date": "2026-09-01"},
        "components": {"portfolio_fit": {"points": 30, "reason": "tracked manager"},
                       "materiality": {"points": 20, "reason": "scale"},
                       "investment_transmission": {"points": 15, "reason": "capacity"},
                       "actionability": {"points": 8, "reason": "monitor deployment"},
                       "source_credibility": {"points": 7, "reason": "issuer release"},
                       "novelty": {"points": 5, "reason": "new"}},
    }
    payload.update(overrides)
    return json.dumps(payload)


class Recorder:
    """Injected provider stub. Nothing in the repository can reach a network."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, prompt, digest, attempt):
        self.calls.append((digest, attempt))
        response = self.responses[min(attempt - 1, len(self.responses) - 1)]
        if isinstance(response, Exception):
            raise response
        return response


def build(provider, store, attempts=2, clock=None):
    return classifier.StructuredClassifier(provider, store, "fixture-model-1", "p1",
                                           max_attempts=attempts,
                                           clock=clock or (lambda: "2026-09-11T00:00:00+00:00"))


class PromptBoundaryTests(unittest.TestCase):
    def test_prompt_carries_only_allowlisted_evidence(self):
        record = dict(article(), decision="publish", event_group_id="E1")
        prompt = classifier.build_prompt(classifier.to_inference_input(record), CONFIG, "p1")
        self.assertNotIn("event_group_id", json.dumps(prompt))
        self.assertNotIn("decision", json.dumps(prompt["evidence"]))
        self.assertEqual(sorted(prompt["evidence"]),
                         sorted(set(classifier.to_inference_input(record))))
        self.assertIn("untrusted data", json.dumps(prompt["rules"]))

    def test_prompt_refuses_evaluator_metadata_smuggled_into_evidence(self):
        payload = {"article_id": "a1", "title": "x", "gold": {"event_group_id": "E1"}}
        with self.assertRaises(ValueError):
            classifier.build_prompt(payload, CONFIG, "p1")

    def test_identical_input_hashes_identically(self):
        first = classifier.build_prompt({"article_id": "a1"}, CONFIG, "p1")
        second = classifier.build_prompt({"article_id": "a1"}, CONFIG, "p1")
        self.assertEqual(classifier.input_hash(first, "m1"), classifier.input_hash(second, "m1"))
        self.assertNotEqual(classifier.input_hash(first, "m1"), classifier.input_hash(first, "m2"))


class ClassifierTests(unittest.TestCase):
    def test_valid_output_becomes_a_proposal_with_preserved_raw_reference(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output()), store).propose(article(), CONFIG, body="text")
            self.assertEqual(result["relevance_level"], "A")
            self.assertEqual(result["components"]["materiality"]["points"], 20)
            self.assertTrue(result["raw_output_ref"])
            self.assertEqual(result["attempts"][-1]["outcome"], "valid")

    def test_unparsable_output_retries_then_enters_review(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            provider = Recorder("not json", "still not json")
            result = build(provider, store).propose(article(), CONFIG)
            self.assertEqual(len(provider.calls), 2)
            self.assertEqual(result["gates"]["identity"], "review_required")
            self.assertIsNone(result["components"]["materiality"]["points"])
            self.assertIn("classifier_failure", result["flags"])

    def test_retry_can_recover_and_both_attempts_are_recorded(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder("broken", valid_output()), store).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "A")
            self.assertEqual([a["outcome"] for a in result["attempts"]], ["unparsable", "valid"])

    def test_unconfigured_anchor_is_a_schema_failure_not_a_rounded_value(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            broken = valid_output(components={
                "portfolio_fit": {"points": 30, "reason": "x"},
                "materiality": {"points": 17, "reason": "x"},
                "investment_transmission": {"points": 15, "reason": "x"},
                "actionability": {"points": 8, "reason": "x"},
                "source_credibility": {"points": 7, "reason": "x"},
                "novelty": {"points": 5, "reason": "x"}})
            result = build(Recorder(broken), store, attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["attempts"][0]["outcome"], "schema_invalid")
            self.assertIn("unconfigured anchor", result["attempts"][0]["detail"])

    def test_unknown_enum_values_are_rejected(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output(sector_ids=["crypto_lending"])), store,
                           attempts=1).propose(article(), CONFIG)
            self.assertIn("unknown sector_ids value", result["attempts"][0]["detail"])

    def test_transport_failure_is_recorded_separately_from_a_bad_decision(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            provider = Recorder(classifier.ProviderError("timeout"), valid_output())
            result = build(provider, store).propose(article(), CONFIG)
            self.assertEqual(result["attempts"][0]["outcome"], "transport_failure")
            self.assertEqual(result["relevance_level"], "A")

    def test_model_cannot_supply_a_total_or_publication_status(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output(total_score=100, publication="published")),
                           store).propose(article(), CONFIG)
            self.assertNotIn("total_score", result)
            self.assertNotIn("publication", result)


class ReplayTests(unittest.TestCase):
    def test_replay_returns_the_saved_output_without_calling_a_model(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            live = build(Recorder(valid_output()), store).propose(article(), CONFIG, body="text")
            replayed = build(classifier.ReplayProvider(store), store).propose(
                article(), CONFIG, body="text")
            self.assertEqual(replayed["components"], live["components"])
            self.assertEqual(replayed["event_identity"], live["event_identity"])

    def test_replay_of_an_unseen_input_fails_loudly(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(classifier.ReplayProvider(store), store).propose(article(), CONFIG)
            self.assertEqual(result["attempts"][0]["outcome"], "transport_failure")
            self.assertIn("replay will not call a model", result["attempts"][0]["detail"])
            self.assertIn("classifier_failure", result["flags"])

    def test_saved_output_is_append_only(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            store.save("hash1", 1, {"raw": "first"})
            store.save("hash1", 1, {"raw": "second"})
            self.assertEqual(store.load("hash1", 1)["raw"], "first")


if __name__ == "__main__":
    unittest.main()
