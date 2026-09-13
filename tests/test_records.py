import unittest

from tests.fixtures import WORK_ROOT, article, decision, temporary_directory
from tools import records


class ArticleContractTests(unittest.TestCase):
    def test_valid_record_passes(self):
        self.assertEqual(records.validate_article(article()), [])

    def test_date_only_evidence_never_acquires_a_midnight_timestamp(self):
        record = article(published_date_precision="date", published_at="2026-09-01T00:00:00+00:00")
        self.assertIn("article: date-only evidence must not carry an invented publication time",
                      records.validate_article(record))

    def test_unavailable_evidence_cannot_claim_examined_text(self):
        record = article(access_status="unavailable", evidence_scope="full_text")
        errors = records.validate_article(record)
        self.assertIn("article: unavailable evidence cannot claim examined text", errors)

    def test_examined_evidence_needs_a_hash_of_the_actual_input(self):
        record = article(evidence_hash=None)
        self.assertIn("article: examined evidence needs evidence_hash of the actual input",
                      records.validate_article(record))

    def test_required_field_may_not_be_null_and_unknown_field_is_rejected(self):
        record = article(publisher=None)
        record["cohort"] = "natural_feed"
        errors = records.validate_article(record)
        self.assertIn("article: publisher must not be null", errors)
        self.assertIn("article: unexpected field cohort", errors)

    def test_numeric_claim_carries_currency_unit_basis_and_period(self):
        record = article(claims=[{"claim_id": "c1", "statement": "Raised money", "article_id": "a1",
                                 "evidence_span": "para 2", "amount": 1200}])
        self.assertEqual(len(records.validate_article(record)), 1)


class InferenceBoundaryTests(unittest.TestCase):
    def test_allowlist_drops_evaluator_fields(self):
        payload = records.to_inference_input(dict(article(), decision="publish", cohort="challenge"))
        self.assertNotIn("decision", payload)
        self.assertNotIn("cohort", payload)
        self.assertIn("title", payload)

    def test_nested_gold_metadata_is_refused_not_silently_passed(self):
        record = dict(article())
        record["title"] = {"text": "Deal closes", "gold": {"event_group_id": "E1"}}
        with self.assertRaises(ValueError):
            records.to_inference_input(record)

    def test_leakage_scan_reports_every_depth(self):
        found = records.leakage_scan({"a": [{"must_not_miss": "yes"}], "rationale": "x"})
        self.assertEqual(sorted(found), ["input.a[0].must_not_miss", "input.rationale"])

    def test_registry_categories_are_evaluator_only_at_every_depth(self):
        self.assertEqual(records.leakage_scan({"nested": [{"categories": ["probe"]}]}),
                         ["input.nested[0].categories"])
        self.assertNotIn("categories", records.to_inference_input(
            dict(article(), categories=["probe"])))
        with self.assertRaises(ValueError):
            records.to_inference_input(dict(article(), title={"categories": ["probe"]}))


class DecisionContractTests(unittest.TestCase):
    def test_valid_decision_passes(self):
        self.assertEqual(records.validate_decision(decision(), {"a1"}), [])

    def test_total_must_be_the_deterministic_sum(self):
        self.assertIn("decision: total_score must be the deterministic sum of the six anchors",
                      records.validate_decision(decision(total_score=99)))

    def test_unscorable_component_forbids_an_imputed_zero_total(self):
        record = decision()
        record["components"]["materiality"] = {"points": None, "reason": "conflicting evidence"}
        record["total_score"] = 0
        self.assertIn("decision: unscorable components require a null total, never an imputed zero",
                      records.validate_decision(record))

    def test_unresolved_gate_must_surface_as_review_required(self):
        record = decision()
        record["gates"]["identity"] = "review_required"
        self.assertIn("decision: an unresolved gate must surface as review_required",
                      records.validate_decision(record))

    def test_model_cannot_approve_publication_and_credentials_are_rejected(self):
        record = decision()
        record["publication"] = {"status": "approved", "selection_reason": "looks good"}
        record["model_metadata"]["api_key"] = "sk-test"
        errors = records.validate_decision(record)
        self.assertIn("decision: only a recorded analyst review can approve or publish", errors)
        self.assertTrue(any("credentials" in error for error in errors))

    def test_phase_2_held_status_is_exactly_monitored(self):
        self.assertIn("decision: Phase 2 held_status must be exactly monitored",
                      records.validate_decision(decision(held_status="confirmed_held")))


class JsonlWriterTests(unittest.TestCase):
    def test_bytes_are_lf_exact_and_overwrite_is_refused(self):
        with temporary_directory() as workspace:
            path = workspace / "evidence.jsonl"
            records.write_jsonl(path, [{"article_id": "a1"}, {"article_id": "a2"}])
            self.assertEqual(path.read_bytes(), b'{"article_id": "a1"}\n{"article_id": "a2"}\n')
            with self.assertRaises(FileExistsError):
                records.write_jsonl(path, [{"article_id": "a3"}])
            self.assertEqual(len(records.read_jsonl(path)), 2)

    def test_interrupted_write_leaves_no_partial_file_in_place(self):
        with temporary_directory() as workspace:
            path = workspace / "nested" / "evidence.jsonl"
            records.write_jsonl(path, [{"article_id": "a1"}])
            self.assertFalse((path.parent / "evidence.jsonl.partial").exists())

    def test_duplicate_json_keys_are_a_contract_violation(self):
        with self.assertRaises(ValueError):
            records.loads('{"article_id": "a1", "article_id": "a2"}')


if __name__ == "__main__":
    unittest.main()
