from dataclasses import dataclass

from flutter_agent.agents.orchestrator import OrchestrationResult, SubagentSpec
from flutter_agent.planning.workflow import WorkflowExecutor


@dataclass
class FakeOrchestrator:
    calls: int = 0

    def run(self, specs, context):
        self.calls += 1
        return OrchestrationResult(True, (f"run-{self.calls}",))


def test_workflow_repairs_failed_verification() -> None:
    orchestrator = FakeOrchestrator()
    checks = iter([(False, "analyzer error"), (True, "")])
    result = WorkflowExecutor(orchestrator, max_repairs=2).run([], "task", lambda _: next(checks))
    assert result.completed
    assert result.repairs == 1
    assert orchestrator.calls == 2


def test_workflow_stops_repeating_identical_verification_failure() -> None:
    orchestrator = FakeOrchestrator()
    result = WorkflowExecutor(orchestrator, max_repairs=3).run(
        [], "task", lambda _: (False, "same analyzer failure")
    )
    assert not result.completed
    assert result.repairs == 1
    assert orchestrator.calls == 2
    assert "repeated" in (result.error or "").lower()

