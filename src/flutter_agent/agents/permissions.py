from typing import Any

from flutter_agent.tools.base import ToolResult
from flutter_agent.tools.registry import ToolRegistry


class RestrictedTools:
    """Tool facade that enforces a subagent's explicit tool grant."""

    def __init__(self, registry: ToolRegistry, allowed_tools: frozenset[str]):
        self.registry = registry
        self.allowed_tools = allowed_tools

    def schemas(self) -> list[dict[str, Any]]:
        return [schema for schema in self.registry.schemas() if schema["function"]["name"] in self.allowed_tools]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if name not in self.allowed_tools:
            return ToolResult(False, error=f"Tool not granted to subagent: {name}")
        return self.registry.execute(name, arguments)

