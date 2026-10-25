from flutter_agent.reporting.report import DeliveryReport
from flutter_agent.tasks import LifecyclePhase, PlanStep, RiskLevel, TaskLifecycle, TaskStatus, TaskType, create_task


def test_delivery_report_serializes_core_run_data() -> None:
    report = DeliveryReport(
        task="Add login",
        completed=True,
        stages=("analyst", "implementer"),
        outputs=("analysis", "implementation"),
    )
    data = report.to_dict()
    assert data["completed"] is True
    assert data["stages"] == ["analyst", "implementer"]
    assert "generated_at" in data


def test_delivery_report_is_derived_from_lifecycle_record(tmp_path) -> None:
    lifecycle = TaskLifecycle()
    task = create_task("Add login", tmp_path, ("Login works",))
    task = lifecycle.transition(task, LifecyclePhase.CLASSIFY, TaskStatus.IN_PROGRESS, "classified", task_type=TaskType.FEATURE, risk=RiskLevel.MEDIUM)
    task = lifecycle.transition(task, LifecyclePhase.PLAN, TaskStatus.PLANNED, "planned", plan=(PlanStep("one", "implement"),))
    task = lifecycle.transition(task, LifecyclePhase.EXECUTE, TaskStatus.IN_PROGRESS, "implemented")
    task = lifecycle.transition(task, LifecyclePhase.VERIFY, TaskStatus.VERIFIED, "checks passed", ("snapshot:abc",))
    task = lifecycle.transition(task, LifecyclePhase.REVIEW, TaskStatus.REVIEW_REQUIRED, "independent review pending")
    task = lifecycle.transition(task, LifecyclePhase.DELIVER, TaskStatus.REVIEW_REQUIRED, "report generated")
    report = DeliveryReport.from_task(task, completed=True)
    assert report.to_dict()["status"] == "REVIEW_REQUIRED"
    assert report.to_dict()["task_record"]["phase"] == "DELIVER"

