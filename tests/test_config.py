from pathlib import Path

from flutter_agent.config import AgentConfig


def test_project_root_is_resolved(tmp_path: Path) -> None:
    config = AgentConfig(project_root=tmp_path / ".")
    assert config.resolved_root() == tmp_path.resolve()

