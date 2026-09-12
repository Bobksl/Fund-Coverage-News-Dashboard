"""Demo-feed assembly: per-day capacity and challenge exclusion from the ordinary calendar."""
import importlib
import json
import unittest

from tests.fixtures import article, decision, temporary_directory
from tools.records import write_jsonl


def _decision(event_id, article_id, total, recommendation="shortlist"):
    return decision(event_id=event_id, decision_id=event_id, article_ids=[article_id],
                    total_score=total, recommendation=recommendation)


class BuildDemoFeedTests(unittest.TestCase):
    def _build(self, natural_calibration, natural_holdout, challenge, evidence):
        module = importlib.import_module("tools.build_demo_feed")
        with temporary_directory() as workspace:
            run_dir = workspace / "run"
            for partition, decisions in (("natural_feed_holdout", natural_holdout),
                                         ("natural_feed_calibration", natural_calibration),
                                         ("challenge", challenge)):
                write_jsonl(run_dir / partition / "predictions.jsonl", decisions)
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, evidence)
            original = (module.RUN_DIR, module.EVIDENCE_PATH, module.OUT_DIR)
            module.RUN_DIR, module.EVIDENCE_PATH = run_dir, evidence_path
            module.OUT_DIR = workspace / "demo-feed"
            try:
                index = module.build()
                out_dir = module.OUT_DIR
                # Read every file back while the workspace still exists: temporary_directory()
                # deletes it as soon as this generator-backed context manager is exited, which
                # happens as soon as this function returns, not when the caller is done reading.
                files = {path.name: json.loads(path.read_text(encoding="utf-8"))
                        for path in out_dir.glob("*.json")}
            finally:
                module.RUN_DIR, module.EVIDENCE_PATH, module.OUT_DIR = original
            return index, files

    def test_challenge_candidates_never_appear_in_the_ordinary_calendar(self):
        evidence_articles = [article(article_id="c1", published_at="2026-09-05",
                                     published_date_precision="date")]
        challenge = [_decision("challenge-1", "c1", 90)]
        index, files = self._build([], [], challenge, evidence_articles)
        self.assertNotIn("2026-09-05", index["dates_with_cards"])
        self.assertEqual(files["2026-09-05.json"], [])
        self.assertTrue(index["has_challenge_diagnostic"])
        diagnostic = files["challenge-diagnostic.json"]
        self.assertEqual([c["event_id"] for c in diagnostic], ["challenge-1"])
        self.assertEqual(diagnostic[0]["partition"], "challenge")

    def test_daily_capacity_caps_a_busy_day_without_starving_a_quiet_day(self):
        busy_articles = [article(article_id=f"b{n}", published_at="2026-09-05",
                                 published_date_precision="date") for n in range(14)]
        busy_decisions = [_decision(f"busy{n}", f"b{n}", 90 - n) for n in range(14)]
        quiet_articles = [article(article_id="q1", published_at="2026-09-06",
                                  published_date_precision="date")]
        quiet_decisions = [_decision("quiet1", "q1", 75)]
        index, files = self._build(busy_decisions, quiet_decisions, [],
                                   busy_articles + quiet_articles)
        self.assertEqual(len(files["2026-09-05.json"]), 10)
        self.assertEqual(len(files["2026-09-06.json"]), 1)
        self.assertIn("2026-09-06", index["dates_with_cards"])


if __name__ == "__main__":
    unittest.main()
