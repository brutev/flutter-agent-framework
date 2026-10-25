from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from flutter_agent.tasks.models import (
    BudgetLimits,
    LifecyclePhase,
    PermissionPolicy,
    PlanStep,
    RiskLevel,
    TaskRecord,
    TaskStatus,
    TaskType,
    TransitionRecord,
    VerificationRequirement,
)

_NEXT_PHASE = {
    LifecyclePhase.INTAKE: LifecyclePhase.CLASSIFY,
    LifecyclePhase.CLASSIFY: LifecyclePhase.PLAN,
    LifecyclePhase.PLAN: LifecyclePhase.EXECUTE,
    LifecyclePhase.EXECUTE: LifecyclePhase.VERIFY,
    LifecyclePhase.VERIFY: LifecyclePhase.REVIEW,
    LifecyclePhase.REVIEW: LifecyclePhase.DELIVER,
}


def create_task(
    user_goal: str,
    project_root: Path,
    acceptance_criteria: tuple[str, ...] = (),
    *,
    budget: BudgetLimits | None = None,
) -> TaskRecord:
    if not user_goal.strip():
        raise ValueError("Task goal must not be empty")
    root = project_root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project root is not a directory: {root}")
    return TaskRecord(
        task_id=str(uuid4()),
        user_goal=user_goal,
        project_root=str(root),
        acceptance_criteria=acceptance_criteria,
        budget=budget or BudgetLimits(),
    )


class TaskLifecycle:
    """Validates lifecycle order and records every transition outcome."""

    def transition(
        self,
        task: TaskRecord,
        to_phase: LifecyclePhase,
        status: TaskStatus,
        outcome: str,
        evidence_refs: tuple[str, ...] = (),
        *,
        task_type: TaskType | None = None,
        risk: RiskLevel | None = None,
        permissions: PermissionPolicy | None = None,
        plan: tuple[PlanStep, ...] | None = None,
        verification_requirements: tuple[VerificationRequirement, ...] | None = None,
    ) -> TaskRecord:
        if _NEXT_PHASE.get(task.phase) is not to_phase:
            raise ValueError(f"Invalid lifecycle transition: {task.phase.value} -> {to_phase.value}")
        if not outcome.strip():
            raise ValueError("Lifecycle transition outcome must not be empty")
        self._check_preconditions(task, to_phase, task_type, risk, plan)
        event = TransitionRecord(task.phase, to_phase, status, outcome, evidence_refs)
        return replace(
            task,
            phase=to_phase,
            status=status,
            task_type=task_type or task.task_type,
            risk=risk or task.risk,
            permissions=permissions or task.permissions,
            plan=plan if plan is not None else task.plan,
            verification_requirements=(
                verification_requirements
                if verification_requirements is not None
                else task.verification_requirements
            ),
            evidence_refs=task.evidence_refs + tuple(ref for ref in evidence_refs if ref not in task.evidence_refs),
            transitions=task.transitions + (event,),
        )

    @staticmethod
    def _check_preconditions(
        task: TaskRecord,
        phase: LifecyclePhase,
        task_type: TaskType | None,
        risk: RiskLevel | None,
        plan: tuple[PlanStep, ...] | None,
    ) -> None:
        if phase is LifecyclePhase.CLASSIFY and (task_type is None or risk is None):
            raise ValueError("Classification requires task type and risk")
        if phase is LifecyclePhase.PLAN:
            if task.task_type is None:
                raise ValueError("Planning requires classification")
            if not plan:
                raise ValueError("Planning requires at least one step")
        if phase is LifecyclePhase.EXECUTE and not task.plan:
            raise ValueError("Execution requires a non-empty plan")
        if phase is LifecyclePhase.VERIFY and task.status not in {TaskStatus.IN_PROGRESS, TaskStatus.FAILED}:
            raise ValueError("Verification requires a recorded execution outcome")
        if phase is LifecyclePhase.REVIEW and task.status not in {
            TaskStatus.VERIFIED,
            TaskStatus.FAILED,
            TaskStatus.UNVERIFIED,
            TaskStatus.BLOCKED,
        }:
            raise ValueError("Review requires a verification outcome")
        if phase is LifecyclePhase.DELIVER and task.status not in {
            TaskStatus.VERIFIED,
            TaskStatus.REVIEW_REQUIRED,
            TaskStatus.FAILED,
            TaskStatus.UNVERIFIED,
            TaskStatus.BLOCKED,
        }:
            raise ValueError("Delivery requires a review outcome")
