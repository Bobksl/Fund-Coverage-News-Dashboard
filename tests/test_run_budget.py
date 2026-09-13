"""T1: the real CLI must enforce one shared authorization before HTTP dispatch."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from tests.fixtures import article, temporary_directory
from tests.test_deepseek_provider import FakeOpener, response_bytes
from tools import run_model_experiment as rme
from tools.inference_budget import BudgetStop, SpendLedger
from tools.providers.deepseek_provider import DeepSeekProvider
from tools.records import read_jsonl, write_jsonl
from tests.test_phase7_accounting import CountingProvider


class RunBudgetTests(unittest.TestCase):
    def args(self, root, replay=False, cap=None, output='out'):
        (root / 'ids.json').write_text('["a1"]', encoding='utf-8')
        if not (root / 'evidence.jsonl').exists():
            write_jsonl(root / 'evidence.jsonl', [article()])
        args = ['synthetic', 'calibration', str(root / 'ids.json'),
                str(root / 'evidence.jsonl'), str(root / output),
                '--provider', 'deepseek', '--model', 'deepseek-flash']
        if replay:
            args.append('--replay')
        if cap is not None:
            args += ['--spend-ledger', str(root / 'spend.jsonl'), '--cap-usd', cap,
                     '--input-per-million', '0.30', '--output-per-million', '1.20']
        return args

    def test_live_cli_requires_budget_before_provider_construction(self):
        with temporary_directory() as root, patch.object(rme, 'build_provider') as build:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                rme.main(self.args(root))
            build.assert_not_called()

    def test_live_function_requires_budget_before_provider_construction(self):
        with temporary_directory() as root, patch.object(rme, 'build_provider') as build:
            with self.assertRaisesRegex(ValueError, 'SpendLedger'):
                rme.run_experiment('synthetic', 'calibration', ['a1'], root / 'missing.jsonl',
                                   None, root / 'out', provider_name='deepseek', model_id='m')
            build.assert_not_called()

    def test_cli_requires_explicit_rates_as_well_as_cap(self):
        with temporary_directory() as root, patch.object(rme, 'build_provider') as build:
            args = self.args(root, cap='25')[:-2]
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                rme.main(args)
            build.assert_not_called()

    def test_budget_stop_after_one_article_preserves_partial_ledger_not_predictions(self):
        with temporary_directory() as root:
            write_jsonl(root / 'evidence.jsonl', [article(article_id=i) for i in ('a1', 'a2')])
            counting = CountingProvider()
            def provider(prompt, digest, attempt):
                if prompt['evidence']['article_id'] == 'a2':
                    raise BudgetStop('synthetic cap stop')
                return counting(prompt, digest, attempt)
            budget = SpendLedger(root / 'spend.jsonl', '25')
            with patch.object(rme, 'build_provider', return_value=provider), self.assertRaises(BudgetStop):
                rme.run_experiment('partial', 'calibration', ['a1', 'a2'], root / 'evidence.jsonl',
                                   None, root / 'out', provider_name='deepseek', model_id='fixture',
                                   spend_ledger=budget)
            m = json.loads((root / 'out/run-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual((m['status'], m['articles_completed'], m['articles_requested']),
                             ('incomplete', 1, 2))
            self.assertEqual(len(read_jsonl(root / 'out/article-attempts.jsonl')), 1)
            self.assertFalse((root / 'out/predictions.jsonl').exists())

    def test_changed_cap_is_incomplete_before_provider_construction(self):
        with temporary_directory() as root, patch.object(rme, 'build_provider') as build:
            SpendLedger(root / 'spend.jsonl', '25')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rme.main(self.args(root, cap='26')), 2)
            build.assert_not_called()
            m = json.loads((root / 'out/run-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(m['status'], 'incomplete')
            self.assertEqual(read_jsonl(root / 'spend.jsonl')[0]['cap_usd'], '25')

    def test_tiny_cap_leaves_incomplete_record_and_no_http_call(self):
        opener = FakeOpener(response_bytes('{}'))
        with temporary_directory() as root:
            def provider(name, model, **kwargs):
                return DeepSeekProvider(model, opener=opener, **kwargs)
            with patch.object(rme, 'build_provider', side_effect=provider), \
                    patch.object(DeepSeekProvider, '_api_key', return_value='synthetic-key'), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = rme.main(self.args(root, cap='0.00000001'))
            self.assertEqual(code, 2)
            self.assertEqual(opener.calls, [])
            manifest = json.loads((root / 'out/run-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['status'], 'incomplete')
            self.assertEqual(manifest['stop_reason'], 'budget_stop')
            self.assertEqual(manifest['articles_completed'], 0)
            self.assertEqual(manifest['cost_basis'], read_jsonl(root / 'spend.jsonl')[0])
            self.assertFalse((root / 'out/predictions.jsonl').exists())

    def test_replay_without_ledger_adds_zero_spend(self):
        with temporary_directory() as root, patch.object(rme, 'build_provider') as build:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rme.main(self.args(root, replay=True)), 0)
            build.assert_not_called()
            manifest = json.loads((root / 'out/run-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['incremental_cost_usd'], '0')
            self.assertFalse((root / 'spend.jsonl').exists())

    def test_completed_run_records_ledger_header_and_shared_charge(self):
        opener = FakeOpener(response_bytes('broken'))
        with temporary_directory() as root:
            def provider(name, model, **kwargs):
                return DeepSeekProvider(model, opener=opener, **kwargs)
            with patch.object(rme, 'build_provider', side_effect=provider), \
                    patch.object(DeepSeekProvider, '_api_key', return_value='synthetic-key'), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rme.main(self.args(root, cap='25')), 0)
            manifest = json.loads((root / 'out/run-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['status'], 'completed')
            self.assertEqual(manifest['cost_basis'], read_jsonl(root / 'spend.jsonl')[0])
            self.assertGreater(float(manifest['incremental_cost_usd']), 0)
            self.assertEqual(manifest['budget_summary']['http_attempts'], 2)

    def test_transport_retry_needs_its_own_reservation(self):
        opener = FakeOpener(response_bytes('{}'), fail_times=1)
        with temporary_directory() as root:
            budget = SpendLedger(root / 'spend.jsonl', cap_usd='0.025')
            provider = DeepSeekProvider('deepseek-flash', opener=opener, budget=budget)
            with patch.object(provider, '_api_key', return_value='synthetic-key'), \
                    patch('tools.providers.deepseek_provider.time.sleep'):
                with self.assertRaises(BudgetStop):
                    provider({}, 'synthetic-request', 1)
            self.assertEqual(len(opener.calls), 1)
            self.assertEqual(budget.summary()['unsettled_requests'], 1)
