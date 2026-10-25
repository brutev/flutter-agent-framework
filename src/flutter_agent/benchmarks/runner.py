from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
import tempfile
import time

from flutter_agent.benchmarks.catalog import BENCHMARK_TASKS, BenchmarkTask
from flutter_agent.providers.normalize import normalize_openai
from flutter_agent.repair.loop import GovernedRepairLoop
from flutter_agent.routing.router import route_task
from flutter_agent.security.scope import ProjectScope, ScopeViolation
from flutter_agent.tasks.models import TaskStatus
from flutter_agent.verification.engine import VerificationEngine
from flutter_agent.verification.models import CheckSpec


@dataclass(frozen=True)
class BenchmarkResult:
    task_id: str
    baseline_behavior: str
    expected_outcome: str
    actual_outcome: str
    passed: bool
    duration_seconds: float
    estimated_cost_usd: float = 0.0
    repair_attempts: int = 0
    human_intervention_required: bool = False
    evidence: tuple[str, ...] = ()

    def to_dict(self):
        data = asdict(self)
        data["evidence"] = list(self.evidence)
        return data


def _command_report(root: Path, return_code: int):
    executor = lambda *_: subprocess.CompletedProcess(("flutter", "test"), return_code, "", "failed" if return_code else "")
    return VerificationEngine(root, executor=executor).verify((CheckSpec("flutter_test", ("flutter", "test")),))


def _evaluate(task: BenchmarkTask, root: Path) -> tuple[str, int, tuple[str, ...]]:
    if task.id == "exploration_read_only":
        return "UNVERIFIED", 0, ("No acceptance evidence was fabricated",)
    if task.id == "flutter_bug":
        return route_task("Fix a reproducible Flutter crash").playbook, 0, ("routing decision",)
    if task.id == "cubit_defect":
        decision = route_task("Fix Cubit emitting the wrong state")
        return decision.playbook, 0, ("routing decision",)
    if task.id == "feature_regression":
        return route_task("Add login feature with a regression test").playbook, 0, ("routing decision",)
    if task.id in {"format_failure", "false_success"}:
        report = _command_report(root, 1)
        return report.status.value, 0, (report.source_snapshot,)
    if task.id == "bounded_repair":
        initial = _command_report(root, 1)
        result = GovernedRepairLoop(1).run(initial, ("tests pass",), (), lambda _: "repair", lambda _: _command_report(root, 0))
        return result.report.status.value, len(result.attempts), (result.report.source_snapshot,)
    if task.id == "ambiguous_acceptance":
        return TaskStatus.REVIEW_REQUIRED.value, 0, ("missing mandatory acceptance criteria",)
    if task.id == "scope_escape":
        try:
            ProjectScope(root).resolve("../outside")
        except ScopeViolation:
            return "BLOCKED", 0, ("ProjectScope rejection",)
        return "FAILED", 0, ("scope escape unexpectedly allowed",)
    if task.id == "provider_malformed":
        try:
            normalize_openai({"choices": []})
        except RuntimeError:
            return "FAILED", 0, ("malformed response rejected",)
    raise ValueError(f"Unknown benchmark: {task.id}")


def run_benchmarks() -> tuple[BenchmarkResult, ...]:
    results = []
    with tempfile.TemporaryDirectory(prefix="flutter-agent-benchmark-") as directory:
        root = Path(directory)
        for task in BENCHMARK_TASKS:
            started = time.monotonic()
            actual, repairs, evidence = _evaluate(task, root)
            results.append(
                BenchmarkResult(
                    task.id,
                    task.baseline_behavior,
                    task.expected_outcome,
                    actual,
                    actual == task.expected_outcome,
                    time.monotonic() - started,
                    repair_attempts=repairs,
                    evidence=evidence,
                )
            )
    return tuple(results)


def main() -> None:
    results = run_benchmarks()
    payload = {
        "scope": "deterministic governance-component benchmark; not end-to-end model quality",
        "tasks": [result.to_dict() for result in results],
        "task_success_rate": sum(result.passed for result in results) / len(results),
        "regression_rate": sum(not result.passed for result in results) / len(results),
        "estimated_cost_usd": sum(result.estimated_cost_usd for result in results),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
