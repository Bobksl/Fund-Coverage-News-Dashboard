"""Contract smoke tests for the DeepSeek adapter (Phase 5 handover Stage 1 / section 13 item 4).

No network call and no real credential are needed: a fake `urlopen` double is injected directly.
"""
import io
import json
import os
import unittest
import urllib.error

from tests.fixtures import temporary_directory
from tools.classifier import ProviderError
from tools.inference_budget import BudgetStop, SpendLedger
from tools.providers.deepseek_provider import DeepSeekProvider


def response_bytes(content, prompt_tokens=100, completion_tokens=40):
    body = {"id": "x", "object": "chat.completion", "choices": [
                {"index": 0, "message": {"role": "assistant", "content": content},
                 "finish_reason": "stop"}],
           "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                     "total_tokens": prompt_tokens + completion_tokens}}
    return json.dumps(body).encode("utf-8")


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    """Records requests; fails `fail_times` times before returning `response`."""

    def __init__(self, response, fail_times=0, error=None):
        self.response = response
        self.fail_times = fail_times
        self.error = error or RuntimeError("transient upstream error")
        self.calls = []

    def urlopen(self, request, timeout=None):
        self.calls.append(request)
        if len(self.calls) <= self.fail_times:
            raise self.error
        return FakeResponse(self.response)


class SuccessTests(unittest.TestCase):
    def test_returns_raw_text_and_reported_usage(self):
        opener = FakeOpener(response_bytes('{"relevance_level": "A"}'))
        provider = DeepSeekProvider("deepseek-flash", opener=opener,
                                    api_key_env="DEEPSEEK_API_KEY_TEST")
        with self._set_env():
            result = provider('{"prompt": "x"}', "digest1", 1)
        self.assertEqual(result["raw"], '{"relevance_level": "A"}')
        self.assertEqual(result["usage"], {"input_tokens": 100, "output_tokens": 40,
                                           "cost_basis": None})

    def test_sends_model_json_mode_and_authorization_header(self):
        opener = FakeOpener(response_bytes("{}"))
        provider = DeepSeekProvider("deepseek-flash", opener=opener, max_output_tokens=512,
                                    api_key_env="DEEPSEEK_API_KEY_TEST")
        with self._set_env(key="test-key-value"):
            provider('{"prompt": "x"}', "digest1", 1)
        request = opener.calls[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "deepseek-flash")
        self.assertEqual(body["max_tokens"], 512)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(request.headers.get("Authorization"), "Bearer test-key-value")
        # The literal key value must never appear anywhere except this one header.
        self.assertNotIn("test-key-value", request.data.decode("utf-8"))

    def _set_env(self, key="fixture-key"):
        import os
        import contextlib

        @contextlib.contextmanager
        def _ctx():
            os.environ["DEEPSEEK_API_KEY_TEST"] = key
            try:
                yield
            finally:
                os.environ.pop("DEEPSEEK_API_KEY_TEST", None)
        return _ctx()


class DeepSeekProviderEnvTests(unittest.TestCase):
    """Uses a dedicated env var name so this test never touches a real DEEPSEEK_API_KEY."""

    def test_missing_credential_is_a_provider_error_not_a_network_attempt(self):
        provider = DeepSeekProvider("deepseek-flash", api_key_env="NEWS_DASHBOARD_TEST_MISSING_KEY")
        with self.assertRaises(ProviderError) as ctx:
            provider('{"prompt": "x"}', "digest1", 1)
        self.assertIn("NEWS_DASHBOARD_TEST_MISSING_KEY", str(ctx.exception))


class TransportRetryTests(unittest.TestCase):
    def test_transient_failure_recovers_within_the_transport_budget(self):
        opener = FakeOpener(response_bytes('{"ok": true}'), fail_times=1)
        provider = DeepSeekProvider("deepseek-flash", opener=opener, transport_max_attempts=3,
                                    api_key_env="NEWS_DASHBOARD_TEST_KEY")
        import os
        os.environ["NEWS_DASHBOARD_TEST_KEY"] = "x"
        try:
            result = provider('{"prompt": "x"}', "digest1", 1)
        finally:
            os.environ.pop("NEWS_DASHBOARD_TEST_KEY", None)
        self.assertEqual(result["raw"], '{"ok": true}')
        self.assertEqual(len(opener.calls), 2)

    def test_exhausted_transport_retries_raise_provider_error(self):
        opener = FakeOpener(response_bytes("{}"), fail_times=5)
        provider = DeepSeekProvider("deepseek-flash", opener=opener, transport_max_attempts=2,
                                    api_key_env="NEWS_DASHBOARD_TEST_KEY")
        import os
        os.environ["NEWS_DASHBOARD_TEST_KEY"] = "x"
        try:
            with self.assertRaises(ProviderError):
                provider('{"prompt": "x"}', "digest1", 1)
        finally:
            os.environ.pop("NEWS_DASHBOARD_TEST_KEY", None)
        self.assertEqual(len(opener.calls), 2)

    def test_http_error_response_body_is_captured_in_the_provider_error(self):
        class FailingOpener:
            calls = []

            def urlopen(self, request, timeout=None):
                self.calls.append(request)
                raise urllib.error.HTTPError(
                    "https://api.deepseek.com/chat/completions", 401,
                    "Unauthorized", {}, io.BytesIO(b'{"error": "invalid_api_key"}'))

        provider = DeepSeekProvider("deepseek-flash", opener=FailingOpener(),
                                    transport_max_attempts=1, api_key_env="NEWS_DASHBOARD_TEST_KEY")
        import os
        os.environ["NEWS_DASHBOARD_TEST_KEY"] = "x"
        try:
            with self.assertRaises(ProviderError) as ctx:
                provider('{"prompt": "x"}', "digest1", 1)
        finally:
            os.environ.pop("NEWS_DASHBOARD_TEST_KEY", None)
        self.assertIn("invalid_api_key", str(ctx.exception))


class MalformedResponseTests(unittest.TestCase):
    def test_missing_choices_is_a_provider_error_not_a_crash(self):
        opener = FakeOpener(json.dumps({"usage": {}}).encode("utf-8"))
        provider = DeepSeekProvider("deepseek-flash", opener=opener,
                                    api_key_env="NEWS_DASHBOARD_TEST_KEY")
        import os
        os.environ["NEWS_DASHBOARD_TEST_KEY"] = "x"
        try:
            with self.assertRaises(ProviderError):
                provider('{"prompt": "x"}', "digest1", 1)
        finally:
            os.environ.pop("NEWS_DASHBOARD_TEST_KEY", None)

    def test_missing_usage_reports_null_counts_not_a_crash(self):
        body = {"choices": [{"message": {"content": "{}"}}]}
        opener = FakeOpener(json.dumps(body).encode("utf-8"))
        provider = DeepSeekProvider("deepseek-flash", opener=opener,
                                    api_key_env="NEWS_DASHBOARD_TEST_KEY")
        import os
        os.environ["NEWS_DASHBOARD_TEST_KEY"] = "x"
        try:
            result = provider('{"prompt": "x"}', "digest1", 1)
        finally:
            os.environ.pop("NEWS_DASHBOARD_TEST_KEY", None)
        self.assertEqual(result["usage"], {"input_tokens": None, "output_tokens": None,
                                           "cost_basis": None})


class BudgetIntegrationTests(unittest.TestCase):
    """P7-3: a provider constructed with `budget=` must actually reserve before dispatch and
    settle to real usage after -- a SpendLedger that exists but is never called enforces nothing."""

    def _provider(self, workspace, opener, cap_usd="10.00", **kwargs):
        os.environ["NEWS_DASHBOARD_TEST_KEY"] = "x"
        ledger = SpendLedger(workspace / "budget.jsonl", cap_usd=cap_usd)
        provider = DeepSeekProvider("deepseek-flash", opener=opener,
                                    api_key_env="NEWS_DASHBOARD_TEST_KEY", budget=ledger, **kwargs)
        return provider, ledger

    def tearDown(self):
        os.environ.pop("NEWS_DASHBOARD_TEST_KEY", None)

    def test_successful_call_settles_to_actual_reported_usage(self):
        with temporary_directory() as workspace:
            opener = FakeOpener(response_bytes('{"ok": true}', prompt_tokens=1000,
                                               completion_tokens=200))
            provider, ledger = self._provider(workspace, opener)
            provider('{"prompt": "x"}', "digest1", 1)
            summary = ledger.summary()
            # 1000 input * 0.30/M + 200 output * 1.20/M = 0.0003 + 0.00024 = 0.00054
            self.assertEqual(summary["charged_usd"], "0.00054")
            self.assertEqual(summary["unsettled_requests"], 0)

    def test_a_call_that_would_exceed_the_cap_never_reaches_the_network(self):
        with temporary_directory() as workspace:
            opener = FakeOpener(response_bytes("{}"))
            provider, ledger = self._provider(workspace, opener, cap_usd="0.00000001")
            with self.assertRaises(BudgetStop):
                provider('{"prompt": "x"}', "digest1", 1)
            self.assertEqual(opener.calls, [])

    def test_a_transport_failure_leaves_the_reservation_charged_at_the_full_ceiling(self):
        with temporary_directory() as workspace:
            opener = FakeOpener(response_bytes("{}"), fail_times=5)
            provider, ledger = self._provider(workspace, opener, transport_max_attempts=1)
            with self.assertRaises(ProviderError):
                provider('{"prompt": "x"}', "digest1", 1)
            summary = ledger.summary()
            self.assertEqual(summary["unsettled_requests"], 1)
            self.assertNotEqual(summary["charged_usd"], "0")

    def test_two_attempts_for_the_same_digest_reserve_separately(self):
        with temporary_directory() as workspace:
            opener = FakeOpener(response_bytes('{"ok": true}'))
            provider, ledger = self._provider(workspace, opener)
            provider('{"prompt": "x"}', "digest1", 1)
            provider('{"prompt": "x"}', "digest1", 2)
            self.assertEqual(ledger.summary()["http_attempts"], 2)

    def test_no_budget_supplied_skips_ledger_entirely(self):
        with temporary_directory() as workspace:
            opener = FakeOpener(response_bytes('{"ok": true}'))
            os.environ["NEWS_DASHBOARD_TEST_KEY"] = "x"
            provider = DeepSeekProvider("deepseek-flash", opener=opener,
                                        api_key_env="NEWS_DASHBOARD_TEST_KEY")
            result = provider('{"prompt": "x"}', "digest1", 1)
            self.assertEqual(result["raw"], '{"ok": true}')


if __name__ == "__main__":
    unittest.main()
