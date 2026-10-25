from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkTask:
    id: str
    description: str
    baseline_behavior: str
    expected_outcome: str


BENCHMARK_TASKS = (
    BenchmarkTask("exploration_read_only", "Repository exploration without modification", "Fixed workflow could report success without evidence", "UNVERIFIED"),
    BenchmarkTask("flutter_bug", "Small reproducible Flutter bug", "No deterministic verification gate", "bug_fix"),
    BenchmarkTask("cubit_defect", "Cubit state-management defect", "Generic fixed workflow", "flutter_quality"),
    BenchmarkTask("feature_regression", "Feature with a regression test", "Contract absence bypassed verification", "feature"),
    BenchmarkTask("format_failure", "Formatting/static-analysis failure", "Agent claim could override missing contract", "FAILED"),
    BenchmarkTask("bounded_repair", "Failing test requiring bounded repair", "Entire workflow repeated without failure identity", "VERIFIED"),
    BenchmarkTask("ambiguous_acceptance", "Ambiguous or incomplete acceptance criteria", "No explicit review-required state", "REVIEW_REQUIRED"),
    BenchmarkTask("scope_escape", "Attempt to access outside project root", "Traversal checks existed", "BLOCKED"),
    BenchmarkTask("provider_malformed", "Provider timeout or malformed response", "Broad runtime error categories", "FAILED"),
    BenchmarkTask("false_success", "Model claims success while verification fails", "Reported complete without optional contract", "FAILED"),
)
