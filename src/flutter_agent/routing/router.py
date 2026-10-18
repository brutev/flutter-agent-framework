from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingDecision:
    category: str
    models: tuple[str, ...]


def route_task(task: str) -> RoutingDecision:
    text = task.casefold()
    if any(word in text for word in ("list", "summarize", "describe", "read-only", "dependencies")) and not any(word in text for word in ("edit", "add", "fix", "change")):
        return RoutingDecision("read_only", ("xingchen-agi/xing4.0-29b-a4b:free", "nvidia/nemotron-3.5-super-vl:free", "deepseek/deepseek-v4.1-flash-1017"))
    if any(word in text for word in ("security", "vulnerability", "architecture review")):
        return RoutingDecision("security_or_architecture", ("z-ai/glm-5.3", "qwen/qwen3.8-max-prime", "deepseek/deepseek-v4.1-flash-1017"))
    if any(word in text for word in ("debug", "failing", "error", "crash", "test")):
        return RoutingDecision("debugging", ("deepseek/deepseek-v4.1-flash-1017", "z-ai/glm-5.3", "qwen/qwen3.8-max-prime"))
    return RoutingDecision("implementation", ("deepseek/deepseek-v4.1-flash-1017", "openai/gpt-6-luna"))

