import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleSet:
    domain_forbidden_imports: tuple[str, ...] = ("flutter", "dio", "get_it")
    cubit_filename_pattern: str = r"^[a-z][a-z0-9_]*_cubit\.dart$"
    approved_dependencies: tuple[str, ...] = ()
    forbidden_dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    rule: str
    message: str
    path: str


def validate_dart_source(path: str, content: str, rules: RuleSet) -> list[Finding]:
    findings: list[Finding] = []
    normalized = path.replace("\\", "/")
    if "/domain/" in f"/{normalized}" or normalized.startswith("domain/"):
        for package in rules.domain_forbidden_imports:
            if f"package:{package}/" in content or f"import '{package}" in content:
                findings.append(Finding("domain_import", f"Domain layer contains forbidden import: {package}", path))
    filename = normalized.rsplit("/", 1)[-1]
    if "/cubit/" in f"/{normalized}" and not re.fullmatch(rules.cubit_filename_pattern, filename):
        findings.append(Finding("naming", f"Cubit filename violates naming convention: {filename}", path))
    return findings

