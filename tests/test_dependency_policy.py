from pathlib import Path

from flutter_agent.standards.dependencies import validate_dependencies


def test_dependency_policy_reports_forbidden_package(tmp_path: Path) -> None:
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text("dependencies:\n  dio: ^5.0.0\n  http: ^1.0.0\n", encoding="utf-8")
    findings = validate_dependencies(pubspec, forbidden=("http",))
    assert any("forbidden" in finding.lower() for finding in findings)


def test_dependency_policy_reports_missing_approved_package(tmp_path: Path) -> None:
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text("dependencies:\n  dio: ^5.0.0\n", encoding="utf-8")
    findings = validate_dependencies(pubspec, approved=("dio", "get_it"))
    assert any("missing approved" in finding.lower() for finding in findings)

