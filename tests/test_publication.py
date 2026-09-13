"""Phase 8 publication: isolated editions, an atomic pointer swap and independent freshness status.

A failed publish must leave the last successful edition served byte-for-byte, and a source check
must never be mistaken for a publication (docs/phase-8-plan.md, first delivery items 1 and 4).
"""
import json
import unittest
from unittest import mock

from tests.fixtures import decision, temporary_directory
from tools import approval_ledger, publication
from tools.records import CREDENTIAL_KEY, leakage_scan


def evidence():
    return {"a1": {"article_id": "a1", "title": "Example Manager closes fund",
                   "canonical_url": "https://example.com/a1", "publisher": "Example Wire"}}


def card(headline="Example Manager closes Private Debt V"):
    return {"event_id": "p-event-1", "status": "ready_for_analyst_review",
            "content": {"headline_en": headline, "summary_en": "s", "interpretation_en": "i",
                        "headline_zh": "zh", "summary_zh": "zh", "interpretation_zh": "zh"}}


def approve(ledger, drafted):
    approval_ledger.append_review(ledger, "p-event-1", 1, drafted["content"], "AN01",
                                  "2026-09-12T00:00:00+00:00", "approved")


def publish(workspace, publication_id, drafted, ledger, kind="historical_sample",
            published_at="2026-09-13T03:00:00+00:00"):
    return publication.publish(
        workspace / "site", publication_id, published_at, kind, {"p-event-1": decision()},
        [drafted], evidence(), ledger, {"p-event-1": "2026-09-01"})


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class PublishTests(unittest.TestCase):
    def test_publish_serves_an_isolated_edition_through_the_pointer(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approve(ledger, drafted)
            pointer = publish(workspace, "ed-001", drafted, ledger)
            site = workspace / "site"
            self.assertEqual(read_json(site / "publication.json"), pointer)
            self.assertEqual(pointer["edition_path"], "editions/ed-001")
            self.assertEqual(pointer["published_at"], "2026-09-13T03:00:00+00:00")
            self.assertEqual(pointer["edition_kind"], "historical_sample")
            self.assertEqual(pointer["update_mode"], "manual")
            self.assertEqual(pointer["article_dates"], ["2026-09-01"])
            self.assertEqual(pointer["edition_sha256"],
                             publication.tree_digest(site / "editions" / "ed-001"))
            day = read_json(site / "editions" / "ed-001" / "2026-09-01.json")
            self.assertEqual(day[0]["en"]["headline"], drafted["content"]["headline_en"])
            self.assertTrue((site / "index.html").exists())
            self.assertTrue((site / "app.js").exists())

    def test_publish_records_a_successful_attempt_separately_from_source_checks(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approve(ledger, drafted)
            publish(workspace, "ed-001", drafted, ledger)
            status = publication.read_status(workspace / "site")
            self.assertEqual(status["last_publish_attempt"]["status"], "succeeded")
            self.assertEqual(status["last_publish_attempt"]["publication_id"], "ed-001")
            self.assertIsNone(status["last_source_check"])
            self.assertEqual(status["update_mode"], "manual")
            self.assertEqual(status["scheduler"], "not_installed")

    def test_unapproved_content_fails_and_keeps_the_last_good_edition(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            approved = card()
            approve(ledger, approved)
            publish(workspace, "ed-001", approved, ledger)
            site = workspace / "site"
            before = (site / "publication.json").read_bytes()
            edited = card(headline="Example Manager closes Private Debt V at $7.3bn")
            with self.assertRaises(publication.PublishError):
                publish(workspace, "ed-002", edited, ledger,
                        published_at="2026-09-14T03:00:00+00:00")
            self.assertEqual((site / "publication.json").read_bytes(), before)
            self.assertFalse((site / "editions" / "ed-002").exists())
            self.assertEqual([p.name for p in (site / "editions").iterdir()], ["ed-001"])
            status = publication.read_status(site)
            self.assertEqual(status["last_publish_attempt"]["status"], "failed")
            self.assertEqual(status["last_publish_attempt"]["publication_id"], "ed-002")
            self.assertIn("no approved card", status["last_publish_attempt"]["detail"])

    def test_a_crash_while_building_keeps_the_last_good_edition(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approve(ledger, drafted)
            publish(workspace, "ed-001", drafted, ledger)
            site = workspace / "site"
            before = (site / "publication.json").read_bytes()
            with mock.patch.object(publication.reviewed_export, "write_reviewed_feed",
                                   side_effect=OSError("disk full")):
                with self.assertRaises(publication.PublishError):
                    publish(workspace, "ed-002", drafted, ledger)
            self.assertEqual((site / "publication.json").read_bytes(), before)
            self.assertEqual([p.name for p in (site / "editions").iterdir()], ["ed-001"])
            self.assertIn("disk full", publication.read_status(site)["last_publish_attempt"]["detail"])

    def test_an_existing_publication_id_is_never_overwritten(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approve(ledger, drafted)
            pointer = publish(workspace, "ed-001", drafted, ledger)
            with self.assertRaises(publication.PublishError):
                publish(workspace, "ed-001", drafted, ledger)
            self.assertEqual(publication.tree_digest(workspace / "site" / "editions" / "ed-001"),
                             pointer["edition_sha256"])

    def test_unknown_edition_kind_is_refused_before_anything_is_written(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approve(ledger, drafted)
            with self.assertRaises(ValueError):
                publish(workspace, "ed-001", drafted, ledger, kind="published_news")
            self.assertFalse((workspace / "site" / "publication.json").exists())

    def test_served_site_carries_no_evaluator_or_credential_keys(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approve(ledger, drafted)
            publish(workspace, "ed-001", drafted, ledger)
            for path in (workspace / "site").rglob("*.json"):
                payload = read_json(path)
                self.assertEqual(leakage_scan(payload), [], path)
                self.assertIsNone(CREDENTIAL_KEY.search(path.read_text(encoding="utf-8")), path)


class LockedFileTests(unittest.TestCase):
    """This workspace is synced by OneDrive; a sync or antivirus handle can briefly hold a file."""

    def test_a_briefly_locked_replace_is_retried(self):
        with temporary_directory() as workspace:
            real_replace = publication.os.replace
            calls = []

            def flaky_replace(source, target):
                calls.append(target)
                if len(calls) == 1:
                    raise PermissionError("[WinError 5] Access is denied")
                return real_replace(source, target)

            with mock.patch.object(publication.os, "replace", side_effect=flaky_replace), \
                    mock.patch.object(publication.time, "sleep"):
                publication.record_source_check(workspace / "site", "2026-09-13T00:00:00+00:00",
                                                "succeeded", new_items=0)
            self.assertEqual(len(calls), 2)
            self.assertEqual(publication.read_status(workspace / "site")["last_source_check"]["status"],
                             "succeeded")

    def test_a_lock_that_never_clears_still_fails_after_bounded_attempts(self):
        with temporary_directory() as workspace:
            with mock.patch.object(publication.os, "replace",
                                   side_effect=PermissionError("[WinError 5] Access is denied")) as replace, \
                    mock.patch.object(publication.time, "sleep"):
                with self.assertRaises(PermissionError):
                    publication.record_source_check(workspace / "site", "2026-09-13T00:00:00+00:00",
                                                    "failed")
            self.assertEqual(replace.call_count, publication.REPLACE_ATTEMPTS)


class SourceCheckStatusTests(unittest.TestCase):
    def test_statuses_are_distinct_and_a_failure_keeps_the_last_successful_check(self):
        with temporary_directory() as workspace:
            site = workspace / "site"
            publication.record_source_check(site, "2026-09-13T00:00:00+00:00", "succeeded",
                                            new_items=0)
            publication.record_source_check(site, "2026-09-13T08:00:00+00:00", "budget_stopped",
                                            detail="cap exhausted")
            status = publication.read_status(site)
            self.assertEqual(status["last_source_check"]["status"], "budget_stopped")
            self.assertEqual(status["last_source_check"]["detail"], "cap exhausted")
            self.assertEqual(status["last_successful_source_check"]["checked_at"],
                             "2026-09-13T00:00:00+00:00")
            self.assertEqual(status["last_successful_source_check"]["new_items"], 0)

    def test_unknown_source_check_status_is_refused(self):
        with temporary_directory() as workspace:
            with self.assertRaises(ValueError):
                publication.record_source_check(workspace / "site", "2026-09-13T00:00:00+00:00",
                                                "ok")

    def test_a_source_check_never_changes_the_published_edition(self):
        with temporary_directory() as workspace:
            ledger = workspace / "ledger.csv"
            drafted = card()
            approve(ledger, drafted)
            publish(workspace, "ed-001", drafted, ledger)
            site = workspace / "site"
            before = (site / "publication.json").read_bytes()
            publication.record_source_check(site, "2026-09-14T00:00:00+00:00", "failed",
                                            detail="index unreachable")
            self.assertEqual((site / "publication.json").read_bytes(), before)
            self.assertEqual(publication.read_status(site)["last_publish_attempt"]["status"],
                             "succeeded")


if __name__ == "__main__":
    unittest.main()
