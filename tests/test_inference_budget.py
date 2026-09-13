"""Spend reservations survive interruption; all values/calls are synthetic."""
import unittest
from tests.fixtures import temporary_directory


class BudgetTests(unittest.TestCase):
    def test_unsettled_request_remains_charged_and_cannot_be_dispatched_twice(self):
        from tools.inference_budget import SpendLedger, BudgetStop
        with temporary_directory() as root:
            budget = SpendLedger(root / 'budget.jsonl', cap_usd='0.05')
            budget.reserve('request1', 65536, 16384)
            recovered = SpendLedger(root / 'budget.jsonl', cap_usd='0.05')
            with self.assertRaises(BudgetStop):
                recovered.reserve('request1', 65536, 16384)
            with self.assertRaises(BudgetStop):
                recovered.reserve('request2', 65536, 16384)

    def test_known_usage_releases_unused_reservation_but_unknown_usage_does_not(self):
        from tools.inference_budget import SpendLedger
        with temporary_directory() as root:
            b = SpendLedger(root / 'budget.jsonl', cap_usd='1')
            b.reserve('known', 65536, 16384)
            b.settle('known', {'prompt_tokens': 100, 'completion_tokens': 20})
            self.assertAlmostEqual(float(b.summary()['charged_usd']), .000054)
            b.reserve('unknown', 65536, 16384)
            b.settle('unknown', {})
            self.assertAlmostEqual(float(b.summary()['charged_usd']), .0393756)

    def test_changing_cap_or_rates_cannot_reopen_existing_authorization(self):
        from tools.inference_budget import SpendLedger, BudgetStop
        with temporary_directory() as root:
            p = root / 'budget.jsonl'
            SpendLedger(p, cap_usd='1')
            with self.assertRaises(BudgetStop):
                SpendLedger(p, cap_usd='2')
