from pathlib import Path

from flutter_agent.skills.loader import load_skills
from flutter_agent.standards.loader import load_rules


def test_load_rules_from_toml(tmp_path: Path) -> None:
    path = tmp_path / "rules.toml"
    path.write_text(
        '[architecture]\ndomain_forbidden_imports = ["flutter", "dio"]\n'
        '[naming]\ncubit_filename_pattern = "^[a-z_]+_cubit\\\\.dart$"\n',
        encoding="utf-8",
    )
    rules = load_rules(path)
    assert rules.domain_forbidden_imports == ("flutter", "dio")


def test_load_skills_from_toml_directory(tmp_path: Path) -> None:
    (tmp_path / "cubit.toml").write_text(
        'name = "cubit"\ninstructions = "Create states and tests"\ntriggers = ["cubit"]\n',
        encoding="utf-8",
    )
    selected = load_skills(tmp_path).select("Add a Cubit")
    assert selected[0].name == "cubit"

