from dataclasses import dataclass
import os

from flutter_agent.config import AgentConfig


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    ok: bool
    message: str


def check_configuration(config: AgentConfig) -> list[PreflightCheck]:
    root = config.resolved_root()
    checks = [
        PreflightCheck("project", root.is_dir(), f"Project root: {root}"),
        PreflightCheck("provider", config.provider.name in {"openrouter", "ollama", "openai_compatible"}, f"Provider: {config.provider.name}"),
        PreflightCheck("model", bool(config.provider.model), "Model is configured" if config.provider.model else "Model is not configured"),
        PreflightCheck("tools", config.provider.supports_tools, "Tool calling is supported" if config.provider.supports_tools else "Configured model does not support tool calling"),
    ]
    if config.provider.name in {"openrouter", "openai_compatible"}:
        key_present = bool(os.environ.get(config.provider.api_key_env))
        checks.append(PreflightCheck("api_key", key_present, "OpenRouter API key is available" if key_present else f"Missing API key: {config.provider.api_key_env}"))
    return checks

