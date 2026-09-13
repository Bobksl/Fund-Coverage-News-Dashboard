import json
import unittest

from tests.fixtures import article, decision, temporary_directory
from tools import drafting

CLAIMS = [
    {"claim_id": "c1", "statement": "Example Manager closed Example Credit Fund II.",
     "article_id": "a1", "evidence_span": "para 1"},
    {"claim_id": "c2", "statement": "The fund raised $7.3 billion of commitments.",
     "article_id": "a1", "evidence_span": "para 2", "amount": 7.3, "currency": "USD",
     "unit": "billion", "basis": "commitments", "period": "2026"},
]
PARTIES = ["Example Manager"]


def card(**overrides):
    payload = {
        "headline_en": "Example Manager closes $7.3 billion credit fund",
        "summary_en": "Example Manager closed Example Credit Fund II with $7.3 billion of commitments.",
        "interpretation_en": "Deployable capital at Example Manager may increase origination capacity.",
        "headline_zh": "Example Manager 完成73亿美元信贷基金募集",
        "summary_zh": "Example Manager 完成 Example Credit Fund II 募集，获得73亿美元认缴。",
        "interpretation_zh": "Example Manager 的可投资本可能提升其放贷能力。",
        "claim_refs": ["c1", "c2"],
        "canonical_source_url": "https://example.com/news/a1",
    }
    payload.update(overrides)
    return payload


class NumericParityTests(unittest.TestCase):
    def test_english_and_chinese_scales_normalize_to_the_same_value(self):
        self.assertEqual(drafting.numeric_facts("$7.3 billion"),
                         drafting.numeric_facts("73亿"))

    def test_percentages_are_kept_distinct_from_amounts(self):
        self.assertEqual(drafting.numeric_facts("12%"), {("percent", 12.0)})
        self.assertNotEqual(drafting.numeric_facts("12%"), drafting.numeric_facts("12 million"))

    def test_claim_amounts_are_normalized_with_their_unit(self):
        self.assertIn(("amount", 7300000000.0), drafting.claim_facts(CLAIMS))


class CardValidationTests(unittest.TestCase):
    def test_a_grounded_parallel_card_has_no_defects(self):
        self.assertEqual(drafting.validate_card(card(), CLAIMS, PARTIES), [])

    def test_an_unsupported_figure_is_a_defect(self):
        broken = card(summary_en="Example Manager closed the fund with $9.9 billion of commitments.")
        defects = drafting.validate_card(broken, CLAIMS, PARTIES)
        self.assertTrue(any("unsupported figure" in defect for defect in defects))

    def test_a_quantity_mistranslated_in_one_place_is_a_defect(self):
        broken = card(summary_zh="Example Manager 完成 Example Credit Fund II 募集，获得37亿美元认缴。")
        self.assertIn("figure amount 3700000000.0 added in the Chinese card",
                      drafting.validate_card(broken, CLAIMS, PARTIES))

    def test_a_quantity_dropped_from_the_chinese_card_is_a_defect(self):
        broken = card(headline_zh="Example Manager 完成信贷基金募集",
                      summary_zh="Example Manager 完成 Example Credit Fund II 募集。")
        self.assertIn("figure amount 7300000000.0 missing from the Chinese card",
                      drafting.validate_card(broken, CLAIMS, PARTIES))

    def test_a_changed_currency_is_a_defect(self):
        broken = card(summary_zh="Example Manager 完成 Example Credit Fund II 募集，获得73亿欧元认缴。")
        self.assertIn("currency differs across languages",
                      drafting.validate_card(broken, CLAIMS, PARTIES))

    def test_dropped_uncertainty_is_a_defect(self):
        broken = card(interpretation_zh="Example Manager 的可投资本将提升其放贷能力。")
        self.assertIn("uncertainty or negation dropped in the Chinese card",
                      drafting.validate_card(broken, CLAIMS, PARTIES))

    def test_a_dropped_party_is_a_defect(self):
        broken = card(headline_zh="完成73亿美元信贷基金募集",
                      summary_zh="完成 Example Credit Fund II 募集，获得73亿美元认缴。",
                      interpretation_zh="可投资本可能提升放贷能力。")
        self.assertIn("party Example Manager missing from the Chinese card",
                      drafting.validate_card(broken, CLAIMS, PARTIES))

    def test_missing_or_unknown_claim_references_are_defects(self):
        self.assertIn("no claim reference supplied",
                      drafting.validate_card(card(claim_refs=[]), CLAIMS, PARTIES))
        self.assertIn("unknown claim reference c9",
                      drafting.validate_card(card(claim_refs=["c9"]), CLAIMS, PARTIES))

    def test_summary_and_interpretation_must_differ(self):
        text = "Example Manager closed Example Credit Fund II."
        broken = card(summary_en=text, interpretation_en=text)
        self.assertIn("summary and interpretation must stay separate",
                      drafting.validate_card(broken, CLAIMS, PARTIES))

    def test_a_card_implying_a_holding_is_a_defect(self):
        broken = card(interpretation_en="Our position in Example Manager may benefit.")
        self.assertIn("card implies a holding; Phase 2 is monitoring-only",
                      drafting.validate_card(broken, CLAIMS, PARTIES))

    def test_missing_language_fields_stop_further_checks(self):
        self.assertEqual(drafting.validate_card(card(summary_zh=""), CLAIMS, PARTIES),
                         ["missing summary_zh"])


class DrafterTests(unittest.TestCase):
    def test_only_shortlisted_events_are_drafted(self):
        with temporary_directory() as workspace:
            drafter = drafting.Drafter(lambda *unused: json.dumps(card()),
                                       drafting.RawOutputStore(workspace / "raw"), "m1", "d1")
            with self.assertRaises(ValueError):
                drafter.draft(decision(recommendation="suppress"), {"a1": article()}, CLAIMS)

    def test_a_valid_card_is_returned_for_analyst_review_not_published(self):
        with temporary_directory() as workspace:
            drafter = drafting.Drafter(lambda *unused: json.dumps(card()),
                                       drafting.RawOutputStore(workspace / "raw"), "m1", "d1")
            result = drafter.draft(decision(), {"a1": article()}, CLAIMS)
            self.assertEqual(result["status"], "ready_for_analyst_review")
            self.assertEqual(result["defects"], [])
            self.assertIn("Analyst approval", result["publication_note"])

    def test_a_defective_card_is_retried_then_held_for_review(self):
        broken = json.dumps(card(summary_en="The fund raised $9.9 billion."))
        with temporary_directory() as workspace:
            drafter = drafting.Drafter(lambda *unused: broken,
                                       drafting.RawOutputStore(workspace / "raw"), "m1", "d1")
            result = drafter.draft(decision(), {"a1": article()}, CLAIMS)
            self.assertEqual(result["status"], "review_required")
            self.assertIsNone(result["content"])
            self.assertEqual(len(result["attempts"]), 2)

    def test_drafting_prompt_carries_no_evaluator_metadata(self):
        prompt = drafting.build_prompt(decision(), [{"article_id": "a1"}], CLAIMS, "d1")
        self.assertNotIn("event_group_id", json.dumps(prompt))
        self.assertEqual(prompt["event"]["held_status"], "monitored")

    def test_drafting_prompt_names_the_required_flat_output_fields(self):
        # Phase 6 repair: a live deepseek-flash call nested the card under "en"/"zh" objects
        # with its own field names because nothing in the prompt ever named the required flat
        # schema. Pin that the schema block lists every field validate_card actually checks.
        prompt = drafting.build_prompt(decision(), [{"article_id": "a1"}], CLAIMS, "d1")
        required = set(prompt["output_schema"]["required"])
        self.assertTrue(set(drafting.TEXT_FIELDS).issubset(required))
        self.assertIn("claim_refs", required)

    def test_provider_usage_and_latency_are_recorded_without_inventing_a_price(self):
        response = {"raw": json.dumps(card()),
                    "usage": {"input_tokens": 900, "output_tokens": 300}}
        with temporary_directory() as workspace:
            drafter = drafting.Drafter(lambda *unused: response,
                                       drafting.RawOutputStore(workspace / "raw"), "m1", "d1",
                                       timer=iter([0.0, 1.5]).__next__)
            result = drafter.draft(decision(), {"a1": article()}, CLAIMS)
            usage = result["model_metadata"]["usage"]
            self.assertEqual((usage["input_tokens"], usage["output_tokens"]), (900, 300))
            self.assertIsNone(usage["cost_basis"])
            self.assertEqual(result["model_metadata"]["latency_ms_total"], 1500.0)


class QaReportTests(unittest.TestCase):
    def test_report_counts_defect_categories_without_correcting_them(self):
        with temporary_directory() as workspace:
            store = drafting.RawOutputStore(workspace / "raw")
            good = drafting.Drafter(lambda *unused: json.dumps(card()), store, "m1", "d1")
            bad = drafting.Drafter(
                lambda *unused: json.dumps(card(summary_en="It raised $9.9 billion.")),
                store, "m1", "d2")
            cards = [good.draft(decision(), {"a1": article()}, CLAIMS),
                     bad.draft(decision(event_id="p-event-2"), {"a1": article()}, CLAIMS)]
            report = drafting.qa_report(cards)
            self.assertEqual(report["cards"], 2)
            self.assertEqual(report["ready_for_analyst_review"], 1)
            self.assertEqual(report["cards_with_defects"], 1)
            self.assertTrue(report["defect_categories"])


if __name__ == "__main__":
    unittest.main()
