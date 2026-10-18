import subprocess
from pathlib import Path

from flutter_agent.security.scope import ProjectScope
from flutter_agent.tools.base import ToolResult


class FlutterTools:
    def __init__(self, scope: ProjectScope):
        self.scope = scope

    def verify(self, command: str, timeout_seconds: int = 120) -> ToolResult:
        allowed = {
            "dart analyze": ["dart", "analyze"],
            "flutter test": ["flutter", "test"],
        }
        if command not in allowed:
            return ToolResult(False, error=f"Command is not allowed: {command}")
        try:
            completed = subprocess.run(
                allowed[command],
                cwd=self.scope.root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            output = (completed.stdout + completed.stderr)[-50_000:]
            return ToolResult(completed.returncode == 0, {"exit_code": completed.returncode, "output": output})
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ToolResult(False, error=str(exc))

