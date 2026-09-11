"""End-to-end wiring on synthetic fixtures.

This proves the stages connect and the evaluation boundary holds. It measures nothing about real
editorial quality and is not a benchmark result.
"""
import json
import re
import unittest
from uuid import UUID

from tests.fixtures import article, temporary_directory
from tools import baseline, corpus, evaluator, runner
from tools.records import validate_article, write_jsonl

CONFIG = baseline.load_config()
IDS = [str(UUID(int=number)) for number in range(1, 8)]
# Whole-word matching: "publisher" legitimately contains "publish".
SECRETS = ("publish", "reject", "must_not_miss", "event_group_id", "G1", "rationale",
           "namesake", "bare NB token")

CORPUS = [
    article(article_id=IDS[0], title="Neuberger Berman closes Private Debt V at $7.3 billion",
            original_url="https://news.example.com/1", canonical_url="https://news.example.com/1",
            published_at="2026-08-20", published_date_precision="date", evidence_hash="sha256:1"),
    article(article_id=IDS[1], title="CIFC prices $400 million collateralized loan obligation",
            original_url="https://news.example.com/2", canonical_url="https://news.example.com/2",
            published_at="2026-09-05", published_date_precision="date", evidence_hash="sha256:2"),
    article(article_id=IDS[2], title="CIFC prices $400 million collateralized loan obligation",
            original_url="https://wire.example.com/copy?utm_source=x",
            canonical_url="https://news.example.com/2", publisher="Example Wire",
            published_at="2026-09-05", published_date_precision="date", evidence_hash="sha256:2"),
    article(article_id=IDS[3], title="Borrower misses payment as covenant breach is reported",
            original_url="https://news.example.com/4", canonical_url="https://news.example.com/4",
            published_at="2026-09-06", published_date_precision="date", evidence_hash="sha256:4"),
    article(article_id=IDS[4], title="Local bakery opens a second branch",
            original_url="https://news.example.com/5", canonical_url="https://news.example.com/5",
            published_at="2026-09-07", published_date_precision="date", evidence_hash="sha256:5"),
    article(article_id=IDS[5], title="NB reports a strong quarter",
            original_url="https://news.example.com/6", canonical_url="https://news.example.com/6",
            published_at="2026-09-08", published_date_precision="date", evidence_hash="sha256:6"),
    article(article_id=IDS[6], title="Undated manager note",
            original_url="https://news.example.com/7", canonical_url="https://news.example.com/7",
            published_at=None, published_date_precision="unknown", evidence_hash="sha256:7"),
]
GOLD_GROUPS = {IDS[0]: "G1", IDS[1]: "G2", IDS[2]: "G2", IDS[3]: "G3", IDS[4]: "G4", IDS[5]: "G5"}
GOLD_ROWS = [
    {"article_id": IDS[0], "event_group_id": "G1", "decision": "publish", "must_not_miss": "no"},
    {"article_id": IDS[1], "event_group_id": "G2", "decision": "publish", "must_not_miss": "no"},
    {"article_id": IDS[2], "event_group_id": "G2", "decision": "publish", "must_not_miss": "no"},
    {"article_id": IDS[3], "event_group_id": "G3", "decision": "publish", "must_not_miss": "yes"},
    {"article_id": IDS[4], "event_group_id": "G4", "decision": "reject", "must_not_miss": "no"},
    {"article_id": IDS[5], "event_group_id": "G5", "decision": "review", "must_not_miss": "no"},
]


class EndToEndTests(unittest.TestCase):
    def test_corpus_records_satisfy_the_evidence_contract(self):
        for record in CORPUS:
            self.assertEqual(validate_article(record), [], record["article_id"])

    def test_split_packet_run_and_evaluate(self):
        with temporary_directory() as workspace:
            registry = (corpus.register(CORPUS[:5], "natural_feed", "roster_v1")
                        + corpus.register(CORPUS[5:], "challenge", "probe_v1", "namesake",
                                          "bare NB token"))
            corpus.write_registry(workspace / "registry.jsonl", registry)

            packet = corpus.build_review_packet(CORPUS, workspace / "packet")
            self.assertEqual(packet["articles"], 6)
            self.assertEqual(packet["excluded"][0]["article_id"], IDS[6])

            split = corpus.temporal_split(CORPUS, GOLD_GROUPS, "2026-09-01")
            self.assertEqual(split["calibration"], [IDS[0]])
            self.assertIn(IDS[6], split["unassigned"])
            (workspace / "split.json").write_text(json.dumps(split), encoding="utf-8")

            manifest = corpus.runner_manifest("run-e2e", "natural_feed_holdout", split["holdout"])
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            report = runner.run(manifest, CORPUS, CONFIG, runner.BaselineEngine(),
                                workspace / "out")

            self.assertEqual(report["articles_in"], len(split["holdout"]))
            self.assertEqual(report["duplicate_articles"], [IDS[2]])
            self.assertEqual(report["invalid_decisions"], [])

            predictions_path = workspace / "out" / "predictions.jsonl"
            labels_path = workspace / "labels.csv"
            labels_path.write_text(json.dumps(GOLD_ROWS), encoding="utf-8")
            freeze = corpus.freeze_record(labels_path, evidence_path, workspace / "split.json",
                                          predictions_path, "2026-09-11T00:00:00+00:00")
            self.assertTrue(evaluator.require_freeze(freeze, predictions_path))

            predictions = [json.loads(line) for line in
                           predictions_path.read_text(encoding="utf-8").splitlines()]
            holdout_rows = [row for row in GOLD_ROWS if row["article_id"] in set(split["holdout"])]
            result = evaluator.evaluate(predictions, holdout_rows, "natural_feed", "holdout")
            self.assertFalse(result["evaluable"])
            self.assertEqual(result["disposition"], "inconclusive_insufficient_positive_events")
            self.assertEqual(result["false_splits"], [])
            combined = evaluator.report([result])
            self.assertIsNone(combined["pooled_metrics"])
            self.assertEqual(combined["overall_disposition"], "pending_human_disposition")

    def test_no_pipeline_artifact_contains_evaluator_only_content(self):
        with temporary_directory() as workspace:
            manifest = corpus.runner_manifest("run-leak", "natural_feed_holdout", IDS[:6])
            runner.run(manifest, CORPUS, CONFIG, runner.BaselineEngine(), workspace / "out")
            corpus.build_review_packet(CORPUS[:6], workspace / "packet")
            for path in sorted(workspace.rglob("*")):
                # The blank label sheet is the analyst's input form: its column headers name the
                # judgements to be made, and its rows must stay empty (covered in test_corpus).
                if not path.is_file() or path.name == "analyst-labels.csv":
                    continue
                text = path.read_text(encoding="utf-8-sig", errors="replace").lower()
                for secret in SECRETS:
                    found = re.search(r"(?<!\w)" + re.escape(secret.lower()) + r"(?!\w)", text)
                    self.assertIsNone(found, f"{secret} leaked into {path.name}")

    def test_cli_entrypoint_runs_the_baseline(self):
        with temporary_directory() as workspace:
            manifest_path = workspace / "manifest.json"
            manifest_path.write_text(json.dumps(
                corpus.runner_manifest("run-cli", "calibration", IDS[:2])), encoding="utf-8")
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            exit_code = runner.main([str(manifest_path), str(evidence_path),
                                     str(workspace / "cli-out")])
            self.assertEqual(exit_code, 0)
            self.assertTrue((workspace / "cli-out" / "run-report.json").exists())


class ReplayEngineTests(unittest.TestCase):
    def test_saved_outputs_replay_into_identical_predictions(self):
        from tools import classifier

        payload = json.dumps({
            "relevance_level": "A", "primary_event_type": "capital_formation",
            "subtype": "final_close", "sector_ids": ["private_credit"], "theme_ids": [],
            "direct_entity_ids": ["neuberger"],
            "event_identity": {"parties": ["Neuberger Berman"], "action": "final_close",
                               "vehicle": "Private Debt V", "period": None,
                               "event_date": "2026-08-20"},
            "components": {"portfolio_fit": {"points": 30, "reason": "tracked manager"},
                           "materiality": {"points": 20, "reason": "scale"},
                           "investment_transmission": {"points": 15, "reason": "capacity"},
                           "actionability": {"points": 6, "reason": "monitor"},
                           "source_credibility": {"points": 7, "reason": "release"},
                           "novelty": {"points": 5, "reason": "new"}}})

        with temporary_directory() as workspace:
            store = classifier.RawOutputStore(workspace / "raw")
            live = classifier.StructuredClassifier(
                lambda prompt, digest, attempt: payload, store, "fixture-model", "p1")
            recorded = runner.run(corpus.runner_manifest("run-live", "calibration", [IDS[0]]),
                                  CORPUS, CONFIG, runner.ClassifierEngine(live), workspace / "live")
            replayed = runner.run(corpus.runner_manifest("run-live", "calibration", [IDS[0]]),
                                  CORPUS, CONFIG,
                                  runner.replay_engine(workspace / "raw", "fixture-model", "p1"),
                                  workspace / "replay")
            self.assertEqual(recorded["recommendations"], replayed["recommendations"])
            # Replay reproduces every decision; provenance deliberately differs so a replay can
            # never be reported as a fresh inference run.
            def without_provenance(path):
                rows = [json.loads(line) for line in
                        path.read_text(encoding="utf-8").splitlines()]
                for row in rows:
                    row.pop("model_metadata")
                return rows
            self.assertEqual(without_provenance(workspace / "live" / "predictions.jsonl"),
                             without_provenance(workspace / "replay" / "predictions.jsonl"))
            live_rows = [json.loads(line) for line in
                         (workspace / "live" / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
            replay_rows = [json.loads(line) for line in
                           (workspace / "replay" / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertNotEqual(live_rows[0]["model_metadata"]["provider"],
                                replay_rows[0]["model_metadata"]["provider"])

    def test_replay_without_a_saved_output_does_not_call_a_model(self):
        with temporary_directory() as workspace:
            report = runner.run(corpus.runner_manifest("run-empty", "calibration", [IDS[0]]),
                                CORPUS, CONFIG,
                                runner.replay_engine(workspace / "raw", "fixture-model", "p1"),
                                workspace / "out")
            self.assertEqual(report["recommendations"], {"review_required": 1})


if __name__ == "__main__":
    unittest.main()
