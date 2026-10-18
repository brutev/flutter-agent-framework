from pathlib import Path
import tomllib

from flutter_agent.standards.rules import RuleSet


def load_rules(path: Path) -> RuleSet:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    architecture = data.get("architecture", {})
    naming = data.get("naming", {})
    dependencies = data.get("dependencies", {})
    return RuleSet(
        domain_forbidden_imports=tuple(architecture.get("domain_forbidden_imports", RuleSet().domain_forbidden_imports)),
        cubit_filename_pattern=naming.get("cubit_filename_pattern", RuleSet().cubit_filename_pattern),
        approved_dependencies=tuple(dependencies.get("approved", [])),
        forbidden_dependencies=tuple(dependencies.get("forbidden", [])),
    )

