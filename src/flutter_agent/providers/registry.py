from flutter_agent.config import ProviderConfig
from flutter_agent.providers.base import ModelProvider
from flutter_agent.providers.openrouter import OpenRouterProvider
from flutter_agent.providers.openai_compatible import OpenAICompatibleProvider
from flutter_agent.providers.ollama import OllamaProvider


def create_provider(config: ProviderConfig) -> ModelProvider:
    if config.name == "openrouter":
        return OpenRouterProvider(config)
    if config.name == "openai_compatible":
        return OpenAICompatibleProvider(config)
    if config.name == "ollama":
        return OllamaProvider(config)
    raise ValueError(f"Unsupported provider: {config.name}")

