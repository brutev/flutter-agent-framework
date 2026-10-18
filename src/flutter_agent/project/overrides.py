from dataclasses import replace
from pathlib import Path
import tomllib

from flutter_agent.project.profile import ProjectProfile


def apply_project_overrides(root: Path, profile: ProjectProfile) -> ProjectProfile:
    path = root.expanduser().resolve() / ".flutter-agent" / "config.toml"
    if not path.exists():
        return profile
    project = tomllib.loads(path.read_text(encoding="utf-8")).get("project", {})
    allowed = {field: value for field, value in project.items() if field in {
        "architecture", "state_management", "http_client", "routing", "dependency_injection"
    }}
    return replace(profile, **allowed)

