"""Approval-ledger-gated export (Phase 5 handover section 5F): pending, rejected and
since-edited cards never reach the reviewed feed; only the exact approved revision does."""
import unittest

from tests.fixtures import decision, temporary_directory
from tools import approval_ledger, reviewed_export


def evidence():
    return {"a1": {"article_id": "a1", "title": "Example Manager closes fund",
                   "canonical_url": "https://example.com/a1", "publisher": "Example Wire"}}


def card(status="ready_for_analyst_review", headline="Example Manager closes Private Debt V"):
    return {"event_id": "p-event-1", "status": status,
           "content": {"headline_en": headline, "summary_en": "s", "interpretation_en": "i",
                       "headline_zh": "zh", "summary_zh": "zh", "interpretation_zh": "zh"}}


class BuildReviewedCardsTests(unittest.TestCase):
    def setUp(self):
        self.decisions = {"p-event-1": decision()}
        self.dates = {"p-event-1": "2026-09-01"}

    def test_pending_card_is_not_exported(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            result = reviewed_export.build_reviewed_cards(
                self.decisions, [card()], evidence(), ledger, self.dates)
            self.assertEqual(result, {})

    def test_rejected_card_is_not_exported(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approval_ledger.append_review(ledger, "p-event-1", decision()["revision"],
                                          drafted["content"], "AN01",
                                          "2026-09-12T00:00:00+00:00", "rejected", "not ready")
            result = reviewed_export.build_reviewed_cards(
                self.decisions, [drafted], evidence(), ledger, self.dates)
            self.assertEqual(result, {})

    def test_approved_exact_revision_is_exported(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approval_ledger.append_review(ledger, "p-event-1", decision()["revision"],
                                          drafted["content"], "AN01",
                                          "2026-09-12T00:00:00+00:00", "approved")
            result = reviewed_export.build_reviewed_cards(
                self.decisions, [drafted], evidence(), ledger, self.dates)
            self.assertEqual(set(result), {"p-event-1"})
            self.assertEqual(result["p-event-1"]["status"], "analyst_approved")
            self.assertEqual(result["p-event-1"]["en"]["headline"], drafted["content"]["headline_en"])
            self.assertEqual(result["p-event-1"]["zh"]["headline"], drafted["content"]["headline_zh"])
            self.assertEqual(result["p-event-1"]["date"], "2026-09-01")
            self.assertEqual(result["p-event-1"]["sources"][0]["publisher"], "Example Wire")

    def test_content_changed_after_approval_is_no_longer_exported(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            original = card()
            approval_ledger.append_review(ledger, "p-event-1", decision()["revision"],
                                          original["content"], "AN01",
                                          "2026-09-12T00:00:00+00:00", "approved")
            edited = card(headline="Example Manager closes Private Debt V at $7.3bn")
            result = reviewed_export.build_reviewed_cards(
                self.decisions, [edited], evidence(), ledger, self.dates)
            self.assertEqual(result, {})

    def test_revision_changed_after_approval_is_no_longer_exported(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approval_ledger.append_review(ledger, "p-event-1", decision()["revision"],
                                          drafted["content"], "AN01",
                                          "2026-09-12T00:00:00+00:00", "approved")
            bumped_decisions = {"p-event-1": decision(revision=2)}
            result = reviewed_export.build_reviewed_cards(
                bumped_decisions, [drafted], evidence(), ledger, self.dates)
            self.assertEqual(result, {})

    def test_a_card_that_never_reached_analyst_review_status_cannot_be_approved(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            failed = card(status="review_required")
            # Nothing was ever appended to the ledger for this card; it cannot appear regardless.
            result = reviewed_export.build_reviewed_cards(
                self.decisions, [failed], evidence(), ledger, self.dates)
            self.assertEqual(result, {})


class WriteReviewedFeedTests(unittest.TestCase):
    def test_writes_one_file_per_date_and_an_index_with_only_approved_cards(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approval_ledger.append_review(ledger, "p-event-1", decision()["revision"],
                                          drafted["content"], "AN01",
                                          "2026-09-12T00:00:00+00:00", "approved")
            out_dir = workspace / "reviewed-feed"
            index = reviewed_export.write_reviewed_feed(
                out_dir, {"p-event-1": decision()}, [drafted], evidence(), ledger,
                {"p-event-1": "2026-09-01"})
            self.assertEqual(index["total_approved_cards"], 1)
            self.assertTrue((out_dir / "2026-09-01.json").exists())
            self.assertTrue((out_dir / "index.json").exists())

    def test_writes_nothing_when_nothing_is_approved(self):
        with temporary_directory() as workspace:
            out_dir = workspace / "reviewed-feed"
            index = reviewed_export.write_reviewed_feed(
                out_dir, {"p-event-1": decision()}, [card()], evidence(), workspace / "ledger.csv",
                {"p-event-1": "2026-09-01"})
            self.assertEqual(index["total_approved_cards"], 0)
            self.assertFalse((out_dir / "2026-09-01.json").exists())


if __name__ == "__main__":
    unittest.main()
