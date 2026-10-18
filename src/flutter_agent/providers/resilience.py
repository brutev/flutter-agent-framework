from __future__ import annotations

import time
from typing import Any

from flutter_agent.providers.base import ModelProvider, ModelResponse


class ResilientProvider(ModelProvider):
    """Adds bounded retries and a small circuit breaker to a provider."""

    name = "resilient"

    def __init__(self, provider: ModelProvider, retries: int = 2, backoff_seconds: float = 0.25,
                 failure_threshold: int = 3, cooldown_seconds: float = 30.0):
        self.provider = provider
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.opened_at: float | None = None
        self.name = getattr(provider, "name", "provider")

    def _retryable(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return any(token in text for token in ("429", "502", "503", "504", "timeout", "temporarily"))

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelResponse:
        if self.opened_at is not None:
            if time.monotonic() - self.opened_at < self.cooldown_seconds:
                raise RuntimeError(f"Circuit open for {self.name}; provider temporarily disabled")
            self.opened_at = None
            self.failures = 0

        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                result = self.provider.complete(messages, tools)
                self.failures = 0
                return result
            except Exception as exc:
                last = exc
                if not self._retryable(exc) or attempt >= self.retries:
                    break
                time.sleep(self.backoff_seconds * (2 ** attempt))

        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()
        raise RuntimeError(f"{self.name} unavailable after retries: {last}") from last
