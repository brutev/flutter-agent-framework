from pathlib import Path

from flutter_agent.security.scope import ProjectScope
from flutter_agent.tools.registry import ToolRegistry
from flutter_agent.agents.permissions import RestrictedTools


def test_subagent_cannot_use_tools_outside_its_grant(tmp_path: Path) -> None:
    restricted = RestrictedTools(ToolRegistry(ProjectScope(tmp_path)), frozenset({"read_file"}))
    denied = restricted.execute("write_file", {"path": "x.dart", "content": ""})
    assert not denied.ok
    assert "not granted" in (denied.error or "").lower()

