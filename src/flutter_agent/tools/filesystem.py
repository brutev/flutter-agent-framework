from pathlib import Path
import os
import tempfile

from flutter_agent.security.scope import ProjectScope
from flutter_agent.standards.rules import RuleSet, validate_dart_source
from flutter_agent.tools.base import ToolResult


class FilesystemTools:
    def __init__(self, scope: ProjectScope, rules: RuleSet | None = None):
        self.scope = scope
        self.rules = rules or RuleSet()

    def list_files(self, path: str = ".") -> ToolResult:
        try:
            directory = self.scope.resolve(path)
            if not directory.is_dir():
                return ToolResult(False, error=f"Not a directory: {path}")
            entries = sorted(
                str(item.relative_to(self.scope.root))
                for item in directory.iterdir()
                if item.name not in {".git", ".dart_tool", "build"}
            )
            return ToolResult(True, entries)
        except (OSError, PermissionError) as exc:
            return ToolResult(False, error=str(exc))

    def read_file(self, path: str, max_bytes: int = 200_000) -> ToolResult:
        try:
            target = self.scope.resolve(path)
            if not target.is_file():
                return ToolResult(False, error=f"Not a file: {path}")
            data = target.read_bytes()
            if len(data) > max_bytes:
                return ToolResult(False, error=f"File exceeds read limit: {max_bytes} bytes")
            return ToolResult(True, data.decode("utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            return ToolResult(False, error=str(exc))

    def search_code(self, query: str, path: str = ".") -> ToolResult:
        if not query:
            return ToolResult(False, error="Search query must not be empty")
        try:
            base = self.scope.resolve(path)
            matches: list[str] = []
            candidates = [base] if base.is_file() else base.rglob("*")
            for candidate in candidates:
                if not candidate.is_file() or candidate.suffix not in {".dart", ".yaml", ".yml", ".json", ".md", ".py"}:
                    continue
                try:
                    for line_number, line in enumerate(candidate.read_text(encoding="utf-8").splitlines(), 1):
                        if query.casefold() in line.casefold():
                            matches.append(f"{candidate.relative_to(self.scope.root)}:{line_number}:{line.strip()}")
                except (OSError, UnicodeDecodeError):
                    continue
            return ToolResult(True, matches[:500])
        except OSError as exc:
            return ToolResult(False, error=str(exc))

    def write_file(self, path: str, content: str) -> ToolResult:
        try:
            target = self.scope.resolve(path)
            if target.suffix == ".dart":
                findings = validate_dart_source(path, content, self.rules)
                if findings:
                    return ToolResult(False, error="; ".join(finding.message for finding in findings))
            if target.exists() and target.is_symlink():
                return ToolResult(False, error="Refusing to overwrite a symbolic link")
            target.parent.mkdir(parents=True, exist_ok=True)
            target = self.scope.resolve(path)
            if target.exists() and target.is_symlink():
                return ToolResult(False, error="Refusing to overwrite a symbolic link")
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            return ToolResult(True, str(target.relative_to(self.scope.root)))
        except (OSError, UnicodeError) as exc:
            return ToolResult(False, error=str(exc))

