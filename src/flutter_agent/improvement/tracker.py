from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class ImprovementProposal:
    category: str
    occurrences: int
    recommendation: str


_RECOMMENDATIONS = {
    "formatting": "Run deterministic formatting before verification.",
    "architecture": "Add or strengthen a deterministic dependency or layering check.",
    "missing_regression_test": "Strengthen the selected playbook's regression-test gate.",
    "provider_tool_call": "Tighten tool-call schema validation and provider feedback.",
    "path_scope": "Strengthen centralized path validation and adversarial scope tests.",
}


class FailureTracker:
    def __init__(self, proposal_threshold: int = 2):
        if proposal_threshold < 2:
            raise ValueError("Structural proposals require at least two observed failures")
        self.proposal_threshold = proposal_threshold
        self._failures: Counter[str] = Counter()

    def record(self, category: str) -> None:
        if not category.strip():
            raise ValueError("Failure category must not be empty")
        self._failures[category] += 1

    def proposals(self) -> tuple[ImprovementProposal, ...]:
        return tuple(
            ImprovementProposal(category, count, _RECOMMENDATIONS.get(category, "Investigate a deterministic safeguard."))
            for category, count in sorted(self._failures.items())
            if count >= self.proposal_threshold
        )
