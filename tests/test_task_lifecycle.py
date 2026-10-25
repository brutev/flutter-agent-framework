import pytest

from flutter_agent.tasks import (
    LifecyclePhase,
    PlanStep,
    RiskLevel,
    TaskLifecycle,
    TaskStatus,
    TaskType,
    VerificationRequirement,
    create_task,
)


def planned_task(tmp_path):
    lifecycle = TaskLifecycle()
    task = create_task("Fix login", tmp_path, ("Login succeeds",))
    task = lifecycle.transition(
        task,
        LifecyclePhase.CLASSIFY,
        TaskStatus.IN_PROGRESS,
        "Classified as a bug fix",
        task_type=TaskType.BUG_FIX,
        risk=RiskLevel.MEDIUM,
    )
    return lifecycle.transition(
        task,
        LifecyclePhase.PLAN,
        TaskStatus.PLANNED,
        "Plan and checks recorded",
        plan=(PlanStep("reproduce", "Reproduce the login defect"),),
        verification_requirements=(VerificationRequirement("flutter_test", ("flutter", "test")),),
    )


def test_lifecycle_records_ordered_outcomes_and_evidence(tmp_path) -> None:
    lifecycle = TaskLifecycle()
    task = planned_task(tmp_path)
    task = lifecycle.transition(task, LifecyclePhase.EXECUTE, TaskStatus.IN_PROGRESS, "Fix implemented")
    task = lifecycle.transition(
        task,
        LifecyclePhase.VERIFY,
        TaskStatus.VERIFIED,
        "Mandatory checks passed",
        ("verification:sha256:abc",),
    )
    task = lifecycle.transition(task, LifecyclePhase.REVIEW, TaskStatus.VERIFIED, "Independent review passed")
    task = lifecycle.transition(task, LifecyclePhase.DELIVER, TaskStatus.VERIFIED, "Delivery report generated")
    assert task.phase is LifecyclePhase.DELIVER
    assert task.status is TaskStatus.VERIFIED
    assert task.evidence_refs == ("verification:sha256:abc",)
    assert [event.to_phase for event in task.transitions] == list(LifecyclePhase)[1:]
    assert task.to_dict()["status"] == "VERIFIED"


def test_lifecycle_rejects_skipped_phase(tmp_path) -> None:
    task = create_task("Fix login", tmp_path)
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        TaskLifecycle().transition(task, LifecyclePhase.PLAN, TaskStatus.PLANNED, "skip")


def test_execution_requires_non_empty_plan(tmp_path) -> None:
    lifecycle = TaskLifecycle()
    task = create_task("Fix login", tmp_path)
    task = lifecycle.transition(
        task,
        LifecyclePhase.CLASSIFY,
        TaskStatus.IN_PROGRESS,
        "classified",
        task_type=TaskType.BUG_FIX,
        risk=RiskLevel.MEDIUM,
    )
    with pytest.raises(ValueError, match="at least one step"):
        lifecycle.transition(task, LifecyclePhase.PLAN, TaskStatus.PLANNED, "empty", plan=())
