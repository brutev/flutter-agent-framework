from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RepairResult:
    repaired: bool
    attempts: int
    error: str | None = None


class RepairController:
    def __init__(self, max_attempts: int = 2):
        if max_attempts < 0:
            raise ValueError("max_attempts must be non-negative")
        self.max_attempts = max_attempts

    def run(self, error: str, attempt: Callable[[str], bool | tuple[bool, str]]) -> RepairResult:
        if not error.strip():
            return RepairResult(True, 0)
        previous = None
        for index in range(1, self.max_attempts + 1):
            if error == previous:
                return RepairResult(False, index - 1, "Repeated failure detected; repair stopped")
            previous = error
            result = attempt(error)
            if isinstance(result, tuple):
                repaired, next_error = result
            else:
                repaired, next_error = result, error
            if repaired:
                return RepairResult(True, index)
            error = next_error
        return RepairResult(False, self.max_attempts, "Repair attempts exhausted")

