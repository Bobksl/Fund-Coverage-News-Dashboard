"""Approval ledger: hash-tied review sign-off, never event-id-only, never label-as-approval."""
import unittest

from tests.fixtures import temporary_directory
from tools import approval_ledger


def content(headline="Neuberger closes Private Debt V", summary="x", interpretation="y"):
    return {"headline_en": headline, "summary_en": summary, "interpretation_en": interpretation,
           "headline_zh": "zh", "summary_zh": "zh", "interpretation_zh": "zh"}


class AppendReviewTests(unittest.TestCase):
    def test_status_must_be_approved_or_rejected(self):
        with temporary_directory() as workspace:
            with self.assertRaises(ValueError):
                approval_ledger.append_review(workspace / "ledger.csv", "e1", 1, content(),
                                              "AN01", "2026-09-12T00:00:00+00:00", "published")

    def test_anonymous_approval_is_refused(self):
        with temporary_directory() as workspace:
            with self.assertRaises(ValueError):
                approval_ledger.append_review(workspace / "ledger.csv", "e1", 1, content(),
                                              "", "2026-09-12T00:00:00+00:00", "approved")

    def test_review_is_appended_not_overwritten(self):
        with temporary_directory() as workspace:
            path = workspace / "ledger.csv"
            approval_ledger.append_review(path, "e1", 1, content(), "AN01",
                                          "2026-09-12T00:00:00+00:00", "rejected", "needs fix")
            approval_ledger.append_review(path, "e1", 1, content(), "AN01",
                                          "2026-09-12T01:00:00+00:00", "approved", "fixed")
            rows = approval_ledger.load_reviews(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["status"], "rejected")
            self.assertEqual(rows[1]["status"], "approved")


class ApprovedHashesTests(unittest.TestCase):
    def test_only_the_latest_decision_for_a_revision_counts(self):
        with temporary_directory() as workspace:
            path = workspace / "ledger.csv"
            approval_ledger.append_review(path, "e1", 1, content(), "AN01",
                                          "2026-09-12T00:00:00+00:00", "approved")
            approval_ledger.append_review(path, "e1", 1, content(), "AN01",
                                          "2026-09-12T01:00:00+00:00", "rejected", "retracted")
            self.assertEqual(approval_ledger.approved_keys(path), set())

    def test_content_change_after_approval_invalidates_it(self):
        with temporary_directory() as workspace:
            path = workspace / "ledger.csv"
            original = content()
            approval_ledger.append_review(path, "e1", 1, original, "AN01",
                                          "2026-09-12T00:00:00+00:00", "approved")
            edited = content(headline="Neuberger closes Private Debt V at $7.3bn")
            cards = [{"event_id": "e1", "revision": 1, "content": edited}]
            self.assertEqual(approval_ledger.filter_approved_cards(cards, path), [])

    def test_matching_current_content_is_exported(self):
        with temporary_directory() as workspace:
            path = workspace / "ledger.csv"
            card_content = content()
            approval_ledger.append_review(path, "e1", 1, card_content, "AN01",
                                          "2026-09-12T00:00:00+00:00", "approved")
            cards = [{"event_id": "e1", "revision": 1, "content": card_content}]
            kept = approval_ledger.filter_approved_cards(cards, path)
            self.assertEqual([c["event_id"] for c in kept], ["e1"])
            self.assertIn("content_hash", kept[0])

    def test_event_id_alone_is_not_enough_a_different_revision_is_not_approved(self):
        with temporary_directory() as workspace:
            path = workspace / "ledger.csv"
            approval_ledger.append_review(path, "e1", 1, content(), "AN01",
                                          "2026-09-12T00:00:00+00:00", "approved")
            cards = [{"event_id": "e1", "revision": 2, "content": content()}]
            self.assertEqual(approval_ledger.filter_approved_cards(cards, path), [])

    def test_empty_ledger_approves_nothing(self):
        with temporary_directory() as workspace:
            cards = [{"event_id": "e1", "revision": 1, "content": content()}]
            self.assertEqual(approval_ledger.filter_approved_cards(cards, workspace / "missing.csv"), [])


if __name__ == "__main__":
    unittest.main()
