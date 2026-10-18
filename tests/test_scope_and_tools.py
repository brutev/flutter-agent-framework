from pathlib import Path

from flutter_agent.security.scope import ProjectScope, ScopeViolation
from flutter_agent.tools.registry import ToolRegistry
from flutter_agent.standards.rules import RuleSet


def test_scope_rejects_parent_escape(tmp_path: Path) -> None:
    scope = ProjectScope(tmp_path)
    try:
        scope.resolve("../outside.txt")
    except ScopeViolation:
        pass
    else:
        raise AssertionError("parent traversal was not rejected")


def test_filesystem_tools_are_project_scoped(tmp_path: Path) -> None:
    registry = ToolRegistry(ProjectScope(tmp_path))
    result = registry.execute("write_file", {"path": "lib/example.dart", "content": "void main() {}"})
    assert result.ok
    assert (tmp_path / "lib/example.dart").read_text() == "void main() {}"
    escaped = registry.execute("read_file", {"path": "../secret.txt"})
    assert not escaped.ok


def test_verify_rejects_unapproved_commands(tmp_path: Path) -> None:
    registry = ToolRegistry(ProjectScope(tmp_path))
    result = registry.execute("verify", {"command": "rm -rf ."})
    assert not result.ok


def test_write_file_rejects_standard_violation(tmp_path: Path) -> None:
    registry = ToolRegistry(ProjectScope(tmp_path), RuleSet(domain_forbidden_imports=("flutter",)))
    result = registry.execute(
        "write_file",
        {"path": "lib/domain/entities/user.dart", "content": "import 'package:flutter/material.dart';"},
    )
    assert not result.ok
    assert "forbidden" in (result.error or "").lower()
