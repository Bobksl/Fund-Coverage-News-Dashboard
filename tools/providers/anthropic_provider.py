"""Anthropic Messages API adapter for tools.classifier.StructuredClassifier / tools.drafting.Drafter.

Verified against the current Messages API docs at implementation time (2026-09-12,
platform.claude.com/docs/en/api/messages): request fields model/max_tokens/messages/system;
response usage.input_tokens/output_tokens. This adapter asks for a single JSON object via the
system prompt and parses the returned text rather than depending on structured-output/schema
mode being available for a given model or account (newer, unevenly supported); the classifier and
drafter already treat a malformed response as a review case, never a crash, so this does not
weaken anything.

No credential is read, logged, or written by anything outside this module: the API key comes
from the environment variable named by `api_key_env` (default ANTHROPIC_API_KEY), and nothing
here prints or persists it. Importing this module never requires the `anthropic` package to be
installed -- the SDK is imported lazily, only when a real call is actually made and no `client`
was already injected (see `AnthropicProvider.__init__`), so the rest of the test suite and the
replay-only path never need it.

Transport-level retry/timeout live here, separate from the schema-level retry in
tools.classifier.run_attempts: a request that times out or errors is retried by this adapter
before the classifier ever sees an attempt; only once transport retries are exhausted does it
raise ProviderError, which the classifier records as `transport_failure` and retries again at the
schema level (a fresh generation, never a resend of the same bytes).
"""
import json
import os
import time

from tools.classifier import ProviderError

DEFAULT_SYSTEM_PROMPT = ("Respond with a single JSON object only, matching the schema implied by "
                         "the supplied rules and ontology. No prose outside the JSON.")


class AnthropicProvider:
    """Callable provider: __call__(prompt, digest, attempt) -> {"raw": str, "usage": {...}}.

    Pass `client` to inject an already-constructed SDK client (or a test double exposing the same
    `.messages.create(...)` shape) and skip the lazy SDK import and credential lookup entirely --
    this is how the contract-smoke tests exercise malformed/partial/transport-failure responses
    without a network call or an installed package.
    """

    def __init__(self, model_id, api_key_env="ANTHROPIC_API_KEY", temperature=None, top_p=None,
                max_output_tokens=2048, timeout_seconds=60.0, transport_max_attempts=3,
                system_prompt=None, client=None):
        self.model_id = model_id
        self.api_key_env = api_key_env
        self.temperature = temperature
        self.top_p = top_p
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.transport_max_attempts = transport_max_attempts
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._client = client

    def _client_instance(self):
        if self._client is None:
            api_key = os.environ.get(self.api_key_env)
            if not api_key:
                raise ProviderError(
                    f"{self.api_key_env} is not set; a provider credential is required to run "
                    f"live inference")
            import anthropic  # Lazy: importing this module must never require the SDK.
            self._client = anthropic.Anthropic(api_key=api_key, timeout=self.timeout_seconds)
        return self._client

    def _request_kwargs(self, prompt_json):
        kwargs = {"model": self.model_id, "max_tokens": self.max_output_tokens,
                 "system": self.system_prompt,
                 "messages": [{"role": "user", "content": prompt_json}]}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        return kwargs

    def __call__(self, prompt, digest, attempt):
        prompt_json = json.dumps(prompt, ensure_ascii=False)
        client = self._client_instance()
        last_error = None
        response = None
        for transport_attempt in range(1, self.transport_max_attempts + 1):
            try:
                response = client.messages.create(**self._request_kwargs(prompt_json))
                break
            except Exception as error:  # The SDK raises its own typed exceptions for every
                                        # failure mode; all of them are a transport failure here,
                                        # never a schema decision.
                last_error = error
                if transport_attempt < self.transport_max_attempts:
                    time.sleep(min(0.5 * (2 ** (transport_attempt - 1)), 8))
                    continue
        if response is None:
            raise ProviderError(
                f"Anthropic request failed after {self.transport_max_attempts} attempts: "
                f"{type(last_error).__name__}: {last_error}")
        text = "".join(block.text for block in response.content
                       if getattr(block, "type", None) == "text")
        usage = getattr(response, "usage", None)
        return {"raw": text,
                "usage": {"input_tokens": getattr(usage, "input_tokens", None),
                         "output_tokens": getattr(usage, "output_tokens", None),
                         "cost_basis": None}}


__all__ = ["AnthropicProvider"]
