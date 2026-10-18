from dataclasses import dataclass
from pathlib import Path

from flutter_agent.agents.orchestrator import SequentialOrchestrator, SubagentSpec


@dataclass
class FakeRunner:
    calls: list[SubagentSpec]

    def run(self, spec: SubagentSpec, context: str) -> str:
        self.calls.append(spec)
        return f"{spec.role}: completed\nContext: {context}"


def test_orchestrator_runs_roles_in_order(tmp_path: Path) -> None:
    runner = FakeRunner([])
    orchestrator = SequentialOrchestrator(runner)
    result = orchestrator.run(
        [
            SubagentSpec("analyst", "Inspect project", frozenset({"read_file"})),
            SubagentSpec("implementer", "Implement feature", frozenset({"read_file", "write_file"})),
        ],
        "Feature request",
    )
    assert result.completed
    assert [call.role for call in runner.calls] == ["analyst", "implementer"]
    assert len(result.outputs) == 2


def test_orchestrator_rejects_duplicate_role() -> None:
    runner = FakeRunner([])
    result = SequentialOrchestrator(runner).run(
        [SubagentSpec("analyst", "one", frozenset()), SubagentSpec("analyst", "two", frozenset())],
        "task",
    )
    assert not result.completed
    assert "duplicate" in (result.error or "").lower()

