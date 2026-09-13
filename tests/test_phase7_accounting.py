"""Synthetic cohort accounting and exact request replay regressions for P7-3."""
import unittest
from unittest.mock import patch
from uuid import UUID

from tests.fixtures import article, temporary_directory
from tests.test_classifier import valid_output
from tools import run_model_experiment as rme
from tools.records import read_jsonl, write_jsonl
from tools.inference_budget import SpendLedger


IDS = [str(UUID(int=n)) for n in (701, 702)]
USAGE = {"input_tokens": 100, "output_tokens": 20}


class CountingProvider:
    def __init__(self, invalid=False):
        self.calls = []
        self.invalid = invalid

    def __call__(self, prompt, digest, attempt):
        article_id = prompt["evidence"]["article_id"]
        self.calls.append((article_id, digest, attempt))
        raw = "broken" if self.invalid else valid_output(entity_matches=[{
            "entity_id": "neuberger", "economic_role": "manager",
            "involvement": "direct_involvement", "evidence_refs": [article_id],
        }])
        return {"raw": raw, "usage": dict(USAGE)}


class Phase7AccountingTests(unittest.TestCase):
    def run_fixture(self, workspace, name, ids=IDS, settings=None):
        evidence = workspace / "evidence.jsonl"
        if not evidence.exists():
            write_jsonl(evidence, [article(
                article_id=article_id,
                original_url=f"https://example.com/{article_id}",
                canonical_url=f"https://example.com/{article_id}",
            ) for article_id in IDS])
        return rme.run_experiment(
            name, "calibration", ids, evidence, None, workspace / name,
            raw_store_dir=workspace / "raw", provider_name="deepseek",
            model_id="fixture-model", inference_settings=settings,
            spend_ledger=SpendLedger(workspace / 'synthetic-spend.jsonl', cap_usd='25'),
        )

    def test_grouped_events_keep_all_article_usage_and_attempts(self):
        provider = CountingProvider()
        with temporary_directory() as workspace, patch.object(rme, "build_provider",
                                                             return_value=provider):
            report, manifest = self.run_fixture(workspace, "initial")
            self.assertEqual(len(provider.calls), 2)
            self.assertEqual(report["predicted_events"], 1)
            self.assertEqual(manifest["usage_totals"],
                             {"input_tokens": 200, "output_tokens": 40})
            rows = read_jsonl(workspace / "initial" / "article-attempts.jsonl")
            self.assertEqual({row["article_id"] for row in rows}, set(IDS))
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(len(row["attempts"]) == 1 for row in rows))

    def test_exact_replay_has_zero_incremental_usage_and_preserves_source_usage(self):
        provider = CountingProvider()
        with temporary_directory() as workspace, patch.object(rme, "build_provider",
                                                             return_value=provider):
            self.run_fixture(workspace, "initial")
            provider.calls.clear()
            report, manifest = self.run_fixture(workspace, "repeat")
            self.assertEqual(provider.calls, [])
            self.assertEqual(report["predicted_events"], 1)
            self.assertEqual(manifest["replayed_articles"], 2)
            self.assertEqual(manifest["incremental_usage_totals"],
                             {"input_tokens": 0, "output_tokens": 0})
            self.assertEqual(manifest["usage_totals"],
                             {"input_tokens": 200, "output_tokens": 40})

    def test_terminal_invalid_attempts_are_replayed_without_new_paid_retries(self):
        provider = CountingProvider(invalid=True)
        with temporary_directory() as workspace, patch.object(rme, "build_provider",
                                                             return_value=provider):
            self.run_fixture(workspace, "initial", ids=IDS[:1])
            self.assertEqual(len(provider.calls), 2)
            provider.calls.clear()
            report, manifest = self.run_fixture(workspace, "repeat", ids=IDS[:1])
            self.assertEqual(provider.calls, [])
            self.assertEqual(report["recommendations"], {"review_required": 1})
            self.assertEqual(manifest["replayed_articles"], 1)
            self.assertEqual(manifest["incremental_usage_totals"],
                             {"input_tokens": 0, "output_tokens": 0})
            self.assertEqual(manifest["usage_totals"],
                             {"input_tokens": 200, "output_tokens": 40})

    def test_different_settings_do_not_replay_the_same_article(self):
        provider = CountingProvider()
        with temporary_directory() as workspace, patch.object(rme, "build_provider",
                                                             return_value=provider):
            self.run_fixture(workspace, "first", ids=IDS[:1],
                             settings={"max_output_tokens": 16384})
            self.run_fixture(workspace, "second", ids=IDS[:1],
                             settings={"max_output_tokens": 32768})
            self.assertEqual(len(provider.calls), 2)
            self.assertNotEqual(provider.calls[0][1], provider.calls[1][1])


if __name__ == "__main__":
    unittest.main()
