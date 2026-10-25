from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any


class LifecyclePhase(StrEnum):
    INTAKE = "INTAKE"
    CLASSIFY = "CLASSIFY"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REVIEW = "REVIEW"
    DELIVER = "DELIVER"


class TaskStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class TaskType(StrEnum):
    QUESTION = "question"
    EXPLORATION = "repository_exploration"
    BUG_FIX = "small_bug_fix"
    FEATURE = "feature_implementation"
    REFACTOR = "refactoring"
    ARCHITECTURE = "architecture_change"
    SECURITY = "security_sensitive_change"
    BUILD_REPAIR = "build_or_dependency_repair"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class BudgetLimits:
    usd: float = 10.0
    max_steps: int = 12
    max_repairs: int = 2
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class PermissionPolicy:
    allowed_tools: tuple[str, ...] = ()
    read_only: bool = False


@dataclass(frozen=True)
class PlanStep:
    id: str
    description: str
    dependencies: tuple[str, ...] = ()
    owned_files: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationRequirement:
    name: str
    command: tuple[str, ...] = ()
    mandatory: bool = True


@dataclass(frozen=True)
class TransitionRecord:
    from_phase: LifecyclePhase
    to_phase: LifecyclePhase
    status: TaskStatus
    outcome: str
    evidence_refs: tuple[str, ...] = ()
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    user_goal: str
    project_root: str
    acceptance_criteria: tuple[str, ...]
    scope: tuple[str, ...] = ()
    task_type: TaskType | None = None
    risk: RiskLevel | None = None
    plan: tuple[PlanStep, ...] = ()
    permissions: PermissionPolicy = field(default_factory=PermissionPolicy)
    budget: BudgetLimits = field(default_factory=BudgetLimits)
    verification_requirements: tuple[VerificationRequirement, ...] = ()
    phase: LifecyclePhase = LifecyclePhase.INTAKE
    status: TaskStatus = TaskStatus.PLANNED
    evidence_refs: tuple[str, ...] = ()
    transitions: tuple[TransitionRecord, ...] = ()

    @property
    def root(self) -> Path:
        return Path(self.project_root)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["task_type"] = self.task_type.value if self.task_type else None
        data["risk"] = self.risk.value if self.risk else None
        data["phase"] = self.phase.value
        data["status"] = self.status.value
        for transition, item in zip(self.transitions, data["transitions"]):
            item["from_phase"] = transition.from_phase.value
            item["to_phase"] = transition.to_phase.value
            item["status"] = transition.status.value
        return data
