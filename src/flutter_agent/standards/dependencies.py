from pathlib import Path
import re


def validate_dependencies(
    pubspec: Path,
    approved: tuple[str, ...] = (),
    forbidden: tuple[str, ...] = (),
) -> list[str]:
    if not pubspec.exists():
        return [f"Missing pubspec.yaml: {pubspec}"]
    text = pubspec.read_text(encoding="utf-8")
    dependencies = set(re.findall(r"^\s{2}([a-zA-Z0-9_]+):", text, re.MULTILINE))
    findings = [f"Forbidden dependency installed: {name}" for name in forbidden if name in dependencies]
    findings.extend(f"Missing approved dependency: {name}" for name in approved if name not in dependencies)
    return findings

