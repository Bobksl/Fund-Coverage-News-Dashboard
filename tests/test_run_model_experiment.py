"""tools/run_model_experiment.py: the reproducible live-shaped entry point (Phase 5 handover 5C).

These tests never touch a network or the anthropic package. Replay mode is exercised the same way
runner.py's own replay engine is tested; freeze preflight is exercised by tampering with the
evidence file after freezing it.
"""
import json
import unittest
from uuid import UUID

from tests.fixtures import article, temporary_directory
from tools import corpus, run_model_experiment as rme
from tools.evaluator import FreezeError
from tools.records import write_jsonl
from tools.inference_budget import SpendLedger

IDS = [str(UUID(int=n)) for n in range(20, 23)]
CORPUS = [
    article(article_id=IDS[0], title="Example Manager closes a fund",
           original_url="https://news.example.com/20", canonical_url="https://news.example.com/20",
           published_at="2026-08-20", published_date_precision="date", evidence_hash="sha256:20"),
]


class BuildProviderTests(unittest.TestCase):
    def test_unauthorized_provider_name_is_refused(self):
        with self.assertRaises(ValueError):
            rme.build_provider("made_up_provider", "model-x")

    def test_anthropic_provider_can_be_built_without_a_credential(self):
        # Construction alone must not require a credential or a network call -- only a real
        # __call__ does (see tests/test_anthropic_provider.py).
        provider = rme.build_provider("anthropic", "claude-sonnet-5")
        self.assertEqual(provider.model_id, "claude-sonnet-5")


class ProviderKwargsTests(unittest.TestCase):
    """A live calibration run against deepseek-flash (a reasoning model whose reasoning_content
    counts against max_tokens) truncated every response because run_experiment built the provider
    with build_provider(provider_name, model_id) only -- provider_kwargs like max_output_tokens
    were computed but never actually passed to the provider constructor."""

    def test_provider_kwargs_reach_the_constructed_provider(self):
        captured = {}

        class FakeProvider:
            def __init__(self, model_id, **kwargs):
                captured["model_id"] = model_id
                captured["kwargs"] = kwargs

            def __call__(self, prompt, digest, attempt):
                from tools.classifier import ProviderError
                # Raising ProviderError (a transport_failure) lets propose() finish gracefully
                # via the review-proposal path instead of crashing the test; the constructor
                # kwargs are already captured above by this point.
                raise ProviderError("not a real call -- only checking constructor kwargs")

        import tools.run_model_experiment as rme
        original = rme.build_provider
        rme.build_provider = lambda name, model_id, **kwargs: FakeProvider(model_id, **kwargs)
        try:
            with temporary_directory() as workspace:
                evidence_path = workspace / "evidence.jsonl"
                write_jsonl(evidence_path, CORPUS)
                ledger = SpendLedger(workspace / 'synthetic-spend.jsonl', cap_usd='25')
                rme.run_experiment(
                    "run-kwargs", "calibration", [IDS[0]], evidence_path, None, workspace / "out",
                    raw_store_dir=workspace / "raw", provider_name="deepseek",
                    model_id="deepseek-flash", provider_kwargs={"max_output_tokens": 8192},
                    replay=False, spend_ledger=ledger)
        finally:
            rme.build_provider = original
        self.assertEqual(captured["kwargs"], {"max_output_tokens": 8192, "budget": ledger})


class ReplayModeTests(unittest.TestCase):
    def test_replay_with_no_saved_output_never_calls_a_model_and_enters_review(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            report, manifest = rme.run_experiment(
                "run-replay-1", "calibration", [IDS[0]], evidence_path, None,
                workspace / "out", raw_store_dir=workspace / "raw",
                provider_name="anthropic", model_id="claude-sonnet-5-fixture", replay=True)
            self.assertEqual(report["recommendations"], {"review_required": 1})
            self.assertEqual(manifest["mode"], "replay")
            self.assertEqual(manifest["provider_transport_failures"], 0)

    def test_run_manifest_records_settings_hash_and_usage_totals(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            report, manifest = rme.run_experiment(
                "run-replay-2", "calibration", [IDS[0]], evidence_path, None,
                workspace / "out", raw_store_dir=workspace / "raw",
                provider_name="anthropic", model_id="claude-sonnet-5-fixture",
                inference_settings={"temperature": 0.0}, replay=True)
            self.assertIn("inference_settings_hash", manifest)
            self.assertEqual(manifest["inference_settings"]["temperature"], 0.0)
            self.assertIn("input_tokens", manifest["usage_totals"])
            self.assertEqual((workspace / "out" / "run-manifest.json").exists(), True)

    def test_two_runs_with_different_settings_produce_different_settings_hashes(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            _, manifest_a = rme.run_experiment(
                "run-a", "calibration", [IDS[0]], evidence_path, None, workspace / "a",
                raw_store_dir=workspace / "raw-a", provider_name="anthropic",
                model_id="claude-sonnet-5-fixture", inference_settings={"temperature": 0.0},
                replay=True)
            _, manifest_b = rme.run_experiment(
                "run-b", "calibration", [IDS[0]], evidence_path, None, workspace / "b",
                raw_store_dir=workspace / "raw-b", provider_name="anthropic",
                model_id="claude-sonnet-5-fixture", inference_settings={"temperature": 0.9},
                replay=True)
            self.assertNotEqual(manifest_a["inference_settings_hash"],
                                manifest_b["inference_settings_hash"])

    def test_no_credential_value_appears_anywhere_in_the_run_manifest(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            _, manifest = rme.run_experiment(
                "run-replay-3", "calibration", [IDS[0]], evidence_path, None,
                workspace / "out", raw_store_dir=workspace / "raw",
                provider_name="anthropic", model_id="claude-sonnet-5-fixture", replay=True)
            serialized = json.dumps(manifest)
            self.assertNotIn("sk-ant", serialized)
            self.assertNotIn("ANTHROPIC_API_KEY", serialized)


class FreezePreflightTests(unittest.TestCase):
    def test_a_tampered_evidence_file_fails_the_preflight_before_any_classification(self):
        with temporary_directory() as workspace:
            evidence_path = workspace / "evidence.jsonl"
            write_jsonl(evidence_path, CORPUS)
            labels_path = workspace / "labels.csv"
            labels_path.write_text("article_id\n", encoding="utf-8")
            split_path = workspace / "split.json"
            split_path.write_text("{}", encoding="utf-8")
            freeze = corpus.freeze_record(labels_path, evidence_path, split_path, None,
                                          "2026-09-12T00:00:00+00:00")
            freeze_path = workspace / "freeze.json"
            freeze_path.write_text(json.dumps(freeze), encoding="utf-8")

            # Tamper with the frozen evidence after the freeze record was written.
            evidence_path.write_bytes(evidence_path.read_bytes() + b"\n")

            with self.assertRaises(FreezeError):
                rme.run_experiment("run-tampered", "calibration", [IDS[0]], evidence_path,
                                   freeze_path, workspace / "out", raw_store_dir=workspace / "raw",
                                   provider_name="anthropic", model_id="claude-sonnet-5-fixture",
                                   replay=True)


if __name__ == "__main__":
    unittest.main()
