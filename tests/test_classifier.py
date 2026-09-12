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
        "entity_matches": [{"entity_id": "neuberger", "economic_role": "manager",
                           "involvement": "direct_involvement", "evidence_refs": ["a1"]}],
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


def _b_transmission(**overrides):
    payload = {"trigger": "a comparable BDC reported rising non-accruals this quarter",
              "mechanism": "signals broader credit-quality deterioration in the same "
                          "middle-market lending segment",
              "outcome": "tighter underwriting standards across comparable direct lenders",
              "uncertainty": None}
    payload.update(overrides)
    return payload


def _readthrough(**overrides):
    payload = {"sector_id": "private_credit",
              "observed_change": "a comparable BDC reported rising non-accruals this quarter",
              "basis": "comparable_exposure",
              "affected_population": "middle-market direct lending BDCs",
              "comparability_explanation": "same borrower segment and lien position as the "
                                          "monitored sector's typical exposure",
              "evidence_refs": ["a1"]}
    payload.update(overrides)
    return payload


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

    def test_prompt_states_the_evidence_refs_format_explicitly(self):
        """The one calibration-smoke-driven repair (docs/phase-5-review-decisions.md): every
        non-crashed response in the pre-repair live smoke run used a label ('title'/'body') or a
        quoted excerpt as evidence_refs, never the required article_id -- an omitted instruction,
        confirmed across 8 of 9 smoke articles. This pins the fix in both places a model reads it."""
        prompt = classifier.build_prompt(classifier.to_inference_input(article()), CONFIG, "p2")
        rules_text = json.dumps(prompt["rules"])
        self.assertIn("article_id", rules_text)
        self.assertIn("'title'", rules_text)
        self.assertIn("'body'", rules_text)
        contract_text = json.dumps(prompt["response_contract"])
        self.assertIn("article_id", contract_text)


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

    def test_level_a_named_only_as_adviser_is_not_level_a(self):
        """Astra review round 1 'must fail', re-verified round 2 with the corrected vocabulary: a
        tracked entity that is only an adviser_arranger with incidental_mention involvement on an
        otherwise unrelated deal is not Level A -- editorial-rulebook.md's own worked example
        ("Guggenheim Securities advising a borrower does not prove Guggenheim Investments lent
        money"), even though the entity's parent_relationship (business_platform_of) is identical
        to a genuinely monitored platform's."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                direct_entity_ids=["guggenheim_securities"], propagated_entity_ids=[],
                entity_matches=[{"entity_id": "guggenheim_securities",
                                 "economic_role": "adviser_arranger",
                                 "involvement": "incidental_mention", "evidence_refs": ["a1"]}],
                event_identity={"parties": ["Acme Corp", "Guggenheim Securities"],
                               "action": "acquisition", "vehicle": None, "period": None,
                               "event_date": "2026-09-01"})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("involvement=direct_involvement", result["attempts"][0]["detail"])

    def test_level_a_propagated_parent_with_a_valid_edge_and_stated_basis_passes(self):
        """Astra review round 2 'must pass', using the corrected direct-vs-propagated shape: the
        directly evidenced business (Deephaven Mortgage) goes in direct_entity_ids with
        involvement=direct_involvement; its tracked parent (Pretium, per config's actual `parent`
        edge) goes in propagated_entity_ids with a stated propagation_basis."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                direct_entity_ids=["deephaven_mortgage"], propagated_entity_ids=["pretium"],
                entity_matches=[{"entity_id": "deephaven_mortgage", "economic_role": "manager",
                                 "involvement": "direct_involvement", "evidence_refs": ["a1"]}],
                propagation_basis="Deephaven Mortgage is Pretium's mortgage servicing platform; "
                                 "a servicing failure there is a firm-wide operational event for "
                                 "Pretium.",
                event_identity={"parties": ["Deephaven Mortgage"], "action": "servicing_failure",
                               "vehicle": "Deephaven Mortgage", "period": None,
                               "event_date": "2026-09-01"})
            result = build(Recorder(payload), store).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "A")

    def test_level_a_propagated_parent_without_a_stated_basis_fails(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                direct_entity_ids=["deephaven_mortgage"], propagated_entity_ids=["pretium"],
                entity_matches=[{"entity_id": "deephaven_mortgage", "economic_role": "manager",
                                 "involvement": "direct_involvement", "evidence_refs": ["a1"]}])
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("propagation_basis", result["attempts"][0]["detail"])

    def test_level_a_propagated_parent_with_no_real_ontology_edge_fails(self):
        """Astra review round 2: propagation must follow an actual config parent edge, not an
        asserted one -- an unrelated/sibling parent with convincing prose must still fail."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                # blue_owl is not deephaven_mortgage's parent (pretium is) -- an invented path.
                direct_entity_ids=["deephaven_mortgage"], propagated_entity_ids=["blue_owl"],
                entity_matches=[{"entity_id": "deephaven_mortgage", "economic_role": "manager",
                                 "involvement": "direct_involvement", "evidence_refs": ["a1"]}],
                propagation_basis="An unrelated company connects somehow to this parent, "
                                 "extending firm-wide consequence.",
                event_identity={"parties": ["Deephaven Mortgage"], "action": "servicing_failure",
                               "vehicle": "Deephaven Mortgage", "period": None,
                               "event_date": "2026-09-01"})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("is not a config ancestor", result["attempts"][0]["detail"])

    def test_level_a_accepts_a_genuine_multi_level_ancestry(self):
        """Astra review round 3 'must pass': otf -> blue_owl_credit -> blue_owl is a real,
        multi-hop config ancestry (config/entities.json). An immediate-parent-only check
        incorrectly rejected blue_owl (the grandparent) even though the full chain is genuine."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                direct_entity_ids=["otf"], propagated_entity_ids=["blue_owl_credit", "blue_owl"],
                entity_matches=[{"entity_id": "otf", "economic_role": "fund",
                                 "involvement": "direct_involvement", "evidence_refs": ["a1"]}],
                propagation_basis="OTF is a Blue Owl Credit vehicle within the Blue Owl platform; "
                                 "a material OTF event carries firm-wide consequence.",
                event_identity={"parties": ["OTF"], "action": "portfolio_quality_change",
                               "vehicle": "OTF", "period": None, "event_date": "2026-09-01"})
            result = build(Recorder(payload), store).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "A")

    def test_level_a_rejects_propagation_rooted_in_an_unevidenced_direct_entity(self):
        """Astra review round 3 'must fail': direct_entity_ids can list more than one entity, but
        propagation must originate from one that is ITSELF evidenced (direct_involvement) -- here
        only neuberger has a direct_involvement match, so pretium (deephaven_mortgage's real
        parent) must not be reachable through the unevidenced deephaven_mortgage entry."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                direct_entity_ids=["neuberger", "deephaven_mortgage"],
                propagated_entity_ids=["pretium"],
                entity_matches=[{"entity_id": "neuberger", "economic_role": "manager",
                                 "involvement": "direct_involvement", "evidence_refs": ["a1"]}],
                propagation_basis="Deephaven Mortgage connects to Pretium via its platform "
                                 "relationship, extending consequence firm-wide.")
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("is not a config ancestor", result["attempts"][0]["detail"])

    def test_level_a_direct_involvement_without_evidence_refs_fails(self):
        """Astra review round 2: a direct_involvement claim needs non-empty evidence_refs, not
        just the assertion."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                entity_matches=[{"entity_id": "neuberger", "economic_role": "manager",
                                 "involvement": "direct_involvement", "evidence_refs": []}])
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("supplies no evidence_refs", result["attempts"][0]["detail"])

    def test_level_a_a_lender_can_be_directly_involved(self):
        """Astra review round 2: economic_role never by itself grants or vetoes Level A -- a
        lender with genuine direct_involvement is legitimate, same as a manager."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                entity_matches=[{"entity_id": "neuberger", "economic_role": "lender",
                                 "involvement": "direct_involvement", "evidence_refs": ["a1"]}])
            result = build(Recorder(payload), store).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "A")

    def test_level_b_needs_no_tracked_entity_but_needs_a_sector(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=[],
                                   transmission=_b_transmission(),
                                   sector_readthrough=_readthrough())
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("at least one monitored sector_id", result["attempts"][0]["detail"])

    def test_level_b_without_a_tracked_entity_and_with_sector_readthrough_is_valid(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=["private_credit"],
                                   transmission=_b_transmission(),
                                   sector_readthrough=_readthrough())
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "B")

    def test_level_b_one_irrelevant_peer_generalized_to_the_sector_fails(self):
        """Astra review Ticket B: presence of a sector_id and prose is not comparability -- the
        structured object with a short, unsupported comparability_explanation must fail too."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=["private_credit"],
                                   transmission=_b_transmission(),
                                   sector_readthrough=_readthrough(comparability_explanation="x"))
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("too short", result["attempts"][0]["detail"])

    def test_level_b_non_string_comparability_explanation_fails(self):
        """Astra review round 2: a non-string value (e.g. 123) must not silently bypass the
        length check -- the prior _text() coercion masked this into an empty, skipped check."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=["private_credit"],
                                   transmission=_b_transmission(),
                                   sector_readthrough=_readthrough(comparability_explanation=123))
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("comparability_explanation must be a string", result["attempts"][0]["detail"])

    def test_level_b_missing_transmission_fails(self):
        """Astra review round 2: B requires the transmission object too, not sector_readthrough
        alone."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=["private_credit"],
                                   transmission={"trigger": None, "mechanism": None,
                                                "outcome": None, "uncertainty": None},
                                   sector_readthrough=_readthrough())
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("requires substantive transmission", result["attempts"][0]["detail"])

    def test_level_b_non_object_transmission_is_a_review_case_not_a_crash(self):
        """Astra review round 2: transmission="not an object" previously raised AttributeError
        from parsed.get("transmission").get(...) (a truthy string survives `or {}`), which would
        have crashed the whole classify call rather than producing a review_required outcome."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=["private_credit"],
                                   transmission="not an object", sector_readthrough=_readthrough())
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["attempts"][0]["outcome"], "schema_invalid")
            self.assertIn("transmission must be an object", result["attempts"][0]["detail"])

    def test_level_c_non_object_transmission_is_a_review_case_not_a_crash(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="C", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=[], transmission=["not", "a dict"])
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["attempts"][0]["outcome"], "schema_invalid")
            self.assertIn("transmission must be an object", result["attempts"][0]["detail"])

    def test_level_b_missing_sector_readthrough_fails(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=["private_credit"],
                                   transmission=_b_transmission())
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("sector_readthrough object", result["attempts"][0]["detail"])

    def test_level_b_readthrough_sector_id_must_be_a_declared_sector(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="B", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=["private_credit"],
                                   transmission=_b_transmission(),
                                   sector_readthrough=_readthrough(sector_id="real_estate_debt"))
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("must be one of the declared sector_ids", result["attempts"][0]["detail"])

    def test_level_c_generic_transmission_statement_fails_without_a_consequence_category(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="C", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=[],
                                   transmission={"trigger": "rate move", "mechanism":
                                                 "rates affect markets", "outcome":
                                                 "affects the market", "uncertainty": None})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("consequence_category", result["attempts"][0]["detail"])

    def test_level_c_padded_generic_statement_with_a_category_word_still_fails(self):
        """Astra review Ticket C: appending a listed keyword to generic prose must not launder it
        past the gate -- consequence_category and affected_exposure are the fields that count."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="C", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=[],
                                   transmission={"trigger": "rate move",
                                                 "mechanism": "rates affect markets and risk",
                                                 "outcome": "affects the market", "uncertainty": None})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertIn("affected_exposure", result["attempts"][0]["detail"])

    def test_level_c_structurally_complete_but_semantically_generic_is_a_known_residual_limit(self):
        """Astra review round 2: this documents, rather than hides, a real gap. A response that
        fills consequence_category and affected_exposure with generic-but-nonempty text (as
        opposed to omitting the fields, tested above) currently passes structural validation --
        Astra reproduced this with affected_exposure="all investment markets". Per the round-2
        adjudication, no further keyword blacklist or length threshold is added to chase this (one
        was already rejected for being simultaneously too strict and too easy to game); the
        remaining gap is closed by the strengthened prompt instruction (PROMPT_RULES) and sampled
        in post-run human/Astra-level review, not by schema validation alone. If this test starts
        failing, the fields are no longer being treated as structural-only and this comment (and
        docs/phase-5-review-decisions.md) need updating to match."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                relevance_level="C", identity_gate=None, direct_entity_ids=[], entity_matches=[],
                sector_ids=[],
                transmission={"trigger": "rate move", "mechanism": "rates affect markets",
                             "outcome": "affects the market", "consequence_category": "risk",
                             "affected_exposure": "all investment markets", "uncertainty": None})
            result = build(Recorder(payload), store).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "C")

    def test_level_c_with_a_specific_causal_chain_and_no_keywords_is_valid(self):
        """Astra review Ticket C 'must pass': a correct explanation using none of the old
        keyword-list words must still pass once it carries the structured fields."""
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(
                relevance_level="C", identity_gate=None, direct_entity_ids=[], entity_matches=[],
                sector_ids=[],
                transmission={"trigger": "central bank lowers the policy rate after its meeting",
                             "mechanism": "borrowers with floating-rate obligations reset to a "
                                          "lower coupon after the scheduled reset date",
                             "outcome": "scheduled interest expense declines and debt-service "
                                        "coverage improves for those borrowers",
                             "consequence_category": "financing",
                             "affected_exposure": "floating-rate private credit borrowers due for "
                                                  "a rate reset this quarter",
                             "uncertainty": "pace of further policy moves is unclear"})
            result = build(Recorder(payload), store, attempts=1).propose(article(), CONFIG)
            self.assertEqual(result["relevance_level"], "C")

    def test_level_c_missing_transmission_fields_fails(self):
        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            payload = valid_output(relevance_level="C", identity_gate=None, direct_entity_ids=[],
                                   entity_matches=[], sector_ids=[],
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
