from typing import Any

from flutter_agent.security.scope import ProjectScope
from flutter_agent.tools.base import Tool, ToolResult
from flutter_agent.tools.filesystem import FilesystemTools
from flutter_agent.tools.flutter import FlutterTools
from flutter_agent.standards.rules import RuleSet


class ToolRegistry:
    def __init__(self, scope: ProjectScope, rules: RuleSet | None = None):
        self.scope = scope
        filesystem = FilesystemTools(scope, rules)
        flutter = FlutterTools(scope)
        self._tools = {
            "list_files": Tool("list_files", "List files in the project", {"type": "object", "properties": {"path": {"type": "string"}}}, filesystem.list_files),
            "read_file": Tool("read_file", "Read a UTF-8 project file", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, filesystem.read_file),
            "search_code": Tool("search_code", "Search supported project files", {"type": "object", "properties": {"query": {"type": "string"}, "path": {"type": "string"}}, "required": ["query"]}, filesystem.search_code),
            "write_file": Tool("write_file", "Create or replace a project file", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, filesystem.write_file),
            "verify": Tool("verify", "Run an approved Dart or Flutter verification command", {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}, flutter.verify),
        }

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(False, error=f"Unknown tool: {name}")
        validation_error = self._validate_arguments(tool, arguments)
        if validation_error:
            return ToolResult(False, error=f"Invalid arguments for {name}: {validation_error}")
        try:
            return tool.handler(**arguments)
        except TypeError as exc:
            return ToolResult(False, error=f"Invalid arguments for {name}: {exc}")

    @staticmethod
    def _validate_arguments(tool: Tool, arguments: Any) -> str | None:
        if not isinstance(arguments, dict):
            return "arguments must be an object"
        schema = tool.parameters
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        missing = [name for name in required if name not in arguments]
        if missing:
            return "missing required fields: " + ", ".join(missing)
        unknown = sorted(set(arguments) - set(properties))
        if unknown:
            return "unknown fields: " + ", ".join(unknown)
        for name, value in arguments.items():
            expected = properties[name].get("type")
            if expected == "string" and not isinstance(value, str):
                return f"{name} must be a string"
            if isinstance(value, str):
                limit = 1_000_000 if name == "content" else 10_000
                if len(value.encode("utf-8")) > limit:
                    return f"{name} exceeds {limit} bytes"
        return None

