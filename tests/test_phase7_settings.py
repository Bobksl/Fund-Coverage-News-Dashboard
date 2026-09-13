"""Synthetic request/provenance regressions; never reads real credentials."""
import json
import unittest
from tools import classifier
from tools.providers.deepseek_provider import DeepSeekProvider
from tests.test_deepseek_provider import FakeOpener, SuccessTests


class EffectiveSettingsTests(unittest.TestCase):
    def test_thinking_is_part_of_canonical_identity(self):
        first = classifier.build_inference_settings(thinking={"type": "enabled"})
        second = classifier.build_inference_settings(thinking={"type": "disabled"})
        self.assertNotEqual(classifier.settings_hash(first), classifier.settings_hash(second))

    def test_explicit_request_matches_effective_settings(self):
        p = DeepSeekProvider("deepseek-flash", thinking={"type": "enabled"},
                             reasoning_effort="high", top_p=1, max_output_tokens=16384)
        settings = p.inference_settings()
        body = p._request_body("{}")
        self.assertEqual(body["thinking"], settings["thinking"])
        self.assertEqual(body["reasoning_effort"], "high")
        self.assertEqual(body["top_p"], 1)
        self.assertNotIn("temperature", body)
        self.assertEqual(settings["max_output_tokens"], body["max_tokens"])
        other = DeepSeekProvider("deepseek-flash", system_prompt="Different JSON instruction")
        self.assertNotEqual(settings["system_prompt_sha256"],
                            other.inference_settings()["system_prompt_sha256"])

    def test_response_envelope_preserves_truncation_model_and_usage(self):
        envelope = {"id": "response-1", "model": "served-version", "system_fingerprint": "fp",
                    "choices": [{"finish_reason": "length", "message": {"content": None}}],
                    "usage": {"prompt_tokens": 90, "completion_tokens": 16384,
                              "prompt_cache_miss_tokens": 90}}
        p = DeepSeekProvider("deepseek-flash", opener=FakeOpener(json.dumps(envelope).encode()),
                             api_key_env="DEEPSEEK_API_KEY_TEST")
        with SuccessTests()._set_env():
            result = p({}, "digest", 1)
        self.assertEqual(result["provider_response"], envelope)
        self.assertEqual(result["finish_reason"], "length")
        self.assertIsNone(result["raw"])
