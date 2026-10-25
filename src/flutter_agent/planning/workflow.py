from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class WorkflowResult:
    completed: bool
    outputs: tuple[str, ...] = ()
    repairs: int = 0
    error: str | None = None


class Orchestrator(Protocol):
    def run(self, specs: list[Any], context: str): ...


class WorkflowExecutor:
    def __init__(self, orchestrator: Orchestrator, max_repairs: int = 2):
        self.orchestrator = orchestrator
        self.max_repairs = max_repairs

    def run(self, specs: list[Any], task: str, verify: Callable[[tuple[str, ...]], tuple[bool, str]]) -> WorkflowResult:
        context = task
        previous_error: str | None = None
        for repair_count in range(self.max_repairs + 1):
            result = self.orchestrator.run(specs, context)
            if not result.completed:
                return WorkflowResult(False, result.outputs, repair_count, result.error)
            passed, error = verify(result.outputs)
            if passed:
                return WorkflowResult(True, result.outputs, repair_count)
            if error == previous_error:
                return WorkflowResult(False, result.outputs, repair_count, "Repeated verification failure; repair stopped")
            previous_error = error
            context = f"{task}\nPrevious workflow failure:\n{error}"
        return WorkflowResult(False, result.outputs, self.max_repairs, "Verification failed after bounded repairs")

