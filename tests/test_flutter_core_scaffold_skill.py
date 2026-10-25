from pathlib import Path
import subprocess
import sys


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "flutter-core-scaffold"
    / "scripts"
    / "scaffold_core.py"
)


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "app"
    (root / "lib").mkdir(parents=True)
    (root / "pubspec.yaml").write_text(
        "name: scaffold_test\ndependencies:\n  flutter:\n    sdk: flutter\n",
        encoding="utf-8",
    )
    return root


def _run(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_dry_run_does_not_create_files(tmp_path: Path) -> None:
    root = _project(tmp_path)

    result = _run(root, "--dry-run")

    assert result.returncode == 0
    assert "planned=13 skipped=0" in result.stdout
    assert not (root / "lib" / "core").exists()


def test_scaffold_is_repeatable_and_does_not_overwrite(tmp_path: Path) -> None:
    root = _project(tmp_path)

    first = _run(root)
    customized = root / "lib" / "core" / "config" / "app_config.dart"
    customized.write_text("// project-owned\n", encoding="utf-8")
    second = _run(root)

    assert first.returncode == 0
    assert "created=13 skipped=0" in first.stdout
    assert second.returncode == 0
    assert "created=0 skipped=13" in second.stdout
    assert customized.read_text(encoding="utf-8") == "// project-owned\n"


def test_rejects_non_project_root(tmp_path: Path) -> None:
    root = tmp_path / "not-a-project"
    root.mkdir()

    result = _run(root)

    assert result.returncode == 2
    assert "not a Flutter project root" in result.stderr


def test_rejects_symlink_escape(tmp_path: Path) -> None:
    root = _project(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "lib" / "core").symlink_to(outside, target_is_directory=True)

    result = _run(root)

    assert result.returncode == 2
    assert "target escapes project root" in result.stderr
    assert not (outside / "core.dart").exists()
