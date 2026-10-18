from dataclasses import dataclass
from pathlib import Path

from flutter_agent.contracts.model import TaskContract
from flutter_agent.security.scope import ProjectScope, ScopeViolation


@dataclass(frozen=True)
class ContractResult:
    passed: bool
    findings: tuple[str, ...] = ()


def validate_contract(root: Path, contract: TaskContract) -> ContractResult:
    scope = ProjectScope(root)
    findings: list[str] = []
    contents: list[str] = []
    for relative in contract.required_files:
        try:
            path = scope.resolve(relative)
        except ScopeViolation:
            findings.append(f"Required file is outside project scope: {relative}")
            continue
        if not path.is_file():
            findings.append(f"Missing required file: {relative}")
            continue
        try:
            contents.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            findings.append(f"Required file is not readable: {relative}")

    combined = "\n".join(contents)
    for symbol in contract.required_symbols:
        if symbol not in combined:
            findings.append(f"Missing required symbol: {symbol}")
    for forbidden in contract.forbidden_content:
        if forbidden in combined:
            findings.append(f"Forbidden content found: {forbidden}")
    return ContractResult(not findings, tuple(findings))

