from typing import Any

from flutter_agent.providers.base import ModelProvider, ModelResponse
from flutter_agent.providers.errors import ProviderFailure, ProviderFailureCategory


class FallbackProvider(ModelProvider):
    name = "fallback"

    def __init__(self, providers: tuple[ModelProvider, ...]):
        if not providers:
            raise ValueError("At least one provider is required")
        self.providers = providers

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelResponse:
        failures: list[str] = []
        for provider in self.providers:
            try:
                return provider.complete(messages, tools)
            except (RuntimeError, ValueError) as exc:
                failures.append(f"{provider.name}: {exc}")
                if isinstance(exc, ProviderFailure) and exc.category in {
                    ProviderFailureCategory.PERMANENT,
                    ProviderFailureCategory.CANCELLED,
                }:
                    raise
        raise RuntimeError("All model fallbacks failed: " + " | ".join(failures))

