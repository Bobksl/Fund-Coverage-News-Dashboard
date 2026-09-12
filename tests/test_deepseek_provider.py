"""Contract smoke tests for the DeepSeek adapter (Phase 5 handover Stage 1 / section 13 item 4).

No network call and no real credential are needed: a fake `urlopen` double is injected directly.
"""
import io
import json
import unittest
import urllib.error

from tools.classifier import ProviderError
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


if __name__ == "__main__":
    unittest.main()
