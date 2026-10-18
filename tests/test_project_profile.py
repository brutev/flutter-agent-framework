from pathlib import Path

from flutter_agent.project.profile import detect_profile


def test_detect_profile_from_flutter_project(tmp_path: Path) -> None:
    (tmp_path / "pubspec.yaml").write_text(
        "dependencies:\n  flutter_bloc: ^8.0.0\n  dio: ^5.0.0\n  get_it: ^7.0.0\n  go_router: ^14.0.0\n",
        encoding="utf-8",
    )
    (tmp_path / "lib" / "domain" / "entities").mkdir(parents=True)
    (tmp_path / "lib" / "data").mkdir()
    profile = detect_profile(tmp_path)
    assert profile.architecture == "clean_architecture"
    assert profile.state_management == "cubit_or_bloc"
    assert profile.http_client == "dio"
    assert profile.routing == "go_router"
    assert "get_it" in profile.dependencies


def test_detect_profile_handles_unknown_project(tmp_path: Path) -> None:
    profile = detect_profile(tmp_path)
    assert profile.architecture == "unknown"
    assert profile.dependencies == ()

