from dataclasses import dataclass

from flutter_agent.tasks.models import RiskLevel, TaskType


@dataclass(frozen=True)
class RoutingDecision:
    category: str
    models: tuple[str, ...]
    task_type: TaskType = TaskType.FEATURE
    playbook: str = "feature"
    risk: RiskLevel = RiskLevel.MEDIUM
    rationale: str = "Implementation task"
    evidence_required: tuple[str, ...] = ("verification report",)


def route_task(task: str) -> RoutingDecision:
    text = task.casefold()
    if any(word in text for word in ("release readiness", "release-ready", "ship readiness")):
        return RoutingDecision(
            "release_readiness",
            ("z-ai/glm-5.3", "deepseek/deepseek-v4.1-flash-1017"),
            TaskType.EXPLORATION,
            "release_readiness",
            RiskLevel.HIGH,
            "Release assessment requires verification but never deployment authority",
            ("verification report", "release blockers"),
        )
    if any(word in text for word in ("review the diff", "code review", "review this change")):
        return RoutingDecision(
            "code_review",
            ("z-ai/glm-5.3", "qwen/qwen3.8-max-prime"),
            TaskType.EXPLORATION,
            "code_review",
            RiskLevel.MEDIUM,
            "The requested output is an independent review",
            ("actual diff", "review findings"),
        )
    if any(word in text for word in ("list", "summarize", "describe", "read-only", "dependencies")) and not any(word in text for word in ("edit", "add", "fix", "change")):
        return RoutingDecision("read_only", ("xingchen-agi/xing4.0-29b-a4b:free", "nvidia/nemotron-3.5-super-vl:free", "deepseek/deepseek-v4.1-flash-1017"), TaskType.EXPLORATION, "investigate", RiskLevel.LOW, "Read-only repository exploration", ("cited project evidence",))
    if any(word in text for word in ("security", "vulnerability", "architecture review")):
        return RoutingDecision("security_or_architecture", ("z-ai/glm-5.3", "qwen/qwen3.8-max-prime", "deepseek/deepseek-v4.1-flash-1017"), TaskType.SECURITY, "code_review", RiskLevel.HIGH, "Security-sensitive work requires independent findings", ("security findings", "verification report"))
    if "refactor" in text:
        return RoutingDecision("refactoring", ("deepseek/deepseek-v4.1-flash-1017", "z-ai/glm-5.3"), TaskType.REFACTOR, "refactor", RiskLevel.MEDIUM, "Behavior-preserving structural change", ("behavior invariants", "verification report"))
    if any(word in text for word in ("cubit", "bloc", "widget lifecycle", "navigation", "accessibility")):
        task_type = TaskType.BUG_FIX if any(word in text for word in ("fix", "wrong", "error", "crash")) else TaskType.FEATURE
        return RoutingDecision("implementation", ("deepseek/deepseek-v4.1-flash-1017", "z-ai/glm-5.3"), task_type, "flutter_quality", RiskLevel.MEDIUM, "Flutter-specific behavior requires lifecycle and state-quality checks", ("Flutter quality findings", "verification report"))
    if any(word in text for word in ("add", "feature", "implement", "create")):
        return RoutingDecision("implementation", ("deepseek/deepseek-v4.1-flash-1017", "openai/gpt-6-luna"), TaskType.FEATURE, "feature", RiskLevel.MEDIUM, "New behavior requires acceptance evidence", ("acceptance criteria", "verification report", "review findings"))
    if any(word in text for word in ("debug", "failing", "error", "crash", "test")):
        task_type = TaskType.BUILD_REPAIR if any(word in text for word in ("build", "dependency")) else TaskType.BUG_FIX
        return RoutingDecision("debugging", ("deepseek/deepseek-v4.1-flash-1017", "z-ai/glm-5.3", "qwen/qwen3.8-max-prime"), task_type, "bug_fix", RiskLevel.MEDIUM, "Concrete failure requires reproduction and regression evidence", ("reproduction", "regression test", "verification report"))
    return RoutingDecision("implementation", ("deepseek/deepseek-v4.1-flash-1017", "openai/gpt-6-luna"), TaskType.FEATURE, "feature", RiskLevel.MEDIUM, "New behavior requires acceptance evidence", ("acceptance criteria", "verification report", "review findings"))

