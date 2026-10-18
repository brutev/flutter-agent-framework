from pathlib import Path

from flutter_agent.project.overrides import apply_project_overrides
from flutter_agent.project.profile import ProjectProfile


def test_project_overrides_replace_detected_values(tmp_path: Path) -> None:
    path = tmp_path / ".flutter-agent"
    path.mkdir()
    (path / "config.toml").write_text(
        '[project]\narchitecture = "clean_architecture"\nstate_management = "cubit"\n',
        encoding="utf-8",
    )
    detected = ProjectProfile("unknown", "unknown", "unknown", "unknown", "unknown", ())
    updated = apply_project_overrides(tmp_path, detected)
    assert updated.architecture == "clean_architecture"
    assert updated.state_management == "cubit"

