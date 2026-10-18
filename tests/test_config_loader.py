from pathlib import Path

from flutter_agent.config_loader import load_agent_config


def test_load_agent_config_from_project_toml(tmp_path: Path) -> None:
    directory = tmp_path / ".flutter-agent"
    directory.mkdir()
    (directory / "config.toml").write_text(
        '[provider]\nname = "openrouter"\nmodel = "test/model"\n'
        'input_per_million = 1.0\noutput_per_million = 2.0\n'
        '[agent]\nmax_steps = 4\nbudget_usd = 3.0\n',
        encoding="utf-8",
    )
    config = load_agent_config(tmp_path)
    assert config.provider.model == "test/model"
    assert config.max_steps == 4
    assert config.budget_usd == 3.0

