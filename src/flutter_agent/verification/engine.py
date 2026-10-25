from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import time
from collections.abc import Callable, Iterable

from flutter_agent.contracts.model import TaskContract
from flutter_agent.contracts.validator import validate_contract
from flutter_agent.security.scope import ProjectScope
from flutter_agent.security.secrets import redact_secrets
from flutter_agent.verification.models import (
    CheckEvidence,
    CheckSpec,
    CheckStatus,
    VerificationReport,
    VerificationStatus,
)

CommandExecutor = Callable[[tuple[str, ...], Path, int], subprocess.CompletedProcess[str]]

_SNAPSHOT_EXCLUDED_DIRECTORIES = {
    ".dart_tool",
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
}
_SNAPSHOT_EXCLUDED_AGENT_DIRECTORIES = {"audit", "reports"}
_READ_ONLY_TERMS = ("describe", "explain", "inspect", "list", "read-only", "summarize")
_CHANGE_TERMS = ("add", "build", "change", "create", "edit", "feature", "fix", "implement", "refactor", "remove", "update")


def source_snapshot(project_root: Path) -> str:
    """Hash project source without following symlinks or volatile build state."""
    root = ProjectScope(project_root).root
    digest = hashlib.sha256()
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_directory = current_path.relative_to(root)
        symlinked_directories = sorted(name for name in directories if (current_path / name).is_symlink())
        for name in symlinked_directories:
            path = current_path / name
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(f"symlink:{os.readlink(path)}".encode())
            digest.update(b"\0")
        directories[:] = sorted(
            name
            for name in directories
            if name not in symlinked_directories
            if name not in _SNAPSHOT_EXCLUDED_DIRECTORIES
            and not (
                relative_directory == Path(".flutter-agent")
                and name in _SNAPSHOT_EXCLUDED_AGENT_DIRECTORIES
            )
        )
        for filename in sorted(filenames):
            path = current_path / filename
            relative = path.relative_to(root)
            if path.is_symlink():
                payload = f"symlink:{os.readlink(path)}".encode()
            else:
                try:
                    payload = path.read_bytes()
                except OSError:
                    payload = b"unreadable"
            digest.update(relative.as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(payload)
            digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def select_flutter_checks(
    project_root: Path,
    task: str,
    changed_files: Iterable[str] = (),
) -> tuple[CheckSpec, ...]:
    """Choose bounded Flutter checks from task intent and changed paths."""
    root = ProjectScope(project_root).root
    if not (root / "pubspec.yaml").is_file():
        return ()

    lowered = task.casefold()
    paths = tuple(path.replace("\\", "/") for path in changed_files)
    read_only = any(term in lowered for term in _READ_ONLY_TERMS) and not any(
        term in lowered for term in _CHANGE_TERMS
    )
    code_change = any(path.endswith(".dart") for path in paths) or not read_only
    if not code_change:
        return ()

    checks = [
        CheckSpec("dart_format", ("dart", "format", "--output=none", "--set-exit-if-changed", ".")),
        CheckSpec("flutter_analyze", ("flutter", "analyze"), timeout_seconds=180),
        CheckSpec("flutter_test", ("flutter", "test"), timeout_seconds=300),
    ]
    android_relevant = any(term in lowered for term in ("android", "apk")) or any(
        path.startswith("android/") for path in paths
    )
    if android_relevant and (root / "android").is_dir():
        checks.append(
            CheckSpec("flutter_build_apk_debug", ("flutter", "build", "apk", "--debug"), timeout_seconds=900)
        )
    return tuple(checks)


def _execute(argv: tuple[str, ...], cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )


class VerificationEngine:
    def __init__(self, project_root: Path, executor: CommandExecutor = _execute, output_limit: int = 50_000):
        self.root = ProjectScope(project_root).root
        self.executor = executor
        self.output_limit = output_limit

    def verify(
        self,
        checks: Iterable[CheckSpec],
        contract: TaskContract | None = None,
    ) -> VerificationReport:
        evidence = tuple(self._run(check) for check in checks)
        acceptance_findings: tuple[str, ...] = ()
        acceptance_failed = False
        if contract is not None:
            contract_result = validate_contract(self.root, contract)
            acceptance_findings = contract_result.findings
            acceptance_failed = not contract_result.passed

        required = tuple(item for item in evidence if item.required)
        if acceptance_failed or any(item.status is CheckStatus.FAILED for item in required):
            status = VerificationStatus.FAILED
        elif not required or any(item.status is CheckStatus.BLOCKED for item in required):
            status = VerificationStatus.UNVERIFIED
        elif all(item.status is CheckStatus.PASSED for item in required):
            status = VerificationStatus.VERIFIED
        else:
            status = VerificationStatus.UNVERIFIED
        return VerificationReport(status, source_snapshot(self.root), evidence, acceptance_findings)

    def _run(self, check: CheckSpec) -> CheckEvidence:
        started = time.monotonic()
        try:
            completed = self.executor(check.argv, self.root, check.timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return CheckEvidence(
                check.name,
                check.argv,
                str(self.root),
                check.required,
                CheckStatus.BLOCKED,
                None,
                time.monotonic() - started,
                error=redact_secrets(str(exc)),
            )
        output = redact_secrets((completed.stdout or "") + (completed.stderr or ""))[-self.output_limit :]
        status = CheckStatus.PASSED if completed.returncode == 0 else CheckStatus.FAILED
        return CheckEvidence(
            check.name,
            check.argv,
            str(self.root),
            check.required,
            status,
            completed.returncode,
            time.monotonic() - started,
            output=output,
        )
