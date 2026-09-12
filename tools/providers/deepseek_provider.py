"""DeepSeek chat-completions adapter for tools.classifier.StructuredClassifier / tools.drafting.Drafter.

Verified against current DeepSeek API docs at implementation time (2026-09-12,
api-docs.deepseek.com): OpenAI-compatible endpoint `https://api.deepseek.com/chat/completions`;
model IDs `deepseek-flash` (fast/economical) and `deepseek-v4-pro`; request fields model/messages/
temperature/top_p/max_tokens/response_format; response `usage.prompt_tokens`/`completion_tokens`
(and `prompt_tokens_details.prompt_cache_hit_tokens`/`prompt_cache_miss_tokens`, not used here
since classifier.py's usage contract only tracks input/output, not cache split). JSON-only output
is requested via `response_format: {"type": "json_object"}` plus an explicit system instruction,
per the docs' own warning that response_format alone is not sufficient.

No credential is read, logged, or written by anything outside this module: the API key comes from
the environment variable named by `api_key_env` (default DEEPSEEK_API_KEY), and nothing here
prints or persists it. This module makes plain HTTPS requests via the standard library (`urllib`)
rather than requiring a vendor SDK, since DeepSeek's API is a simple OpenAI-compatible REST
endpoint and no additional package is needed.

Transport-level retry/timeout live here, separate from the schema-level retry in
tools.classifier.run_attempts: a request that times out or errors is retried by this adapter
before the classifier ever sees an attempt; only once transport retries are exhausted does it
raise ProviderError, which the classifier records as `transport_failure` and retries again at the
schema level (a fresh generation, never a resend of the same bytes).
"""
import json
import os
import time
import urllib.error
import urllib.request

from tools.classifier import ProviderError

DEFAULT_BASE_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_SYSTEM_PROMPT = ("Respond with a single JSON object only, matching the schema implied by "
                         "the supplied rules and ontology. No prose outside the JSON.")


class DeepSeekProvider:
    """Callable provider: __call__(prompt, digest, attempt) -> {"raw": str, "usage": {...}}.

    Pass `opener` to inject a test double exposing `.urlopen(request, timeout=...) ->
    context-manager yielding a file-like with .read()` and skip the real network call entirely --
    this is how the contract-smoke tests exercise malformed/partial/transport-failure responses
    without spending anything.
    """

    def __init__(self, model_id, api_key_env="DEEPSEEK_API_KEY", base_url=DEFAULT_BASE_URL,
                temperature=None, top_p=None, max_output_tokens=2048, timeout_seconds=60.0,
                transport_max_attempts=3, system_prompt=None, opener=None):
        self.model_id = model_id
        self.api_key_env = api_key_env
        self.base_url = base_url
        self.temperature = temperature
        self.top_p = top_p
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.transport_max_attempts = transport_max_attempts
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.opener = opener or urllib.request

    def _api_key(self):
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise ProviderError(
                f"{self.api_key_env} is not set; a provider credential is required to run live "
                f"inference")
        return api_key

    def _request_body(self, prompt_json):
        body = {"model": self.model_id,
               "messages": [{"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt_json}],
               "max_tokens": self.max_output_tokens,
               "response_format": {"type": "json_object"}}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if self.top_p is not None:
            body["top_p"] = self.top_p
        return body

    def __call__(self, prompt, digest, attempt):
        prompt_json = json.dumps(prompt, ensure_ascii=False)
        api_key = self._api_key()
        payload = json.dumps(self._request_body(prompt_json)).encode("utf-8")
        request = urllib.request.Request(
            self.base_url, data=payload, method="POST",
            headers={"Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"})
        last_error = None
        response_body = None
        for transport_attempt in range(1, self.transport_max_attempts + 1):
            try:
                with self.opener.urlopen(request, timeout=self.timeout_seconds) as response:
                    response_body = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace") if hasattr(error, "read") else str(error)
                last_error = f"HTTP {error.code}: {detail[:500]}"
            except Exception as error:  # noqa: BLE001 -- any transport failure is uniform here
                last_error = f"{type(error).__name__}: {error}"
            if transport_attempt < self.transport_max_attempts:
                time.sleep(min(0.5 * (2 ** (transport_attempt - 1)), 8))
        if response_body is None:
            raise ProviderError(
                f"DeepSeek request failed after {self.transport_max_attempts} attempts: {last_error}")
        try:
            text = response_body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError(f"DeepSeek response has an unexpected shape: {error}") from error
        usage = response_body.get("usage") or {}
        return {"raw": text,
                "usage": {"input_tokens": usage.get("prompt_tokens"),
                         "output_tokens": usage.get("completion_tokens"),
                         "cost_basis": None}}


__all__ = ["DeepSeekProvider"]
