import pytest

from flutter_agent.config import ProviderConfig
from flutter_agent.providers.openai_compatible import OpenAICompatibleProvider
from flutter_agent.providers.ollama import OllamaProvider
from flutter_agent.providers.base import ToolCall
from flutter_agent.providers.registry import create_provider


def test_registry_supports_openai_compatible() -> None:
    provider = create_provider(ProviderConfig(name="openai_compatible", model="x"))
    assert isinstance(provider, OpenAICompatibleProvider)


def test_registry_supports_ollama() -> None:
    provider = create_provider(ProviderConfig(name="ollama", model="qwen"))
    assert isinstance(provider, OllamaProvider)


def test_registry_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError):
        create_provider(ProviderConfig(name="unknown"))


def test_ollama_normalizes_tool_calls(monkeypatch) -> None:
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "", "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "a.dart"}}}]}}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("flutter_agent.providers.ollama.httpx.Client", Client)
    response = OllamaProvider(ProviderConfig(name="ollama", model="qwen")).complete([], [])
    assert response.tool_calls == (ToolCall("ollama-call-0", "read_file", {"path": "a.dart"}),)

