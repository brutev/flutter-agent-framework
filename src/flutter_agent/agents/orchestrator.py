from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SubagentSpec:
    role: str
    prompt: str
    allowed_tools: frozenset[str]


@dataclass(frozen=True)
class OrchestrationResult:
    completed: bool
    outputs: tuple[str, ...] = ()
    error: str | None = None


class SubagentRunner(Protocol):
    def run(self, spec: SubagentSpec, context: str) -> str: ...


class SequentialOrchestrator:
    def __init__(self, runner: SubagentRunner):
        self.runner = runner

    def run(self, specs: list[SubagentSpec], initial_context: str) -> OrchestrationResult:
        roles = [spec.role for spec in specs]
        if len(roles) != len(set(roles)):
            return OrchestrationResult(False, error="Duplicate subagent roles are not allowed")
        context = initial_context
        outputs: list[str] = []
        for spec in specs:
            if not spec.role.strip() or not spec.prompt.strip():
                return OrchestrationResult(False, tuple(outputs), "Subagent role and prompt are required")
            try:
                output = self.runner.run(spec, context)
            except Exception as exc:
                return OrchestrationResult(False, tuple(outputs), f"Subagent {spec.role} failed: {exc}")
            outputs.append(output)
            context = output
        return OrchestrationResult(True, tuple(outputs))

