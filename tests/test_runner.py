import csv
import json
import unittest

from tests.fixtures import article, temporary_directory
from tools import baseline, corpus, evaluator, runner
from tools.records import write_jsonl

CONFIG = baseline.load_config()


def evidence(article_id, title, **overrides):
    return article(article_id=article_id, title=title,
                   original_url=f"https://news.example.com/{article_id}?utm_source=mail",
                   canonical_url=overrides.pop("canonical_url", f"https://news.example.com/{article_id}"),
                   evidence_hash=overrides.pop("evidence_hash", f"sha256:{article_id}"),
                   **overrides)


def manifest(article_ids, run_id="run-1", partition="calibration"):
    return {"run_id": run_id, "partition": partition, "article_ids": list(article_ids)}


CORPUS = [
    evidence("a1", "Neuberger Berman closes Private Debt V at $7.3 billion"),
    evidence("a2", "CIFC prices $400 million collateralized loan obligation"),
    evidence("a3", "Local bakery opens a second branch"),
    evidence("a4", "NB reports a strong quarter"),
]


class RunnerTests(unittest.TestCase):
    def test_every_article_leaves_an_outcome(self):
        with temporary_directory() as workspace:
            report = runner.run(manifest([a["article_id"] for a in CORPUS]), CORPUS, CONFIG,
                                runner.BaselineEngine(), workspace / "out")
            self.assertEqual(report["articles_in"], 4)
            self.assertEqual(report["articles_with_outcome"], 4)
            self.assertEqual(report["invalid_decisions"], [])

    def test_predictions_validate_against_the_decision_contract(self):
        with temporary_directory() as workspace:
            runner.run(manifest(["a1", "a2"]), CORPUS, CONFIG, runner.BaselineEngine(),
                       workspace / "out")
            rows = [json.loads(line) for line in
                    (workspace / "out" / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(row["held_status"], "monitored")
                self.assertIsNone(row["analyst_review"])
                self.assertIn(row["publication"]["status"], {"pending_review", "not_selected"})

    def test_repeated_runs_are_byte_identical(self):
        with temporary_directory() as workspace:
            first = runner.run(manifest(["a1", "a2", "a3"]), CORPUS, CONFIG,
                               runner.BaselineEngine(), workspace / "first")
            second = runner.run(manifest(["a1", "a2", "a3"]), list(reversed(CORPUS)), CONFIG,
                                runner.BaselineEngine(), workspace / "second")
            self.assertEqual((workspace / "first" / "predictions.jsonl").read_bytes(),
                             (workspace / "second" / "predictions.jsonl").read_bytes())
            self.assertEqual(first["predicted_events"], second["predicted_events"])

    def test_existing_predictions_are_never_overwritten(self):
        with temporary_directory() as workspace:
            runner.run(manifest(["a1"]), CORPUS, CONFIG, runner.BaselineEngine(), workspace / "out")
            with self.assertRaises(FileExistsError):
                runner.run(manifest(["a1"]), CORPUS, CONFIG, runner.BaselineEngine(),
                           workspace / "out")

    def test_review_export_carries_no_analyst_fields(self):
        with temporary_directory() as workspace:
            runner.run(manifest(["a1", "a4"]), CORPUS, CONFIG, runner.BaselineEngine(),
                       workspace / "out")
            with (workspace / "out" / "review.csv").open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(rows)
            forbidden = {"decision", "event_group_id", "must_not_miss", "rationale", "analyst_id"}
            self.assertFalse(forbidden & set(rows[0]))
            self.assertTrue(any(row["source_urls"] for row in rows))

    def test_unresolved_identity_reaches_the_review_column(self):
        with temporary_directory() as workspace:
            report = runner.run(manifest(["a4"]), CORPUS, CONFIG, runner.BaselineEngine(),
                                workspace / "out")
            report_selected = report["selected"]
            with (workspace / "out" / "review.csv").open(encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["recommendation"], "review_required")
            self.assertIn("identity", row["review_reason"])
            self.assertNotIn(row["event_id"], report_selected)

    def test_manifest_carrying_gold_metadata_is_refused(self):
        with temporary_directory() as workspace:
            poisoned = dict(manifest(["a1"]), gold={"event_group_id": "E1"})
            with self.assertRaises(ValueError):
                runner.run(poisoned, CORPUS, CONFIG, runner.BaselineEngine(), workspace / "out")

    def test_missing_evidence_fails_loudly(self):
        with temporary_directory() as workspace:
            with self.assertRaises(KeyError):
                runner.run(manifest(["a1", "absent"]), CORPUS, CONFIG, runner.BaselineEngine(),
                           workspace / "out")

    def test_duplicate_articles_collapse_into_one_event_with_both_ids(self):
        pair = [evidence("d1", "CIFC prices $400 million collateralized loan obligation",
                         canonical_url="https://news.example.com/shared"),
                evidence("d2", "CIFC prices $400 million collateralized loan obligation",
                         canonical_url="https://news.example.com/shared")]
        with temporary_directory() as workspace:
            report = runner.run(manifest(["d1", "d2"]), pair, CONFIG, runner.BaselineEngine(),
                                workspace / "out")
            self.assertEqual(report["predicted_events"], 1)
            self.assertEqual(report["duplicate_articles"], ["d2"])

    def test_run_without_a_freeze_records_freeze_verified_false(self):
        with temporary_directory() as workspace:
            report = runner.run(manifest(["a1"]), CORPUS, CONFIG, runner.BaselineEngine(),
                                workspace / "out")
            self.assertFalse(report["spec_metadata"]["freeze_verified"])

    def test_run_with_a_matching_freeze_passes_the_preflight(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            freeze = corpus.freeze_record(evidence_path, evidence_path, evidence_path, None,
                                          "2026-09-11T00:00:00+00:00")
            report = runner.run(manifest(["a1"]), CORPUS, CONFIG, runner.BaselineEngine(),
                                workspace / "out", freeze=freeze, evidence_path=evidence_path)
            self.assertTrue(report["spec_metadata"]["freeze_verified"])

    def test_run_refuses_a_freeze_that_no_longer_matches_the_evidence_file(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            freeze = corpus.freeze_record(evidence_path, evidence_path, evidence_path, None,
                                          "2026-09-11T00:00:00+00:00")
            evidence_path.write_bytes(evidence_path.read_bytes() + b"\n")
            with self.assertRaises(evaluator.FreezeError):
                runner.run(manifest(["a1"]), CORPUS, CONFIG, runner.BaselineEngine(),
                          workspace / "out", freeze=freeze, evidence_path=evidence_path)

    def test_run_report_records_config_hashes_for_the_freeze(self):
        with temporary_directory() as workspace:
            report = runner.run(manifest(["a1"]), CORPUS, CONFIG, runner.BaselineEngine(),
                                workspace / "out")
            self.assertIn("scoring.json", report["spec_metadata"]["config_hashes"])
            self.assertEqual(report["partition"], "calibration")


if __name__ == "__main__":
    unittest.main()
