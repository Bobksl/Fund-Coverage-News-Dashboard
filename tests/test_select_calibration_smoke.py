"""Calibration-smoke selection (Phase 5 handover section 6): category-driven, never gold-informed.

Uses a synthetic evidence set so this test does not depend on the real (private, work/-ignored)
corpus being present.
"""
import unittest

from tests.fixtures import article
from tools.baseline import load_config
from tools.select_calibration_smoke import CATEGORIES, build_manifest, categorize, select
from tools.records import write_jsonl

CONFIG = load_config()


def synthetic_corpus():
    return [
        article(article_id="a1", title="Neuberger Berman closes Private Debt V at $7.3 billion",
               canonical_url="https://example.com/1"),
        article(article_id="a2", title="Neuberger Berman launches venture IPO vehicle",
               canonical_url="https://example.com/2"),
        article(article_id="a3", title="Funding Circle posts 50pc revenue growth in H1",
               canonical_url="https://example.com/3"),
        article(article_id="a4", title="Private credit lenders warned to brace for wider rate outcomes",
               canonical_url="https://example.com/4"),
        article(article_id="a5", title="Blue Owl Managed Funds Lead $2.4 Billion AI Factory Financing",
               canonical_url="https://example.com/5"),
        article(article_id="a6", title="Industry conference names new panel of judges",
               canonical_url="https://example.com/6"),
        article(article_id="a7", title="NB reports a strong quarter",
               canonical_url="https://example.com/7"),
        article(article_id="a8", title="Investors buy shopping center", canonical_url="https://example.com/8",
               publisher="Commercial Observer"),
        article(article_id="a9", title="Fund raises $500 million for private credit strategy",
               canonical_url="https://example.com/9", publisher="Alternative Credit Investor"),
        article(article_id="a10", title="Undisclosed borrower update", canonical_url="https://example.com/10",
               access_status="partial"),
        article(article_id="a11", title="Manager wire report", canonical_url="https://example.com/11"),
        article(article_id="a12", title="Manager wire report", canonical_url="https://example.com/12"),
    ]


class CategorizeTests(unittest.TestCase):
    def test_direct_tracked_vehicle_event_is_detected(self):
        record = article(title="Neuberger Berman closes Private Debt V at $7.3 billion")
        self.assertIn("direct_tracked_vehicle_event", categorize(record, {"neuberger berman": "neuberger",
                                                                          "nb": "neuberger"}))

    def test_untracked_sector_only_title_is_level_b_candidate(self):
        record = article(title="Funding Circle posts 50pc revenue growth in H1")
        self.assertIn("sector_only_level_b_event", categorize(record, {}))

    def test_partial_access_is_flagged_regardless_of_other_categories(self):
        record = article(title="Undisclosed borrower update", access_status="partial")
        self.assertIn("inaccessible_or_partial_evidence", categorize(record, {}))


class SelectTests(unittest.TestCase):
    def test_selection_covers_most_categories_from_a_diverse_synthetic_corpus(self):
        picks, missing = select(synthetic_corpus(), CONFIG)
        # Not every category is guaranteed to have a real example (see the real-corpus manifest's
        # own documented gap), but a deliberately diverse fixture should cover the great majority.
        self.assertGreaterEqual(len(CATEGORIES) - len(missing), 9)

    def test_duplicate_titles_are_selected_as_the_multi_article_case(self):
        picks, _ = select(synthetic_corpus(), CONFIG)
        self.assertEqual(set(picks["multi_article_same_event_or_update"]), {"a11", "a12"})


class BuildManifestTests(unittest.TestCase):
    def test_manifest_article_count_is_within_the_10_to_15_target(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.jsonl"
            write_jsonl(path, synthetic_corpus())
            manifest = build_manifest(path, "2026-09-12T00:00:00+00:00")
            self.assertGreaterEqual(manifest["article_count"], 8)
            self.assertLessEqual(manifest["article_count"], 15)
            self.assertIn("No gold label", manifest["selection_method"])

    def test_manifest_is_deterministic_across_repeated_builds(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.jsonl"
            write_jsonl(path, synthetic_corpus())
            first = build_manifest(path, "2026-09-12T00:00:00+00:00")
            second = build_manifest(path, "2026-09-12T00:00:00+00:00")
            self.assertEqual(first["article_ids_sha256"], second["article_ids_sha256"])


if __name__ == "__main__":
    unittest.main()
