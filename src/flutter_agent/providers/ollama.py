from typing import Any

import httpx

from flutter_agent.config import ProviderConfig
from flutter_agent.providers.base import ModelResponse, ModelProvider
from flutter_agent.providers.normalize import normalize_ollama


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, config: ProviderConfig):
        self.config = config

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelResponse:
        if not self.config.model:
            raise ValueError("An Ollama model must be configured")
        payload: dict[str, Any] = {"model": self.config.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            response = client.post(f"{self.config.base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return normalize_ollama(data)

