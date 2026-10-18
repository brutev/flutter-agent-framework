from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class SecurityFinding:
    kind: str
    path: str
    detail: str
    severity: str = "high"


SECRET_PATTERNS = (
    re.compile(r"(?i)sk-[a-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[^\s'\"]{12,}"),
)
SKIP_DIRECTORIES = {".git", ".dart_tool", "build", ".flutter-agent", "__pycache__"}


def scan_project(root: Path) -> tuple[SecurityFinding, ...]:
    """Perform a bounded, read-only scan for common accidental exposures."""
    findings: list[SecurityFinding] = []
    root = root.resolve()
    for path in root.rglob("*"):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        if path.is_symlink():
            try:
                target = path.resolve()
                if root not in target.parents and target != root:
                    findings.append(SecurityFinding("symlink_escape", str(path.relative_to(root)), str(target)))
            except OSError:
                findings.append(SecurityFinding("broken_symlink", str(path.relative_to(root)), "unresolvable target"))
            continue
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(SecurityFinding("possible_secret", str(path.relative_to(root)), "secret-like value detected"))
                break
    return tuple(findings)
