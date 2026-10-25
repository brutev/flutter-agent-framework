from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from flutter_agent.verification.models import CheckEvidence, VerificationReport


@dataclass(frozen=True)
class RepairContext:
    failed_checks: tuple[CheckEvidence, ...]
    acceptance_criteria: tuple[str, ...]
    changed_files: tuple[str, ...]
    source_snapshot: str
    attempt: int


@dataclass(frozen=True)
class RepairAttempt:
    attempt: int
    before_snapshot: str
    after_snapshot: str
    affected_checks: tuple[str, ...]
    outcome: str


@dataclass(frozen=True)
class GovernedRepairResult:
    report: VerificationReport
    attempts: tuple[RepairAttempt, ...] = ()
    stopped_reason: str | None = None


class GovernedRepairLoop:
    """Bounded DIAGNOSE -> REPAIR -> REVERIFY with repeated-failure detection."""

    def __init__(self, max_attempts: int = 2):
        if max_attempts < 0:
            raise ValueError("max_attempts must be non-negative")
        self.max_attempts = max_attempts

    def run(
        self,
        initial: VerificationReport,
        acceptance_criteria: tuple[str, ...],
        changed_files: tuple[str, ...],
        repair: Callable[[RepairContext], str],
        reverify: Callable[[tuple[str, ...]], VerificationReport],
    ) -> GovernedRepairResult:
        report = initial
        attempts: list[RepairAttempt] = []
        seen_failures: set[tuple[str, str]] = set()
        for attempt_number in range(1, self.max_attempts + 1):
            if report.verified:
                return GovernedRepairResult(report, tuple(attempts))
            failed = tuple(check for check in report.checks if check.required and check.status.value != "PASSED")
            affected = tuple(check.name for check in failed)
            signature = (report.summary, report.source_snapshot)
            if signature in seen_failures:
                return GovernedRepairResult(report, tuple(attempts), "Repeated failure without new evidence")
            seen_failures.add(signature)
            context = RepairContext(
                failed,
                acceptance_criteria,
                changed_files,
                report.source_snapshot,
                attempt_number,
            )
            outcome = repair(context)
            next_report = reverify(affected)
            attempts.append(
                RepairAttempt(
                    attempt_number,
                    report.source_snapshot,
                    next_report.source_snapshot,
                    affected,
                    outcome,
                )
            )
            report = next_report
        reason = None if report.verified else "Repair attempt limit reached"
        return GovernedRepairResult(report, tuple(attempts), reason)
