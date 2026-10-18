from pathlib import Path
import tomllib

from flutter_agent.config import AgentConfig, ProviderConfig


def load_agent_config(project_root: Path) -> AgentConfig:
    root = project_root.expanduser().resolve()
    path = root / ".flutter-agent" / "config.toml"
    if not path.exists():
        return AgentConfig(project_root=root)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    provider = ProviderConfig(**data.get("provider", {}))
    agent = data.get("agent", {})
    return AgentConfig(project_root=root, provider=provider, **agent)

