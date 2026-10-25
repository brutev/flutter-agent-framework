from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class CheckStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class CheckSpec:
    name: str
    argv: tuple[str, ...]
    required: bool = True
    timeout_seconds: int = 120

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Verification check name must not be empty")
        if not self.argv or any(not argument for argument in self.argv):
            raise ValueError("Verification command arguments must not be empty")
        if self.timeout_seconds < 1:
            raise ValueError("Verification timeout must be at least one second")


@dataclass(frozen=True)
class CheckEvidence:
    name: str
    command: tuple[str, ...]
    cwd: str
    required: bool
    status: CheckStatus
    exit_code: int | None
    duration_seconds: float
    output: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["command"] = list(self.command)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class VerificationReport:
    status: VerificationStatus
    source_snapshot: str
    checks: tuple[CheckEvidence, ...]
    acceptance_findings: tuple[str, ...] = ()

    @property
    def verified(self) -> bool:
        return self.status is VerificationStatus.VERIFIED

    @property
    def summary(self) -> str:
        if not self.checks:
            return "No verification checks were selected; required evidence is absent"
        details = [f"{check.name}: {check.status.value}" for check in self.checks]
        details.extend(self.acceptance_findings)
        return "; ".join(details)

    def is_current(self, project_root: Path) -> bool:
        from flutter_agent.verification.engine import source_snapshot

        return self.source_snapshot == source_snapshot(project_root)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "source_snapshot": self.source_snapshot,
            "checks": [check.to_dict() for check in self.checks],
            "acceptance_findings": list(self.acceptance_findings),
        }
