import unittest

from tests.fixtures import component
from tools import baseline, scoring

SCORING = baseline.load_config()["scoring"]


def proposal(points=None, relevance="A", gates=None, **overrides):
    anchors = {"portfolio_fit": 30, "materiality": 20, "investment_transmission": 15,
               "actionability": 8, "source_credibility": 10, "novelty": 5}
    anchors.update(points or {})
    record = {"components": {name: component(value) for name, value in anchors.items()},
              "relevance_level": relevance,
              "gates": gates if gates is not None else {"identity": "pass", "relevance": "pass"},
              "primary_event_type": "capital_formation", "critical_candidate": False}
    record.update(overrides)
    return record


def decision(event_id, total, region="US", recommendation="shortlist", reasons=("shortlisted",),
             anchors=None):
    values = {"materiality": 15, "investment_transmission": 10, "portfolio_fit": 25}
    values.update(anchors or {})
    return {"event_id": event_id, "total_score": total, "primary_region": region,
            "recommendation": recommendation, "disposition_reason_codes": list(reasons),
            "components": {name: component(value) for name, value in values.items()}}


class GateTests(unittest.TestCase):
    def test_full_pass_produces_a_band_and_summed_total(self):
        gates, total, recommendation, reasons = scoring.evaluate(proposal(), SCORING)
        self.assertEqual(total, 88)
        self.assertEqual(recommendation, "priority_shortlist")
        self.assertEqual(reasons, ["shortlisted"])
        self.assertEqual(set(gates.values()), {"pass"})

    def test_below_materiality_fails_before_the_score_can_rescue_it(self):
        _, total, recommendation, reasons = scoring.evaluate(
            proposal({"materiality": 5}), SCORING)
        self.assertEqual(total, 73)
        self.assertEqual(recommendation, "suppress")
        self.assertIn("below_materiality", reasons)

    def test_level_c_needs_the_higher_transmission_threshold(self):
        _, _, level_c, _ = scoring.evaluate(
            proposal({"investment_transmission": 10}, relevance="C"), SCORING)
        _, _, level_b, _ = scoring.evaluate(
            proposal({"investment_transmission": 10}, relevance="B"), SCORING)
        self.assertEqual(level_c, "suppress")
        self.assertIn(level_b, {"shortlist", "priority_shortlist"})

    def test_unscorable_component_gives_a_null_total_and_review(self):
        record = proposal()
        record["components"]["materiality"] = component(None)
        gates, total, recommendation, _ = scoring.evaluate(record, SCORING)
        self.assertIsNone(total)
        self.assertEqual(recommendation, "review_required")
        self.assertIn("review_required", gates.values())

    def test_anchor_outside_the_configured_scale_is_invalid_not_rounded(self):
        _, total, recommendation, reasons = scoring.evaluate(proposal({"materiality": 17}), SCORING)
        self.assertIsNone(total)
        self.assertEqual(recommendation, "review_required")
        self.assertIn("draft_invalid", reasons)

    def test_unresolved_identity_propagates_to_review(self):
        _, _, recommendation, _ = scoring.evaluate(
            proposal(gates={"identity": "review_required", "relevance": "pass"}), SCORING)
        self.assertEqual(recommendation, "review_required")

    def test_critical_event_is_never_suppressed_by_a_band(self):
        record = proposal({"materiality": 5}, primary_event_type="credit_stress",
                          critical_candidate=True)
        _, _, recommendation, reasons = scoring.evaluate(record, SCORING)
        self.assertEqual(recommendation, "review_required")
        self.assertIn("critical_review", reasons)


class RankingTests(unittest.TestCase):
    def test_critical_events_outrank_higher_scores(self):
        ordered = scoring.rank([decision("e1", 92), decision("e2", 70, reasons=("critical_review",))],
                               SCORING)
        self.assertEqual([d["event_id"] for d in ordered], ["e2", "e1"])

    def test_europe_tie_break_applies_only_within_band_and_five_points(self):
        close_pair = [decision("us", 74), decision("eu", 71, region="Europe")]
        self.assertEqual([d["event_id"] for d in scoring.rank(close_pair, SCORING, ["US"] * 10)],
                         ["eu", "us"])
        far = [decision("us", 79), decision("eu", 71, region="Europe")]
        self.assertEqual([d["event_id"] for d in scoring.rank(far, SCORING, ["US"] * 10)],
                         ["us", "eu"])

    def test_tie_break_is_inactive_once_europe_is_on_target(self):
        pair = [decision("us", 74), decision("eu", 71, region="Europe")]
        on_target = ["Europe"] * 3 + ["US"] * 7
        self.assertEqual([d["event_id"] for d in scoring.rank(pair, SCORING, on_target)],
                         ["us", "eu"])

    def test_ablation_ignores_the_hundred_point_total(self):
        high_total = decision("total", 95, anchors={"materiality": 15, "portfolio_fit": 30})
        high_materiality = decision("stress", 62, anchors={"materiality": 25})
        ordered = scoring.rank_ablation([high_total, high_materiality])
        self.assertEqual([d["event_id"] for d in ordered], ["stress", "total"])


class EditionTests(unittest.TestCase):
    def test_capacity_overflows_instead_of_dropping_and_no_minimum_is_forced(self):
        ranked = [decision(f"e{n}", 90 - n) for n in range(12)]
        edition = scoring.select_edition(ranked, SCORING)
        self.assertEqual(len(edition["selected"]), 10)
        self.assertEqual(len(edition["overflow"]), 2)
        self.assertFalse(edition["below_target"])

    def test_thin_day_is_reported_not_padded(self):
        edition = scoring.select_edition([decision("e1", 80)], SCORING)
        self.assertEqual(len(edition["selected"]), 1)
        self.assertTrue(edition["below_target"])
        self.assertFalse(edition["enforce_min"])

    def test_critical_review_event_is_surfaced_for_urgent_review(self):
        critical = decision("risk", None, recommendation="review_required",
                            reasons=("critical_review",))
        edition = scoring.select_edition([critical], SCORING)
        self.assertEqual([d["event_id"] for d in edition["urgent_review"]], ["risk"])


class DailyEditionTests(unittest.TestCase):
    def test_each_day_gets_its_own_capacity_not_a_partition_wide_cap(self):
        # A busy day (14 eligible events) and a quiet day (2 eligible events); a single
        # partition-wide select_edition would let the busy day's overflow crowd out nothing
        # here since capacity is per day, so the quiet day must still get both of its events.
        busy = [decision(f"busy{n}", 90 - n) for n in range(14)]
        quiet = [decision(f"quiet{n}", 80 - n) for n in range(2)]
        dates = {d["event_id"]: "2026-09-05" for d in busy}
        dates.update({d["event_id"]: "2026-09-06" for d in quiet})
        editions, undated = scoring.select_editions_by_day(busy + quiet, dates, SCORING)
        self.assertEqual(len(editions["2026-09-05"]["selected"]), 10)
        self.assertEqual(len(editions["2026-09-05"]["overflow"]), 4)
        self.assertEqual(len(editions["2026-09-06"]["selected"]), 2)
        self.assertTrue(editions["2026-09-06"]["below_target"])
        self.assertEqual(undated, [])

    def test_undated_decisions_are_returned_separately_not_silently_dropped(self):
        dated = decision("e1", 90)
        undated_decision = decision("e2", 85)
        dates = {"e1": "2026-09-05"}
        editions, undated = scoring.select_editions_by_day([dated, undated_decision], dates, SCORING)
        self.assertEqual(list(editions), ["2026-09-05"])
        self.assertEqual([d["event_id"] for d in undated], ["e2"])

    def test_no_dated_decisions_produces_an_empty_calendar(self):
        editions, undated = scoring.select_editions_by_day([], {}, SCORING)
        self.assertEqual(editions, {})
        self.assertEqual(undated, [])


if __name__ == "__main__":
    unittest.main()
