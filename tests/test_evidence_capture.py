import unittest

from tests.fixtures import article, temporary_directory
from tools import evidence_capture as capture

BODY = "A tracked manager closed a credit fund. " * 20


def record(article_id="a1", **overrides):
    values = {"article_id": article_id, "evidence_hash": None, "evidence_local_ref": None,
              "evidence_scope": "metadata_only", "access_status": "accessible"}
    values.update(overrides)
    return article(**values)


class ClassifyTests(unittest.TestCase):
    def test_a_full_page_is_accessible_full_text(self):
        self.assertEqual(capture.classify(BODY), ("accessible", "full_text"))

    def test_a_bare_teaser_behind_a_gate_keeps_no_text(self):
        teaser = "Results out. Subscribe to continue reading."
        self.assertEqual(capture.classify(teaser), ("partial", "metadata_only"))

    def test_a_substantive_gated_lede_is_kept_as_an_excerpt(self):
        lede = ("The lender reported record revenue of 138.2m and its chief executive announced "
                "plans to step down, according to half-year results published on Tuesday. "
                "Credit extended rose 52 per cent over the period. ") + "Already have an account?"
        self.assertEqual(capture.classify(lede), ("partial", "primary_excerpt"))

    def test_an_explicit_gated_flag_never_yields_full_text(self):
        self.assertEqual(capture.classify(BODY, gated=True), ("partial", "primary_excerpt"))

    def test_a_short_page_without_a_gate_is_a_partial_excerpt(self):
        short = ("The manager provided a loan against a portfolio of assets, according to a "
                 "statement issued on Tuesday, though the terms of the facility were not "
                 "disclosed in the announcement.")
        self.assertEqual(capture.classify(short), ("partial", "primary_excerpt"))

    def test_a_snippet_too_short_to_add_anything_is_metadata_only(self):
        self.assertEqual(capture.classify("A short note about a loan."),
                         ("partial", "metadata_only"))

    def test_a_bounded_capture_is_an_excerpt_not_full_text(self):
        self.assertEqual(capture.classify(BODY, mode="excerpt"), ("accessible", "primary_excerpt"))
        self.assertEqual(capture.classify(BODY, mode="full"), ("accessible", "full_text"))

    def test_an_empty_or_reported_failure_is_unavailable(self):
        self.assertEqual(capture.classify(""), ("unavailable", "metadata_only"))
        self.assertEqual(capture.classify(BODY, "unavailable"), ("unavailable", "metadata_only"))

    def test_the_hash_tracks_words_not_line_wrapping(self):
        self.assertEqual(capture.digest("one two\n\n\n\nthree"), capture.digest("one two\n\nthree"))
        self.assertNotEqual(capture.digest("one two"), capture.digest("one three"))


class ApplyTests(unittest.TestCase):
    def test_a_captured_article_gets_a_hash_and_a_local_reference(self):
        with temporary_directory() as workspace:
            updated, report = capture.apply_captures(
                [record()], [{"article_id": "a1", "text": BODY}], workspace / "store")
            self.assertEqual(updated[0]["evidence_scope"], "full_text")
            self.assertTrue(updated[0]["evidence_hash"].startswith("sha256:"))
            self.assertEqual(updated[0]["evidence_local_ref"],
                             "work/phase2/evidence-store/a1.txt")
            self.assertEqual(report["captures_applied"], 1)
            self.assertTrue((workspace / "store" / "a1.txt").exists())

    def test_a_gated_article_keeps_no_text_and_no_hash(self):
        with temporary_directory() as workspace:
            updated, report = capture.apply_captures(
                [record()], [{"article_id": "a1", "text": "Teaser. Subscribe to continue reading."}],
                workspace / "store")
            self.assertEqual(updated[0]["evidence_scope"], "metadata_only")
            self.assertIsNone(updated[0]["evidence_hash"])
            self.assertFalse((workspace / "store" / "a1.txt").exists())
            self.assertEqual(report["uncaptured"], ["a1"])

    def test_changed_source_text_is_recorded_as_a_correction(self):
        with temporary_directory() as workspace:
            first = record(evidence_hash=capture.digest("old text of the article " * 30),
                           evidence_scope="full_text",
                           evidence_local_ref="work/phase2/evidence-store/a1.txt")
            updated, report = capture.apply_captures(
                [first], [{"article_id": "a1", "text": BODY, "captured_at": "2026-09-12"}],
                workspace / "store")
            self.assertEqual(len(report["corrections"]), 1)
            self.assertEqual(report["corrections"][0]["previous_evidence_hash"],
                             first["evidence_hash"])
            self.assertEqual(updated[0]["evidence_hash"], capture.digest(BODY))

    def test_an_identical_recapture_records_no_correction(self):
        with temporary_directory() as workspace:
            first = record(evidence_hash=capture.digest(BODY), evidence_scope="full_text",
                           evidence_local_ref="work/phase2/evidence-store/a1.txt")
            _, report = capture.apply_captures(
                [first], [{"article_id": "a1", "text": BODY}], workspace / "store")
            self.assertEqual(report["corrections"], [])

    def test_a_capture_for_another_cohort_is_skipped_not_applied(self):
        with temporary_directory() as workspace:
            _, report = capture.apply_captures(
                [record()], [{"article_id": "elsewhere", "text": BODY}], workspace / "store")
            self.assertEqual(report["skipped"][0]["article_id"], "elsewhere")
            self.assertEqual(report["captures_applied"], 0)

    def test_updated_records_still_satisfy_the_evidence_contract(self):
        with temporary_directory() as workspace:
            updated, report = capture.apply_captures(
                [record(), record("a2")],
                [{"article_id": "a1", "text": BODY}, {"article_id": "a2", "text": ""}],
                workspace / "store")
            self.assertEqual(report["invalid"], [])
            self.assertEqual(report["by_evidence_scope"],
                             {"full_text": 1, "metadata_only": 1})


if __name__ == "__main__":
    unittest.main()


class BoilerplateTests(unittest.TestCase):
    def test_text_repeated_across_articles_is_rejected_as_chrome(self):
        chrome = "Home Funds Capabilities About us Contact us " * 20
        captures = [{"article_id": f"a{n}", "text": chrome} for n in range(4)]
        flagged = capture.flag_boilerplate(captures)
        self.assertEqual(flagged, 4)
        self.assertTrue(all(c["text"] == "" for c in captures))
        self.assertIn("boilerplate", captures[0]["capture_failure"])

    def test_distinct_article_text_survives(self):
        captures = [{"article_id": "a1", "text": BODY},
                    {"article_id": "a2", "text": "A different article entirely. " * 20}]
        self.assertEqual(capture.flag_boilerplate(captures), 0)
        self.assertTrue(captures[0]["text"])

    def test_a_flagged_capture_becomes_uncaptured_not_stored(self):
        with temporary_directory() as workspace:
            chrome = "Menu Home About " * 30
            captures = [{"article_id": f"a{n}", "text": chrome} for n in range(3)]
            capture.flag_boilerplate(captures)
            records = [record(f"a{n}") for n in range(3)]
            updated, report = capture.apply_captures(records, captures, workspace / "store")
            self.assertEqual(len(report["uncaptured"]), 3)
            self.assertTrue(all(r["evidence_scope"] == "metadata_only" for r in updated))
            self.assertEqual(list((workspace / "store").glob("*.txt")), [])
