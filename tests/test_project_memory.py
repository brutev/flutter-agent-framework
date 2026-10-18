from pathlib import Path

from flutter_agent.project.memory import load_profile, save_profile
from flutter_agent.project.profile import ProjectProfile


def test_project_profile_round_trips(tmp_path: Path) -> None:
    profile = ProjectProfile("clean_architecture", "cubit_or_bloc", "dio", "go_router", "get_it", ("dio", "get_it"))
    path = save_profile(tmp_path, profile)
    assert path.name == "project_profile.json"
    assert load_profile(tmp_path) == profile

