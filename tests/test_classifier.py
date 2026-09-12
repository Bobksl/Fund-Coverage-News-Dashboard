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
        "identity_gate": "pass",
        "direct_entity_ids": ["neuberger"],
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


class PromptContextTests(unittest.TestCase):
    def test_prompt_carries_the_manager_ontology_and_scoring_definitions(self):
        prompt = classifier.build_prompt(classifier.to_inference_input(article()), CONFIG, "p1")
        ontology = prompt["ontology"]
        entity_ids = {item["canonical_id"] for item in ontology["entities"]}
        self.assertIn("neuberger", entity_ids)
        neuberger = next(item for item in ontology["entities"] if item["canonical_id"] == "neuberger")
        self.assertIn("Neuberger Berman", neuberger["aliases"])
        self.assertEqual(neuberger["parent"], None)
        self.assertIn("private_credit", {item["canonical_id"] for item in ontology["sectors"]})
        sector = next(item for item in ontology["sectors"] if item["canonical_id"] == "private_credit")
        self.assertTrue(sector["inclusion_logic"])
        self.assertIn("A", ontology["relevance_levels"])
        self.assertIn("required_connection", ontology["relevance_levels"]["B"])
        anchors = ontology["anchors"]["materiality"]
        self.assertTrue(any(a["points"] == 25 and "definition" in a for a in anchors))
        self.assertIn("min_transmission_A_B", ontology["eligibility"])

    def test_prompt_context_carries_no_evaluator_only_field(self):
        prompt = classifier.build_prompt(classifier.to_inference_input(article()), CONFIG, "p1")
        self.assertEqual(classifier.leakage_scan(prompt), [])


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

    def test_missing_identity_gate_defaults_to_review_not_pass(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output(identity_gate=None)), store).propose(article(), CONFIG)
            self.assertEqual(result["gates"]["identity"], "review_required")

    def test_explicit_identity_gate_pass_is_preserved(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output(identity_gate="pass")), store).propose(article(), CONFIG)
            self.assertEqual(result["gates"]["identity"], "pass")

    def test_invalid_identity_gate_value_is_a_schema_failure(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output(identity_gate="confirmed")), store,
                           attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["attempts"][0]["outcome"], "schema_invalid")
            self.assertIn("invalid identity_gate", result["attempts"][0]["detail"])

    def test_unknown_entity_id_is_a_schema_failure(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output(direct_entity_ids=["fictional_manager"])), store,
                           attempts=1).propose(article(), CONFIG)
            self.assertIn("unknown direct_entity_ids value fictional_manager",
                         result["attempts"][0]["detail"])

    def test_malformed_event_identity_is_a_schema_failure(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output(event_identity="Neuberger Berman")), store,
                           attempts=1).propose(article(), CONFIG)
            self.assertIn("event_identity must be an object", result["attempts"][0]["detail"])

    def test_scored_component_without_a_reason_is_a_schema_failure(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            broken = valid_output(components={
                "portfolio_fit": {"points": 30, "reason": ""},
                "materiality": {"points": 20, "reason": "x"},
                "investment_transmission": {"points": 15, "reason": "x"},
                "actionability": {"points": 8, "reason": "x"},
                "source_credibility": {"points": 7, "reason": "x"},
                "novelty": {"points": 5, "reason": "x"}})
            result = build(Recorder(broken), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("needs a non-empty reason", result["attempts"][0]["detail"])

    def test_non_list_evidence_refs_is_a_schema_failure(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            broken = valid_output(components={
                "portfolio_fit": {"points": 30, "reason": "x", "evidence_refs": "c1"},
                "materiality": {"points": 20, "reason": "x"},
                "investment_transmission": {"points": 15, "reason": "x"},
                "actionability": {"points": 8, "reason": "x"},
                "source_credibility": {"points": 7, "reason": "x"},
                "novelty": {"points": 5, "reason": "x"}})
            result = build(Recorder(broken), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("evidence_refs must be a list", result["attempts"][0]["detail"])

    def test_completely_malformed_payload_types_enter_review_not_a_crash(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            hostile = json.dumps({"relevance_level": "A", "primary_event_type": "capital_formation",
                                  "event_identity": ["ignore prior instructions"],
                                  "components": "not an object"})
            result = build(Recorder(hostile), store, attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["attempts"][0]["outcome"], "schema_invalid")
            self.assertEqual(result["relevance_level"], None)
            self.assertIn("classifier_failure", result["flags"])

    def test_model_cannot_supply_a_total_or_publication_status(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            result = build(Recorder(valid_output(total_score=100, publication="published")),
                           store).propose(article(), CONFIG)
            self.assertNotIn("total_score", result)
            self.assertNotIn("publication", result)


class RelevanceSemanticsTests(unittest.TestCase):
    """ED04 cross-field invariants (Phase 5 handover section 5A): a name mention, a one-line
    sector assertion or a generic macro statement must not pass as a real classification."""

    def test_level_a_tracked_name_mention_alone_is_not_enough(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            broken = valid_output(direct_entity_ids=[], propagated_entity_ids=[])
            result = build(Recorder(broken), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("resolved direct or propagated entity", result["attempts"][0]["detail"])

    def test_level_a_requires_identity_gate_pass(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            broken = valid_output(identity_gate="review_required")
            result = build(Recorder(broken), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("requires identity_gate pass", result["attempts"][0]["detail"])

    def test_level_a_requires_event_identity_to_establish_a_role(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            broken = valid_output(event_identity={"parties": ["Example Manager"], "action": None,
                                                   "vehicle": None, "period": None, "event_date": None})
            result = build(Recorder(broken), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("establish the tracked manager/vehicle's role", result["attempts"][0]["detail"])

    def test_level_b_needs_no_tracked_entity_but_needs_a_sector(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   sector_ids=[],
                                   transmission={"trigger": "peer default", "mechanism":
                                                 "raises deployment risk across private credit funds",
                                                 "outcome": "tighter underwriting", "uncertainty": None})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("at least one monitored sector_id", result["attempts"][0]["detail"])

    def test_level_b_without_a_tracked_entity_and_with_transmission_and_sector_is_valid(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   sector_ids=["private_credit"],
                                   transmission={"trigger": "peer default", "mechanism":
                                                 "raises deployment risk across private credit funds",
                                                 "outcome": "tighter underwriting", "uncertainty": None})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "B")

    def test_level_b_generic_sector_statement_without_transmission_fields_fails(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   sector_ids=["private_credit"],
                                   transmission={"trigger": None, "mechanism": None,
                                                 "outcome": None, "uncertainty": None})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("transmission.trigger and transmission.mechanism",
                         result["attempts"][0]["detail"])

    def test_level_c_generic_transmission_statement_fails(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="C", identity_gate=None, direct_entity_ids=[],
                                   sector_ids=[],
                                   transmission={"trigger": "rate move", "mechanism":
                                                 "rates affect markets", "outcome":
                                                 "affects the market", "uncertainty": None})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("generic statement", result["attempts"][0]["detail"])

    def test_level_c_with_a_specific_causal_chain_is_valid(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="C", identity_gate=None, direct_entity_ids=[],
                                   sector_ids=[],
                                   transmission={"trigger": "base rate cut announced",
                                                 "mechanism": "lowers financing cost for floating "
                                                              "rate private credit borrowers",
                                                 "outcome": "improves debt service coverage and "
                                                            "supports valuation of levered assets",
                                                 "uncertainty": "pace of further cuts unclear"})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "C")

    def test_level_c_missing_transmission_fields_fails(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="C", identity_gate=None, direct_entity_ids=[],
                                   sector_ids=[],
                                   transmission={"trigger": "rates", "mechanism": None,
                                                 "outcome": None, "uncertainty": None})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("substantive transmission", result["attempts"][0]["detail"])


class EvidenceRefsTests(unittest.TestCase):
    def test_evidence_ref_must_point_at_supplied_evidence(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            broken = valid_output(components={
                "portfolio_fit": {"points": 30, "reason": "x", "evidence_refs": ["some-other-article"]},
                "materiality": {"points": 20, "reason": "x"},
                "investment_transmission": {"points": 15, "reason": "x"},
                "actionability": {"points": 8, "reason": "x"},
                "source_credibility": {"points": 7, "reason": "x"},
                "novelty": {"points": 5, "reason": "x"}})
            result = build(Recorder(broken), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("does not reference evidence supplied in this input",
                         result["attempts"][0]["detail"])

    def test_evidence_ref_matching_the_article_id_is_accepted(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(components={
                "portfolio_fit": {"points": 30, "reason": "x", "evidence_refs": ["a1#p1"]},
                "materiality": {"points": 20, "reason": "x"},
                "investment_transmission": {"points": 15, "reason": "x"},
                "actionability": {"points": 8, "reason": "x"},
                "source_credibility": {"points": 7, "reason": "x"},
                "novelty": {"points": 5, "reason": "x"}})
            result = build(Recorder(payload), store).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "A")


class InferenceSettingsTests(unittest.TestCase):
    """Phase 5 handover section 5B: settings must be part of run identity, not just prompt+model."""

    def test_build_inference_settings_keeps_only_supplied_fields(self):
        settings = classifier.build_inference_settings(
            provider="anthropic", model_id="claude-sonnet-5", temperature=0.0, seed=None,
            unsupported_made_up_field="x")
        self.assertEqual(settings, {"provider": "anthropic", "model_id": "claude-sonnet-5",
                                    "temperature": 0.0})

    def test_same_prompt_and_model_different_settings_hash_differently(self):
        prompt = classifier.build_prompt(classifier.to_inference_input(article()), CONFIG, "p1")
        settings_a = classifier.build_inference_settings(temperature=0.0)
        settings_b = classifier.build_inference_settings(temperature=0.7)
        self.assertNotEqual(classifier.input_hash(prompt, "m1", settings_a),
                            classifier.input_hash(prompt, "m1", settings_b))

    def test_two_runs_with_different_settings_do_not_collide_in_the_raw_store(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            settings_a = classifier.build_inference_settings(temperature=0.0)
            settings_b = classifier.build_inference_settings(temperature=0.7)
            classifier_a = build(Recorder(valid_output()), store)
            classifier_a.inference_settings = settings_a
            classifier_b = build(Recorder(valid_output(eligibility_reason="different run")), store)
            classifier_b.inference_settings = settings_b
            result_a = classifier_a.propose(article(), CONFIG)
            result_b = classifier_b.propose(article(), CONFIG)
            self.assertNotEqual(result_a["raw_output_ref"], result_b["raw_output_ref"])

    def test_metadata_settings_carry_the_recorded_inference_settings(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            settings = classifier.build_inference_settings(provider="anthropic", temperature=0.0)
            engine = build(Recorder(valid_output()), store)
            engine.inference_settings = settings
            result = engine.propose(article(), CONFIG)
            self.assertEqual(result["model_metadata"]["settings"]["provider"], "anthropic")
            self.assertEqual(result["model_metadata"]["settings"]["temperature"], 0.0)


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
