import unittest

from tests.fixtures import temporary_directory
from tools import challenge


def row(article_id="a1", category="hard_negative", **overrides):
    values = {"article_id": article_id, "categories": [category],
              "selection_reason": "routine mega-manager activity"}
    values.update(overrides)
    return values


class ValidationTests(unittest.TestCase):
    def test_a_valid_row_passes(self):
        self.assertEqual(challenge.validate_rows([row()]), [])

    def test_an_unknown_category_is_refused(self):
        self.assertTrue(challenge.validate_rows([row(category="interesting")]))

    def test_one_record_may_serve_two_overlapping_probes(self):
        both = row(categories=["manager_independent_bc", "multi_article_group"])
        self.assertEqual(challenge.validate_rows([both]), [])
        report = challenge.coverage([both])
        self.assertEqual(report["by_category"]["multi_article_group"]["have"], 1)
        self.assertEqual(report["by_category"]["manager_independent_bc"]["have"], 1)
        self.assertEqual(report["records"], 1)
        self.assertEqual(report["category_assignments"], 2)

    def test_a_selection_reason_is_required(self):
        self.assertTrue(challenge.validate_rows([row(selection_reason="")]))

    def test_duplicate_articles_are_refused(self):
        self.assertTrue(challenge.validate_rows([row(), row()]))

    def test_an_analyst_label_may_not_ride_along(self):
        errors = challenge.validate_rows([row(decision="publish")])
        self.assertTrue(any("analyst field decision" in error for error in errors))

    def test_a_natural_feed_article_must_be_linked_not_recounted(self):
        errors = challenge.validate_rows([row("nf1")], natural_feed_ids={"nf1"})
        self.assertTrue(any("linked rather than recounted" in error for error in errors))
        linked = row("nf1", linked_natural_feed_article_id="nf1")
        self.assertEqual(challenge.validate_rows([linked], natural_feed_ids={"nf1"}), [])


class CoverageTests(unittest.TestCase):
    def test_short_coverage_is_reported_short(self):
        report = challenge.coverage([row()])
        self.assertEqual(report["by_category"]["hard_negative"]["have"], 1)
        self.assertEqual(report["by_category"]["hard_negative"]["short_by"], 24)
        self.assertFalse(report["complete"])
        self.assertIn("hard_negative", report["categories_short"])

    def test_a_met_minimum_is_not_a_pass_claim(self):
        rows = [row(f"a{n}", "similar_headline_pair", selection_reason="deceptive pair")
                for n in range(2)]
        report = challenge.coverage(rows)
        self.assertTrue(report["by_category"]["similar_headline_pair"]["met"])
        self.assertIn("never that the pipeline passed it", report["note"])

    def test_zero_minimum_category_counts_as_met(self):
        self.assertTrue(challenge.coverage([])["by_category"]["operational"]["met"])


class PacketTests(unittest.TestCase):
    def test_packet_rows_expose_only_the_article_id(self):
        rows = challenge.packet_rows([row(selection_reason="namesake probe")])
        self.assertEqual(rows, [{"article_id": "a1"}])

    def test_registry_refuses_to_overwrite(self):
        with temporary_directory() as workspace:
            path = workspace / "challenge.jsonl"
            challenge.write_registry(path, [row()])
            with self.assertRaises(FileExistsError):
                challenge.write_registry(path, [row()])

    def test_registry_refuses_invalid_rows(self):
        with temporary_directory() as workspace:
            with self.assertRaises(ValueError):
                challenge.write_registry(workspace / "c.jsonl", [row(category="nope")])


if __name__ == "__main__":
    unittest.main()
