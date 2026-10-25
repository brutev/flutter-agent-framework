from typing import Any

import httpx

from flutter_agent.config import ProviderConfig
from flutter_agent.providers.base import ModelResponse, ModelProvider
from flutter_agent.providers.normalize import normalize_openai
from flutter_agent.providers.errors import ProviderFailure, ProviderFailureCategory
from flutter_agent.security.secrets import redact_secrets


class OpenRouterProvider(ModelProvider):
    name = "openrouter"

    def __init__(self, config: ProviderConfig):
        self.config = config
        # Keep the model visible in fallback diagnostics.
        self.name = f"openrouter:{config.model}"

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        key = self.config.api_key()
        if not key:
            raise RuntimeError(f"Missing API key environment variable: {self.config.api_key_env}")
        if not self.config.model:
            raise ValueError("A model must be configured for OpenRouter")

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_output_tokens,
        }
        if tools:
            payload["tools"] = tools

        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            response = client.post(
                f"{self.config.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if response.status_code == 401:
                    raise ProviderFailure(
                        "OpenRouter authentication failed (401). Check OPENROUTER_API_KEY in this terminal.",
                        ProviderFailureCategory.PERMANENT,
                    ) from exc
                detail = ""
                try:
                    body = response.json()
                    error = body.get("error", {}) if isinstance(body, dict) else {}
                    if isinstance(error, dict):
                        detail = error.get("message") or error.get("code") or str(error)
                    elif error:
                        detail = str(error)
                except ValueError:
                    detail = response.text[:240].strip()
                suffix = f": {redact_secrets(detail, [key])}" if detail else ""
                category = ProviderFailureCategory.RATE_LIMIT if response.status_code == 429 else (
                    ProviderFailureCategory.TRANSIENT if response.status_code >= 500 else ProviderFailureCategory.PERMANENT
                )
                raise ProviderFailure(f"OpenRouter request failed ({response.status_code}){suffix}", category) from exc
            data = response.json()

        # Some OpenRouter gateways return a JSON error with HTTP 200 (or a
        # provider-specific envelope) instead of the OpenAI `choices` shape.
        # Turn that into a normal provider failure so fallback routing can try
        # the next model and the user sees the actual reason.
        if not isinstance(data, dict) or not isinstance(data.get("choices"), list) or not data["choices"]:
            error = data.get("error") if isinstance(data, dict) else None
            if isinstance(error, dict):
                detail = error.get("message") or error.get("code") or str(error)
            elif error:
                detail = str(error)
            else:
                detail = f"unexpected response shape: {list(data) if isinstance(data, dict) else type(data).__name__}"
            raise ProviderFailure(
                f"OpenRouter model {self.config.model} failed: {detail}",
                ProviderFailureCategory.MALFORMED_RESPONSE,
            )

        return normalize_openai(data)

