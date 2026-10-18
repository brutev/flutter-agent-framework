import json
from dataclasses import asdict
from pathlib import Path

from flutter_agent.project.profile import ProjectProfile


def save_profile(root: Path, profile: ProjectProfile) -> Path:
    path = root.expanduser().resolve() / ".flutter-agent" / "project_profile.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
    return path


def load_profile(root: Path) -> ProjectProfile | None:
    path = root.expanduser().resolve() / ".flutter-agent" / "project_profile.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectProfile(
        architecture=data["architecture"],
        state_management=data["state_management"],
        http_client=data["http_client"],
        routing=data["routing"],
        dependency_injection=data["dependency_injection"],
        dependencies=tuple(data.get("dependencies", [])),
    )

