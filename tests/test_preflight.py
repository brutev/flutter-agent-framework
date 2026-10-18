from pathlib import Path

from flutter_agent.config import AgentConfig, ProviderConfig
from flutter_agent.preflight import check_configuration


def test_preflight_reports_missing_model_and_key(tmp_path: Path) -> None:
    checks = check_configuration(AgentConfig(project_root=tmp_path))
    messages = " ".join(check.message for check in checks if not check.ok)
    assert "model" in messages.lower()
    assert "key" in messages.lower()


def test_preflight_accepts_configured_openrouter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    config = AgentConfig(project_root=tmp_path, provider=ProviderConfig(model="test/model"))
    checks = check_configuration(config)
    assert all(check.ok for check in checks)


def test_preflight_rejects_provider_without_tool_support(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    config = AgentConfig(project_root=tmp_path, provider=ProviderConfig(model="test/model", supports_tools=False))
    checks = check_configuration(config)
    assert any(not check.ok and "tool" in check.message.lower() for check in checks)

