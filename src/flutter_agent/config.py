from pathlib import Path
import os

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    name: str = "openrouter"
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = ""
    api_key_env: str = "OPENROUTER_API_KEY"
    timeout_seconds: float = Field(default=60.0, gt=0)
    max_output_tokens: int = Field(default=4096, ge=1, le=131072)
    retry_attempts: int = Field(default=2, ge=0, le=5)
    retry_backoff_seconds: float = Field(default=0.25, ge=0, le=30)
    circuit_failure_threshold: int = Field(default=3, ge=1, le=20)
    circuit_cooldown_seconds: float = Field(default=30.0, gt=0, le=3600)
    input_per_million: float = Field(default=0.10, ge=0)
    output_per_million: float = Field(default=0.50, ge=0)
    supports_tools: bool = True
    supports_structured_output: bool = False

    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


class AgentConfig(BaseModel):
    project_root: Path
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    max_steps: int = Field(default=12, ge=1, le=100)
    max_repair_attempts: int = Field(default=2, ge=0, le=5)
    budget_usd: float = Field(default=10.0, ge=0)

    def resolved_root(self) -> Path:
        return self.project_root.expanduser().resolve()

