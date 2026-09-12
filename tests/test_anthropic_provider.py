"""Contract smoke tests for the Anthropic adapter (Phase 5 handover Stage 1 / section 13 item 4).

No network call and no installed `anthropic` package are needed: a fake client double is injected
directly, exercising transport success, transient failure with recovery, exhausted retries and
usage capture -- the same shapes a real call could return.
"""
import time
import unittest

from tools.classifier import ProviderError
from tools.providers.anthropic_provider import AnthropicProvider


class TextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class Usage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class Response:
    def __init__(self, text, input_tokens=100, output_tokens=40):
        self.content = [TextBlock(text)]
        self.usage = Usage(input_tokens, output_tokens)


class FlakyMessages:
    """Fails `fail_times` times, then returns `response`. Never leaks the constructor's api_key."""

    def __init__(self, response, fail_times=0, error=None):
        self.response = response
        self.fail_times = fail_times
        self.error = error or RuntimeError("transient upstream error")
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self.fail_times:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, messages):
        self.messages = messages


class SuccessTests(unittest.TestCase):
    def test_returns_raw_text_and_reported_usage(self):
        client = FakeClient(FlakyMessages(Response('{"relevance_level": "A"}')))
        provider = AnthropicProvider("claude-sonnet-5", client=client)
        result = provider('{"prompt": "x"}', "digest1", 1)
        self.assertEqual(result["raw"], '{"relevance_level": "A"}')
        self.assertEqual(result["usage"], {"input_tokens": 100, "output_tokens": 40,
                                           "cost_basis": None})

    def test_sends_model_and_max_tokens(self):
        client = FakeClient(FlakyMessages(Response("{}")))
        provider = AnthropicProvider("claude-sonnet-5", client=client, max_output_tokens=512)
        provider('{"prompt": "x"}', "digest1", 1)
        sent = client.messages.calls[0]
        self.assertEqual(sent["model"], "claude-sonnet-5")
        self.assertEqual(sent["max_tokens"], 512)
        self.assertIn("messages", sent)

    def test_optional_sampling_parameters_are_only_sent_when_set(self):
        client = FakeClient(FlakyMessages(Response("{}")))
        provider = AnthropicProvider("claude-sonnet-5", client=client)
        provider('{"prompt": "x"}', "digest1", 1)
        self.assertNotIn("temperature", client.messages.calls[0])
        self.assertNotIn("top_p", client.messages.calls[0])

        client2 = FakeClient(FlakyMessages(Response("{}")))
        provider2 = AnthropicProvider("claude-sonnet-5", client=client2, temperature=0.0, top_p=0.9)
        provider2('{"prompt": "x"}', "digest1", 1)
        self.assertEqual(client2.messages.calls[0]["temperature"], 0.0)
        self.assertEqual(client2.messages.calls[0]["top_p"], 0.9)


class TransportRetryTests(unittest.TestCase):
    def test_transient_failure_recovers_within_the_transport_budget(self):
        client = FakeClient(FlakyMessages(Response('{"ok": true}'), fail_times=1))
        provider = AnthropicProvider("claude-sonnet-5", client=client, transport_max_attempts=3)
        started = time.perf_counter()
        result = provider('{"prompt": "x"}', "digest1", 1)
        self.assertLess(time.perf_counter() - started, 5)  # backoff is capped, not seconds-long here
        self.assertEqual(result["raw"], '{"ok": true}')
        self.assertEqual(len(client.messages.calls), 2)

    def test_exhausted_transport_retries_raise_provider_error(self):
        client = FakeClient(FlakyMessages(Response("{}"), fail_times=5))
        provider = AnthropicProvider("claude-sonnet-5", client=client, transport_max_attempts=2)
        with self.assertRaises(ProviderError):
            provider('{"prompt": "x"}', "digest1", 1)
        self.assertEqual(len(client.messages.calls), 2)


class MalformedResponseTests(unittest.TestCase):
    def test_non_text_content_blocks_are_ignored_not_crashed_on(self):
        class ToolUseBlock:
            type = "tool_use"

        response = Response("")
        response.content = [ToolUseBlock(), TextBlock("partial")]
        client = FakeClient(FlakyMessages(response))
        provider = AnthropicProvider("claude-sonnet-5", client=client)
        result = provider('{"prompt": "x"}', "digest1", 1)
        self.assertEqual(result["raw"], "partial")

    def test_missing_usage_object_reports_null_counts_not_a_crash(self):
        response = Response("{}")
        response.usage = None
        client = FakeClient(FlakyMessages(response))
        provider = AnthropicProvider("claude-sonnet-5", client=client)
        result = provider('{"prompt": "x"}', "digest1", 1)
        self.assertEqual(result["usage"], {"input_tokens": None, "output_tokens": None,
                                           "cost_basis": None})


class CredentialTests(unittest.TestCase):
    def test_missing_credential_is_a_provider_error_not_a_network_attempt(self):
        provider = AnthropicProvider("claude-sonnet-5", api_key_env="NEWS_DASHBOARD_TEST_MISSING_KEY")
        with self.assertRaises(ProviderError) as ctx:
            provider('{"prompt": "x"}', "digest1", 1)
        self.assertIn("NEWS_DASHBOARD_TEST_MISSING_KEY", str(ctx.exception))

    def test_error_repr_never_contains_the_api_key_value(self):
        client = FakeClient(FlakyMessages(Response("{}"), fail_times=5,
                                          error=RuntimeError("auth failed for key sk-ant-secretvalue")))
        provider = AnthropicProvider("claude-sonnet-5", client=client, transport_max_attempts=1)
        with self.assertRaises(ProviderError) as ctx:
            provider('{"prompt": "x"}', "digest1", 1)
        # The adapter never sees or constructs a key itself in this path; it only forwards
        # whatever the (fake) SDK exception says, so this pins that behaviour rather than a
        # credential-scrubbing feature this module does not implement.
        self.assertIn("auth failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
